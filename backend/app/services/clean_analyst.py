"""
CleanAnalyst v1.0 - Умный помощник без костылей
GPT-4o как полноценный аналитик данных
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


class CleanAnalyst:
    """
    Чистый подход: даём GPT данные, задаём вопрос, доверяем ответу.
    """

    SYSTEM_PROMPT = """Ты - умный аналитик данных для Google Sheets. Анализируешь таблицы, делаешь расчёты, объясняешь логику.

## ТВОИ ВОЗМОЖНОСТИ

### Анализ и расчёты:
- Суммы, средние, проценты, доли
- Поиск трендов и паттернов
- Прогнозирование (тренд, экстраполяция, среднее)
- Группировка и агрегация
- Поиск аномалий и проблем
- Сравнение периодов

### Действия с таблицей:
- **write_column** - добавить новую колонку с данными
- **highlight** - выделить строки цветом
- **sort** - отсортировать таблицу
- **chart** - создать диаграмму
- **formula** - создать формулу Google Sheets
- **answer** - просто ответить текстом

## ФОРМАТ ОТВЕТА (JSON)

```json
{
  "thinking": "Мои рассуждения: что вижу в данных, как буду решать задачу",

  "methodology": {
    "name": "название метода (trend_extrapolation, weighted_average, sum, filter, etc.)",
    "reason": "почему выбрал именно этот метод",
    "formula": "формула или алгоритм расчёта"
  },

  "examples": [
    {
      "item": "ID или название элемента",
      "input": "входные данные (например: Окт=2245, Ноя=3282, Дек=3913)",
      "calculation": "пошаговый расчёт",
      "result": "итоговое значение"
    }
  ],

  "result": {
    "summary": "краткий ответ на вопрос пользователя",
    "details": "подробное объяснение с цифрами"
  },

  "action": {
    "type": "write_column | highlight | sort | chart | formula | answer",
    ... специфичные поля для каждого типа (см. ниже) ...
  },

  "confidence": 0.95,
  "warnings": ["предупреждения если есть"]
}
```

## ТИПЫ ДЕЙСТВИЙ (action)

### write_column - добавить колонку
```json
{
  "type": "write_column",
  "key_column": "Артикул",
  "new_column_name": "Прогноз Январь",
  "values": [
    ["АРТ001", 5193],
    ["АРТ002", 2852]
  ]
}
```

### highlight - выделить строки
```json
{
  "type": "highlight",
  "rows": [2, 5, 8],
  "color": "#FFCCCB",
  "reason": "Строки с отрицательными значениями"
}
```

### sort - сортировка
```json
{
  "type": "sort",
  "column": "Сумма",
  "column_index": 3,
  "order": "desc"
}
```

### chart - диаграмма
```json
{
  "type": "chart",
  "chart_type": "COLUMN | LINE | PIE | BAR",
  "title": "Продажи по месяцам",
  "x_column": "Месяц",
  "x_column_index": 0,
  "y_columns": ["Продажи", "План"],
  "y_column_indices": [1, 2]
}
```

### formula - формула Google Sheets
```json
{
  "type": "formula",
  "formula": "=СУММ(B2:B100)",
  "target_cell": "B101",
  "explanation": "Сумма всех значений в колонке B"
}
```

### answer - текстовый ответ
```json
{
  "type": "answer",
  "text": "Ответ на вопрос пользователя"
}
```

## ВАЖНЫЕ ПРАВИЛА

1. **ВСЕГДА показывай рассуждения** в "thinking" - что понял, что вижу, как решаю
2. **ВСЕГДА объясняй методологию** - почему выбрал этот подход
3. **ВСЕГДА давай примеры** - минимум 2-3 конкретных расчёта с числами
4. **Формулы на русском** - СУММ, СРЗНАЧ, ЕСЛИ, ВПР (не SUM, AVERAGE, IF, VLOOKUP)
5. **Будь честным** - если не уверен или данных мало, скажи об этом

## ПРИМЕР ХОРОШЕГО ОТВЕТА

Запрос: "Спрогнозируй заказы на январь"

```json
{
  "thinking": "Вижу данные за 3 месяца: Октябрь, Ноябрь, Декабрь. Замечаю рост у большинства позиций. Для прогноза использую экстраполяцию тренда - это точнее чем просто среднее, когда есть явная динамика.",

  "methodology": {
    "name": "trend_extrapolation",
    "reason": "Данные показывают устойчивый рост (+15-30% в месяц), поэтому среднее занизит прогноз. Экстраполяция учитывает динамику.",
    "formula": "Прогноз = Декабрь × (1 + средний_месячный_рост)"
  },

  "examples": [
    {
      "item": "СХ_анимезхс_54",
      "input": "Окт=2245, Ноя=3282, Дек=3913",
      "calculation": "Рост Окт→Ноя: +46%, Ноя→Дек: +19%. Средний рост: +32.5%. Прогноз: 3913 × 1.325 = 5185",
      "result": "5185"
    },
    {
      "item": "СХ_андеграунд_100шт",
      "input": "Окт=1200, Ноя=1650, Дек=2100",
      "calculation": "Рост Окт→Ноя: +37.5%, Ноя→Дек: +27.3%. Средний: +32.4%. Прогноз: 2100 × 1.324 = 2780",
      "result": "2780"
    },
    {
      "item": "СХ_романтика_54",
      "input": "Окт=950, Ноя=1100, Дек=1050",
      "calculation": "Рост нестабильный (+15.8%, -4.5%). Изменение <10% - использую взвешенное среднее: (950×1 + 1100×2 + 1050×3) / 6 = 1042",
      "result": "1042"
    }
  ],

  "result": {
    "summary": "Прогноз на январь для 134 позиций. 120 позиций с трендом роста (экстраполяция), 14 стабильных (взвешенное среднее).",
    "details": "Средний рост по всем позициям: +24% в месяц. Топ роста: СХ_анимезхс_54 (+32%), СХ_андеграунд_100шт (+32%). Стабильные: СХ_романтика_54, СХ_коты_54."
  },

  "action": {
    "type": "write_column",
    "key_column": "Артикул",
    "new_column_name": "Прогноз Январь",
    "values": [
      ["СХ_анимезхс_54", 5185],
      ["СХ_андеграунд_100шт", 2780],
      ["СХ_романтика_54", 1042]
    ]
  },

  "confidence": 0.85,
  "warnings": ["Прогноз основан на 3 месяцах - для большей точности желательно 6+ месяцев данных"]
}
```"""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    def format_data_as_table(self, df: pd.DataFrame, column_names: List[str], max_rows: int = 500) -> str:
        """Форматирует данные в читаемую таблицу"""

        lines = []

        # Информация о данных
        total_rows = len(df)
        show_rows = min(total_rows, max_rows)

        if total_rows > max_rows:
            lines.append(f"ТАБЛИЦА: {total_rows} строк × {len(column_names)} колонок (показаны первые {show_rows})")
        else:
            lines.append(f"ТАБЛИЦА: {total_rows} строк × {len(column_names)} колонок")

        lines.append("")

        # Заголовки с индексами колонок
        header_with_idx = [f"{col} [Col {i}]" for i, col in enumerate(column_names)]
        lines.append("| № | " + " | ".join(column_names) + " |")
        lines.append("|---|" + "|".join(["---"] * len(column_names)) + "|")

        # Данные
        for idx, (_, row) in enumerate(df.head(show_rows).iterrows()):
            row_num = idx + 2  # +2 because row 1 is header in sheets
            values = []
            for col in column_names:
                if col in df.columns:
                    val = row[col]
                    if pd.isna(val):
                        values.append("")
                    elif isinstance(val, float):
                        values.append(f"{val:.0f}" if val == int(val) else f"{val:.2f}")
                    else:
                        values.append(str(val)[:30])  # Truncate long values
                else:
                    values.append("")
            lines.append(f"| {row_num} | " + " | ".join(values) + " |")

        if total_rows > max_rows:
            lines.append(f"| ... | ещё {total_rows - max_rows} строк ... |")

        return "\n".join(lines)

    async def analyze(
        self,
        query: str,
        df: pd.DataFrame,
        column_names: List[str],
        context: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        reference_df: Optional[pd.DataFrame] = None,
        reference_sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Главный метод анализа
        """
        start_time = time.time()

        # Форматируем основные данные
        data_text = self.format_data_as_table(df, column_names)

        # Добавляем справочный лист если есть (для VLOOKUP)
        reference_text = ""
        if reference_df is not None and reference_sheet_name:
            ref_cols = list(reference_df.columns)
            reference_text = f"""

СПРАВОЧНЫЙ ЛИСТ "{reference_sheet_name}" (для подтягивания данных):
{self.format_data_as_table(reference_df, ref_cols, max_rows=100)}
"""

        # Контекст пользователя
        context_text = f"\nРОЛЬ ПОЛЬЗОВАТЕЛЯ: {context}\n" if context else ""

        # История диалога
        history_text = ""
        if history:
            history_text = "\nПРЕДЫДУЩИЕ ВОПРОСЫ:\n"
            for h in history[-3:]:
                q = h.get('query', '')
                r = str(h.get('response', h.get('summary', '')))[:200]
                history_text += f"В: {q}\nО: {r}\n"

        # Формируем запрос
        user_prompt = f"""{context_text}{history_text}
{data_text}
{reference_text}

ВОПРОС: {query}

Проанализируй данные и ответь в JSON формате. Покажи рассуждения, методологию и примеры расчётов."""

        try:
            logger.info(f"[CleanAnalyst] Query: {query[:50]}...")
            logger.info(f"[CleanAnalyst] Data: {len(df)} rows, {len(column_names)} cols")

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Низкая для стабильности
                max_tokens=4000,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            elapsed = time.time() - start_time

            logger.info(f"[CleanAnalyst] Thinking: {result.get('thinking', '')[:100]}...")
            logger.info(f"[CleanAnalyst] Method: {result.get('methodology', {}).get('name', 'N/A')}")
            logger.info(f"[CleanAnalyst] Action: {result.get('action', {}).get('type', 'N/A')}")
            logger.info(f"[CleanAnalyst] Time: {elapsed:.2f}s")

            return {
                "success": True,
                "gpt_response": result,
                "processing_time": f"{elapsed:.2f}s"
            }

        except json.JSONDecodeError as e:
            logger.error(f"[CleanAnalyst] JSON parse error: {e}")
            logger.error(f"[CleanAnalyst] Raw response: {result_text[:500]}")
            return {"success": False, "error": f"JSON parse error: {e}"}
        except Exception as e:
            logger.error(f"[CleanAnalyst] Error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def transform_to_frontend_format(self, gpt_response: Dict, processing_time: str) -> Dict[str, Any]:
        """
        Преобразует ответ GPT в формат для фронтенда
        """

        action = gpt_response.get("action", {})
        action_type = action.get("type", "answer")
        methodology = gpt_response.get("methodology", {})
        examples = gpt_response.get("examples", [])
        result = gpt_response.get("result", {})

        # Формируем детальное объяснение
        explanation_parts = []

        # Методология
        if methodology:
            explanation_parts.append(f"МЕТОД: {methodology.get('name', 'N/A')}")
            if methodology.get('reason'):
                explanation_parts.append(methodology['reason'])
            if methodology.get('formula'):
                explanation_parts.append(f"Формула: {methodology['formula']}")
            explanation_parts.append("")

        # Примеры
        if examples:
            explanation_parts.append("ПРИМЕРЫ РАСЧЁТОВ:")
            for ex in examples[:5]:
                explanation_parts.append(f"• {ex.get('item', 'N/A')}")
                explanation_parts.append(f"  Данные: {ex.get('input', '')}")
                explanation_parts.append(f"  Расчёт: {ex.get('calculation', '')}")
                explanation_parts.append(f"  Результат: {ex.get('result', '')}")
                explanation_parts.append("")

        explanation = "\n".join(explanation_parts)

        # Базовый ответ
        response = {
            "success": True,
            "formula": None,
            "explanation": explanation,
            "target_cell": None,
            "confidence": gpt_response.get("confidence", 0.9),
            "response_type": "analysis",
            "summary": result.get("summary", ""),
            "methodology": methodology,
            "thinking": gpt_response.get("thinking", ""),
            "insights": [],
            "key_findings": [result.get("details", "")] if result.get("details") else [],
            "warnings": gpt_response.get("warnings", []),
            "processing_time": processing_time,
            "processor_version": "CleanAnalyst v1.0",
            "python_executed": False  # GPT сам всё считает
        }

        # Преобразуем action в формат фронтенда
        if action_type == "write_column":
            response["action_type"] = "write_data"
            response["merge_by_key"] = action.get("key_column")
            response["write_headers"] = [action.get("key_column"), action.get("new_column_name")]
            response["write_data"] = action.get("values", [])

        elif action_type == "highlight":
            response["action_type"] = "highlight"
            response["highlight_rows"] = action.get("rows", [])
            response["highlight_color"] = action.get("color", "#FFCCCB")
            response["highlight_message"] = action.get("reason", "")

        elif action_type == "sort":
            response["action_type"] = "sort"
            response["sort_column"] = action.get("column")
            response["sort_column_index"] = action.get("column_index")
            response["sort_order"] = action.get("order", "desc")

        elif action_type == "chart":
            response["action_type"] = "chart"
            response["chart_spec"] = {
                "chart_type": action.get("chart_type", "COLUMN"),
                "title": action.get("title", ""),
                "x_column_index": action.get("x_column_index", 0),
                "y_column_indices": action.get("y_column_indices", [1]),
                "row_count": action.get("row_count", 100)
            }

        elif action_type == "formula":
            response["response_type"] = "formula"
            response["formula"] = self._translate_formula(action.get("formula", ""))
            response["target_cell"] = action.get("target_cell")
            response["explanation"] = action.get("explanation", "")

        else:  # answer
            response["action_type"] = None
            response["summary"] = action.get("text", result.get("summary", ""))

        return response

    def _translate_formula(self, formula: str) -> str:
        """Переводит английские функции в русские (для Google Sheets RU)"""

        translations = {
            'SUM': 'СУММ', 'AVERAGE': 'СРЗНАЧ', 'COUNT': 'СЧЁТ', 'COUNTA': 'СЧЁТЗ',
            'IF': 'ЕСЛИ', 'SUMIF': 'СУММЕСЛИ', 'COUNTIF': 'СЧЁТЕСЛИ',
            'VLOOKUP': 'ВПР', 'HLOOKUP': 'ГПР', 'INDEX': 'ИНДЕКС', 'MATCH': 'ПОИСКПОЗ',
            'MAX': 'МАКС', 'MIN': 'МИН', 'AND': 'И', 'OR': 'ИЛИ',
            'LEFT': 'ЛЕВСИМВ', 'RIGHT': 'ПРАВСИМВ', 'MID': 'ПСТР', 'LEN': 'ДЛСТР',
            'ROUND': 'ОКРУГЛ', 'IFERROR': 'ЕСЛИОШИБКА', 'ISBLANK': 'ЕПУСТО',
            'TODAY': 'СЕГОДНЯ', 'NOW': 'ТДАТА', 'YEAR': 'ГОД', 'MONTH': 'МЕСЯЦ', 'DAY': 'ДЕНЬ',
            'FILTER': 'ФИЛЬТР', 'SORT': 'СОРТ', 'UNIQUE': 'УНИК',
            'SUMIFS': 'СУММЕСЛИМН', 'COUNTIFS': 'СЧЁТЕСЛИМН', 'AVERAGEIF': 'СРЗНАЧЕСЛИ'
        }

        result = formula
        for eng, rus in translations.items():
            # Replace only function names (followed by opening parenthesis)
            result = re.sub(rf'\b{eng}\s*\(', f'{rus}(', result, flags=re.IGNORECASE)

        # Replace commas with semicolons (Russian locale)
        # But not inside quoted strings
        parts = []
        in_quotes = False
        current = ""
        for char in result:
            if char == '"':
                in_quotes = not in_quotes
            if char == ',' and not in_quotes:
                current += ';'
            else:
                current += char
        result = current

        return result
