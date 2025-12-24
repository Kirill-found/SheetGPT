# -*- coding: utf-8 -*-
"""
SmartAnalyst v1.0 - GPT планирует, Pandas считает

Архитектура:
1. GPT анализирует запрос и генерирует спецификацию для pandas
2. Pandas выполняет точные расчёты
3. GPT форматирует результат для пользователя
"""

import json
import pandas as pd
import numpy as np
import time
import re
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)


class SmartAnalyst:
    """
    Двухфазный подход: GPT понимает, Pandas считает
    """

    # Phase 1: GPT генерирует спецификацию для pandas
    PLANNER_PROMPT = """Ты - планировщик аналитических запросов. Твоя задача - понять что хочет пользователь и сформировать ТОЧНУЮ спецификацию для pandas.

## ВХОДНЫЕ ДАННЫЕ
Колонки таблицы: {columns}
Примеры данных (первые 5 строк): {sample_data}
Запрос пользователя: {query}

## ТВОЯ ЗАДАЧА
Верни JSON спецификацию для выполнения запроса в pandas:

```json
{{
  "intent": "aggregation | filter | sort | formula | question",
  "description": "краткое описание что нужно сделать",

  "aggregation": {{
    "enabled": true/false,
    "group_by": "название колонки для группировки или null",
    "operations": [
      {{"column": "колонка", "operation": "sum|count|mean|min|max", "alias": "название результата"}}
    ]
  }},

  "filters": [
    {{"column": "колонка", "operator": "equals|contains|greater|less|not_equals", "value": "значение"}}
  ],

  "sort": {{
    "enabled": true/false,
    "column": "колонка",
    "ascending": true/false
  }},

  "output_format": "summary | table | single_value",
  "needs_gpt_analysis": true/false
}}
```

## ПРИМЕРЫ

Запрос: "посчитай сумму по городам"
```json
{{
  "intent": "aggregation",
  "description": "Сумма по городам",
  "aggregation": {{
    "enabled": true,
    "group_by": "Город",
    "operations": [{{"column": "Сумма", "operation": "sum", "alias": "Итого"}}]
  }},
  "filters": [],
  "output_format": "summary",
  "needs_gpt_analysis": false
}}
```

Запрос: "покажи только оплаченные заказы"
```json
{{
  "intent": "filter",
  "description": "Фильтр по оплаченным",
  "aggregation": {{"enabled": false}},
  "filters": [{{"column": "Статус", "operator": "equals", "value": "Оплачен"}}],
  "output_format": "table",
  "needs_gpt_analysis": false
}}
```

Запрос: "посчитай только оплаченные заказы по городам"
```json
{{
  "intent": "aggregation",
  "description": "Сумма оплаченных по городам",
  "aggregation": {{
    "enabled": true,
    "group_by": "Город",
    "operations": [{{"column": "Сумма", "operation": "sum", "alias": "Оплачено"}}]
  }},
  "filters": [{{"column": "Статус", "operator": "equals", "value": "Оплачен"}}],
  "output_format": "summary",
  "needs_gpt_analysis": false
}}
```

Запрос: "какой тренд продаж?"
```json
{{
  "intent": "question",
  "description": "Анализ тренда требует GPT",
  "aggregation": {{"enabled": false}},
  "filters": [],
  "output_format": "summary",
  "needs_gpt_analysis": true
}}
```

## ВАЖНО
- Названия колонок должны ТОЧНО совпадать с column_names
- Если не уверен какую колонку использовать - посмотри на sample_data
- Для фильтра "оплачен" ищи колонку "Статус" и значение "Оплачен" (с большой буквы!)
- needs_gpt_analysis = true только для сложных аналитических вопросов

Верни ТОЛЬКО JSON, без комментариев."""

    # Phase 2: GPT форматирует результат
    FORMATTER_PROMPT = """Ты форматируешь результаты расчётов для пользователя.

## ДАННЫЕ РАСЧЁТА (выполнено в pandas - числа ТОЧНЫЕ!)
{calculation_result}

## ИСХОДНЫЙ ЗАПРОС
{query}

## ФОРМАТ ОТВЕТА
Верни JSON:
```json
{{
  "summary": "Краткий ответ списком с bullet points. Форматируй числа с пробелами (1 234 567 руб)",
  "methodology": {{
    "name": "название метода",
    "formula": "использованная формула",
    "copyable_formula": "=СУММЕСЛИ(...) формула для Google Sheets"
  }},
  "confidence": 0.95,
  "warnings": []
}}
```

Пример summary для агрегации:
"Сумма продаж по городам:
• Москва: 1 234 567 руб
• Самара: 987 654 руб
• Всего: 2 222 221 руб"

ВАЖНО: Числа уже посчитаны pandas - просто красиво отформатируй их!"""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def analyze(
        self,
        query: str,
        df: pd.DataFrame,
        column_names: List[str],
        context: Optional[str] = None,
        history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Главный метод анализа - двухфазный подход
        """
        start_time = time.time()

        try:
            # Phase 1: GPT планирует
            logger.info(f"[SmartAnalyst] Phase 1: Planning for query: {query[:50]}...")
            spec = await self._get_execution_spec(query, df, column_names)
            logger.info(f"[SmartAnalyst] Spec: {json.dumps(spec, ensure_ascii=False)[:200]}")

            # Phase 2: Pandas выполняет (если нужно)
            calculation_result = None
            if spec.get("aggregation", {}).get("enabled") or spec.get("filters"):
                logger.info("[SmartAnalyst] Phase 2: Executing in pandas...")
                calculation_result = self._execute_in_pandas(df, column_names, spec)
                logger.info(f"[SmartAnalyst] Pandas result: {calculation_result}")

            # Phase 3: GPT форматирует
            if calculation_result and not spec.get("needs_gpt_analysis"):
                logger.info("[SmartAnalyst] Phase 3: Formatting results...")
                result = await self._format_results(query, calculation_result, spec)
                result["python_executed"] = True
            else:
                # Fallback: сложный запрос - GPT анализирует сам
                logger.info("[SmartAnalyst] Complex query - full GPT analysis...")
                result = await self._full_gpt_analysis(query, df, column_names, context, history)
                result["python_executed"] = False

            elapsed = time.time() - start_time
            result["processing_time"] = f"{elapsed:.2f}s"
            result["processor_version"] = "SmartAnalyst v1.0"

            return {"success": True, "gpt_response": result, "processing_time": f"{elapsed:.2f}s"}

        except Exception as e:
            logger.error(f"[SmartAnalyst] Error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _get_execution_spec(self, query: str, df: pd.DataFrame, column_names: List[str]) -> Dict:
        """Phase 1: GPT генерирует спецификацию"""

        # Подготовим примеры данных
        sample_rows = []
        for idx, row in df.head(5).iterrows():
            sample_rows.append({col: str(row[col])[:30] for col in column_names if col in df.columns})

        prompt = self.PLANNER_PROMPT.format(
            columns=json.dumps(column_names, ensure_ascii=False),
            sample_data=json.dumps(sample_rows, ensure_ascii=False, indent=2),
            query=query
        )

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",  # Быстрая модель для планирования
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)

    def _execute_in_pandas(self, df: pd.DataFrame, column_names: List[str], spec: Dict) -> Dict:
        """Phase 2: Pandas выполняет расчёты"""

        result = {
            "operation": spec.get("intent"),
            "description": spec.get("description"),
            "data": []
        }

        work_df = df.copy()

        # Применяем фильтры
        filters_applied = []
        for f in spec.get("filters", []):
            col = f.get("column")
            op = f.get("operator")
            val = f.get("value")

            if col not in work_df.columns:
                logger.warning(f"[SmartAnalyst] Filter column not found: {col}")
                continue

            if op == "equals":
                work_df = work_df[work_df[col].astype(str).str.lower() == str(val).lower()]
            elif op == "contains":
                work_df = work_df[work_df[col].astype(str).str.contains(str(val), case=False, na=False)]
            elif op == "greater":
                work_df = work_df[pd.to_numeric(work_df[col], errors='coerce') > float(val)]
            elif op == "less":
                work_df = work_df[pd.to_numeric(work_df[col], errors='coerce') < float(val)]
            elif op == "not_equals":
                work_df = work_df[work_df[col].astype(str).str.lower() != str(val).lower()]

            filters_applied.append(f"{col} {op} '{val}'")

        result["filters_applied"] = filters_applied
        result["rows_after_filter"] = len(work_df)

        # Выполняем агрегацию
        agg_spec = spec.get("aggregation", {})
        if agg_spec.get("enabled"):
            group_col = agg_spec.get("group_by")
            operations = agg_spec.get("operations", [])

            if group_col and group_col in work_df.columns and operations:
                agg_dict = {}
                for op in operations:
                    col = op.get("column")
                    operation = op.get("operation")
                    alias = op.get("alias", col)

                    if col in work_df.columns:
                        # Конвертируем в числа
                        work_df[col] = pd.to_numeric(work_df[col], errors='coerce')
                        agg_dict[col] = operation

                if agg_dict:
                    grouped = work_df.groupby(group_col).agg(agg_dict)
                    grouped = grouped.sort_values(by=list(agg_dict.keys())[0], ascending=False)

                    # Форматируем результат
                    for idx, row in grouped.iterrows():
                        item = {"group": str(idx)}
                        for col in agg_dict.keys():
                            val = row[col]
                            item[col] = float(val) if pd.notna(val) else 0
                            item[f"{col}_formatted"] = f"{val:,.0f}".replace(",", " ") if pd.notna(val) else "0"
                        result["data"].append(item)

                    # Итого
                    result["totals"] = {}
                    for col in agg_dict.keys():
                        total = grouped[col].sum()
                        result["totals"][col] = float(total)
                        result["totals"][f"{col}_formatted"] = f"{total:,.0f}".replace(",", " ")

        return result

    async def _format_results(self, query: str, calc_result: Dict, spec: Dict) -> Dict:
        """Phase 3: GPT форматирует результаты"""

        prompt = self.FORMATTER_PROMPT.format(
            calculation_result=json.dumps(calc_result, ensure_ascii=False, indent=2),
            query=query
        )

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Добавляем данные из расчёта
        result["calculation_data"] = calc_result
        result["action_type"] = None  # Просто ответ, не действие

        return result

    async def _full_gpt_analysis(self, query: str, df: pd.DataFrame, column_names: List[str],
                                  context: Optional[str], history: Optional[List[Dict]]) -> Dict:
        """Fallback: полный анализ GPT для сложных запросов"""

        # Используем существующую логику из CleanAnalyst
        from app.services.clean_analyst import CleanAnalyst

        # Временно создаём CleanAnalyst для сложных запросов
        clean_analyst = CleanAnalyst(self.client.api_key)
        result = await clean_analyst.analyze(query, df, column_names, context, history)

        if result.get("success"):
            return result.get("gpt_response", {})
        else:
            return {"summary": "Ошибка анализа", "error": result.get("error")}
