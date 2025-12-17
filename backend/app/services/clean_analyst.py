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

## КРИТИЧЕСКИ ВАЖНО

### Соответствие колонок и букв:
Массив column_names напрямую соответствует буквам колонок Excel:
- Индекс 0 → колонка A
- Индекс 1 → колонка B
- Индекс 2 → колонка C
- и т.д.

При fill_column/fill_columns используй букву колонки из этого соответствия!

### При записи данных (write_column):
- **ВСЕГДА возвращай ВСЕ строки** - если в таблице 134 строки, в values должно быть 134 записи
- Никогда не обрезай данные, не возвращай только примеры
- Каждая строка исходных данных должна получить расчётное значение
- **КОПИРУЙ КЛЮЧИ ТОЧНО** - артикулы/названия копируй символ в символ, не обрезай и не изменяй!
  - ПРАВИЛЬНО: "СХ_андер_Т_ж+андер_100шт"
  - НЕПРАВИЛЬНО: "СХ_андер_Т_ж+андер_100ш" (обрезано!)

### При прогнозировании:
- **Учитывай сезонность** - январь после праздников обычно ХУЖЕ декабря (спад 10-30%)
- **Будь консервативным** - лучше занизить прогноз, чем дать нереалистично высокий
- Не экстраполируй бесконечный рост - рынок имеет потолок
- Если декабрь показывает пик (предновогодние продажи), январь будет ниже

### Прозрачность расчётов:
- Показывай КАЖДЫЙ шаг расчёта с конкретными числами
- Формула должна быть воспроизводимой - пользователь должен мочь проверить
- Объясни ПОЧЕМУ выбран этот метод, а не другой

## ТВОИ ВОЗМОЖНОСТИ

### Анализ и расчёты:
- Суммы, средние, проценты, доли
- Поиск трендов и паттернов
- Прогнозирование (с учётом сезонности!)
- Группировка и агрегация
- Поиск аномалий и проблем
- Сравнение периодов

### Действия с таблицей:
- **write_column** - добавить новую колонку с данными (ВСЕГДА все строки!)
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
    "formula": "описание алгоритма расчёта",
    "copyable_formula": "РАБОЧАЯ формула Google Sheets с адресами ячеек, которую можно скопировать. Пример: =ВПР(A2;'Лист2'!A:H;8;ЛОЖЬ). ТОЛЬКО адреса ячеек (A2, B2), НИКОГДА названия колонок!"
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
    "summary": "ИНФОРМАТИВНЫЙ ответ с формулой и ключевыми числами. Пример: 'Прогноз по формуле ((Окт×1+Ноя×2+Дек×3)/6)×0.85. Средний прогноз: 1200, диапазон: 100-3000'",
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

### write_column - добавить колонку (с привязкой по ключу)
Используй ТОЛЬКО когда в таблице РЕАЛЬНО СУЩЕСТВУЕТ уникальная ключевая колонка (Артикул, ID, SKU, Email).
**КРИТИЧЕСКИ ВАЖНО**:
- key_column ДОЛЖНА существовать в column_names!
- НЕ придумывай колонки типа "№", "Row", "Строка" - их НЕТ в данных!
- Для РАСЧЁТОВ (ROMI, маржа, %) используй fill_column - он проще и надёжнее!
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

### fill_column - заполнить ОДНУ колонку (по порядку строк) ⭐ ДЛЯ РАСЧЁТОВ
Используй для добавления РАССЧИТАННЫХ показателей (ROMI, маржа, %, конверсия и т.д.)
**ВАЖНО**:
- target_column: СЛЕДУЮЩАЯ буква после последней колонки! Если данные в A-L, новая колонка = M
- column_name: название новой колонки ("ROMI %", "Маржа" и т.д.)
- start_row: 2 (первая строка данных после заголовка)
- values: расчёт для КАЖДОЙ строки данных! Если 42 строки - 42 значения!
```json
{
  "type": "fill_column",
  "target_column": "B",
  "column_name": "Заказов",
  "start_row": 8,
  "values": [474, 537, 600]
}
```

### fill_columns - заполнить НЕСКОЛЬКО колонок ⭐ ПРЕДПОЧТИТЕЛЬНЫЙ ДЛЯ ПРОГНОЗОВ
Используй когда просят рассчитать/спрогнозировать НЕСКОЛЬКО показателей (заказы И выручку И прибыль).
**ВАЖНО**:
- Если колонка уже существует (B=Заказов, C=Выручка, D=Прибыль), заполняй ЕЁ!
- Все колонки заполняются начиная с одной start_row
- Количество values в каждой колонке должно быть одинаковым
```json
{
  "type": "fill_columns",
  "start_row": 8,
  "columns": [
    {"target": "B", "name": "Заказов", "values": [442, 468, 494]},
    {"target": "C", "name": "Выручка", "values": [498000, 526000, 555000]},
    {"target": "D", "name": "Прибыль", "values": [76804, 81428, 85952]}
  ]
}
```
Пример: таблица [Месяц(A), Заказов(B), Выручка(C), Прибыль(D)] с данными до строки 7. Прогноз на Янв/Фев/Мар → start_row=8, 3 значения В КАЖДУЮ из колонок B, C, D.

### replace_data - полная перезапись данных (разбить CSV, структурировать)
Используй когда данные в одной ячейке/колонке содержат CSV или нужно полностью заменить структуру таблицы.
Например: "разбей данные по ячейкам", "разделить по колонкам", данные вида "A,B,C" в одной ячейке.
**ВАЖНО**: НЕ используй write_column с merge_by_key для разбиения CSV - нет ключевой колонки!
```json
{
  "type": "replace_data",
  "headers": ["Месяц", "Заказов", "Выручка", "Прибыль"],
  "rows": [
    ["Июль 2024", 245, 287650, 41200],
    ["Август 2024", 312, 358900, 52300]
  ]
}
```

### highlight - выделить конкретные строки (если знаешь номера)
```json
{
  "type": "highlight",
  "rows": [2, 5, 8],
  "color": "#FFCCCB",
  "reason": "Строки с отрицательными значениями"
}
```

### conditional_format - условное форматирование по значению ⭐ ДЛЯ ВЫДЕЛЕНИЯ ПО УСЛОВИЮ
Используй когда нужно выделить строки ПО УСЛОВИЮ (бренд = Apple, сумма > 1000, и т.д.)
Для НЕСКОЛЬКИХ условий с разными цветами - верни МАССИВ rules!
```json
{
  "type": "conditional_format",
  "rules": [
    {
      "column_index": 1,
      "condition_type": "TEXT_EQ",
      "condition_value": "Apple",
      "color": "#90EE90"
    },
    {
      "column_index": 1,
      "condition_type": "TEXT_EQ",
      "condition_value": "Realme",
      "color": "#FF6347"
    }
  ]
}
```
condition_type: TEXT_EQ (равно), TEXT_CONTAINS (содержит), NUMBER_GREATER (>), NUMBER_LESS (<), NUMBER_EQ (=)

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
**ВАЖНО для chart**: индексы колонок начинаются с 0! Если колонки ["Артикул", "Декабрь"], то Артикул=0, Декабрь=1.

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
5. **Формулы для Google Sheets RU** - используй правильный синтаксис:
   - Разделитель аргументов: точка с запятой `;`
   - ЛОЖЬ/ИСТИНА заменяй на `0`/`1`
   - **ВПР обязательно**: `=ВПР(A2;'Лист'!A:H;номер_колонки;0)` где:
     - A2 = ячейка с искомым значением (артикул в колонке A, строка 2)
     - 'Лист'!A:H = диапазон поиска, ВСЕГДА начинается с A (колонка с ключами)
     - номер_колонки = какую колонку вернуть (1=A, 2=B, 8=H)
     - 0 = точное совпадение
   - Пример: `=ВПР(A2;'для расчёта'!A:H;8;0)` - ищем артикул из A2 в листе 'для расчёта', возвращаем 8-ю колонку
6. **Будь честным** - если не уверен или данных мало, скажи об этом

## ПРИМЕР ХОРОШЕГО ОТВЕТА

Запрос: "Спрогнозируй заказы на январь"

```json
{
  "thinking": "Вижу данные за 3 месяца: Октябрь, Ноябрь, Декабрь. Декабрь - пик продаж (предновогодний). Январь ВСЕГДА хуже декабря из-за спада после праздников. Использую консервативный подход: взвешенное среднее с понижающим коэффициентом для января.",

  "methodology": {
    "name": "weighted_average_seasonal",
    "reason": "Январь после праздников всегда показывает спад 15-25% от декабря. Экстраполяция тренда здесь не подходит - она даст нереалистично высокий прогноз. Использую взвешенное среднее × 0.85 (сезонный коэффициент).",
    "formula": "Прогноз = ((Окт×1 + Ноя×2 + Дек×3) / 6) × 0.85",
    "copyable_formula": "=((B2*1+C2*2+D2*3)/6)*0,85"
  },

  "examples": [
    {
      "item": "СХ_анимезхс_54",
      "input": "Окт=2245, Ноя=3282, Дек=3913",
      "calculation": "Шаг 1: Взвешенная сумма = 2245×1 + 3282×2 + 3913×3 = 2245 + 6564 + 11739 = 20548. Шаг 2: Взвешенное среднее = 20548 / 6 = 3425. Шаг 3: С сезонным коэффициентом = 3425 × 0.85 = 2911",
      "result": "2911"
    },
    {
      "item": "СХ_андеграунд_100шт",
      "input": "Окт=1200, Ноя=1650, Дек=2100",
      "calculation": "Шаг 1: 1200×1 + 1650×2 + 2100×3 = 1200 + 3300 + 6300 = 10800. Шаг 2: 10800 / 6 = 1800. Шаг 3: 1800 × 0.85 = 1530",
      "result": "1530"
    },
    {
      "item": "СХ_романтика_54",
      "input": "Окт=950, Ноя=1100, Дек=1050",
      "calculation": "Шаг 1: 950×1 + 1100×2 + 1050×3 = 950 + 2200 + 3150 = 6300. Шаг 2: 6300 / 6 = 1050. Шаг 3: 1050 × 0.85 = 893",
      "result": "893"
    }
  ],

  "result": {
    "summary": "Прогноз по формуле ((Окт×1+Ноя×2+Дек×3)/6)×0.85. Коэффициент 0.85 учитывает январский спад. Средний прогноз: ~1500, диапазон: 100-2911.",
    "details": "Январь традиционно слабее декабря на 15-25%. Взвешенное среднее даёт больший вес последним месяцам. Коэффициент 0.85 корректирует на сезонность."
  },

  "action": {
    "type": "write_column",
    "key_column": "Артикул",
    "new_column_name": "Прогноз Январь",
    "values": [
      ["СХ_анимезхс_54", 2911],
      ["СХ_андеграунд_100шт", 1530],
      ["СХ_романтика_54", 893],
      ... ВСЕ 134 строки ...
    ]
  },

  "confidence": 0.75,
  "warnings": ["Прогноз учитывает типичный январский спад. Если ваш бизнес не подвержен сезонности, результат может быть занижен."]
}
```

**ВАЖНО: в values должны быть ВСЕ строки из исходных данных, не только примеры!**"""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    def format_data_as_table(self, df: pd.DataFrame, column_names: List[str], max_rows: int = 1000) -> str:
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

        # v11.5: Явное соответствие колонок и букв Excel
        lines.append("КОЛОНКИ И БУКВЫ EXCEL:")
        for i, col in enumerate(column_names):
            letter = chr(65 + i)  # A, B, C, ...
            lines.append(f"  {letter} = {col}")
        lines.append("")

        # Заголовки с буквами колонок (Row - номер строки, НЕ колонка данных!)
        headers_with_letters = [f"{col} ({chr(65 + i)})" for i, col in enumerate(column_names)]
        lines.append("| Row | " + " | ".join(headers_with_letters) + " |")
        lines.append("|-----|" + "|".join(["---"] * len(column_names)) + "|")

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
                        # v11.5: Escape pipe character to prevent table parsing issues
                        val_str = str(val)[:30].replace('|', '/')
                        values.append(val_str)
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

        # История диалога - важно для follow-up вопросов типа "как ты это рассчитал?"
        history_text = ""
        if history:
            history_text = "\nИСТОРИЯ ДИАЛОГА (отвечай с учётом контекста!):\n"
            for h in history[-3:]:
                q = h.get('query', '')
                # v11.5: Увеличили до 500 символов чтобы сохранить контекст
                r = str(h.get('response', h.get('summary', '')))[:500]
                history_text += f"Пользователь: {q}\nТвой ответ: {r}\n---\n"
            history_text += "Если пользователь спрашивает 'как ты это рассчитал?' или 'почему?' - отвечай про ПРЕДЫДУЩИЙ вопрос!\n"

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

        # Translate copyable_formula if present
        if methodology.get('copyable_formula'):
            methodology['copyable_formula'] = self._translate_formula(methodology['copyable_formula'])

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
            "examples": examples,  # v11.0: Pass examples for frontend display
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

        elif action_type == "conditional_format":
            response["action_type"] = "conditional_format"
            response["conditional_rules"] = action.get("rules", [])

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

        elif action_type == "fill_column":
            # fill_column - write values directly to a specific column without key matching
            response["action_type"] = "fill_column"
            response["target_column"] = action.get("target_column")  # e.g., "E"
            response["column_name"] = action.get("column_name")  # e.g., "Прогноз"
            response["start_row"] = action.get("start_row", 2)  # Row to start writing (default: 2, after header)
            response["fill_values"] = action.get("values", [])  # List of values to write

        elif action_type == "fill_columns":
            # fill_columns - write values to multiple columns at once
            response["action_type"] = "fill_columns"
            response["start_row"] = action.get("start_row", 2)
            response["columns"] = action.get("columns", [])  # List of {target, name, values}

        elif action_type == "replace_data":
            # replace_data - full data replacement (for CSV split, restructure)
            response["action_type"] = "replace_data"
            response["structured_data"] = {
                "headers": action.get("headers", []),
                "rows": action.get("rows", [])
            }

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
            'SUMIFS': 'СУММЕСЛИМН', 'COUNTIFS': 'СЧЁТЕСЛИМН', 'AVERAGEIF': 'СРЗНАЧЕСЛИ',
            'SPLIT': 'РАЗДЕЛИТЬ', 'CONCATENATE': 'СЦЕПИТЬ', 'CONCAT': 'СЦЕП',
            'TRIM': 'СЖПРОБЕЛЫ', 'UPPER': 'ПРОПИСН', 'LOWER': 'СТРОЧН', 'PROPER': 'ПРОПНАЧ',
            'TEXT': 'ТЕКСТ', 'VALUE': 'ЗНАЧЕН', 'FIND': 'НАЙТИ', 'SEARCH': 'ПОИСК',
            'REPLACE': 'ЗАМЕНИТЬ', 'SUBSTITUTE': 'ПОДСТАВИТЬ', 'TRANSPOSE': 'ТРАНСП',
            'ARRAYFORMULA': 'МАССИВ', 'QUERY': 'QUERY', 'IMPORTRANGE': 'IMPORTRANGE'
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
