"""
Simple GPT Processor v1.0.0 - Упрощённая архитектура без паттернов

Архитектура:
┌─────────────────────────────────────────────────────┐
│              SIMPLE GPT PROCESSOR v1.0              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. Schema Extraction (локально, 0 tokens)          │
│     → Типы колонок, уникальные значения             │
│                                                     │
│  2. GPT-4o генерирует Pandas код (ВСЕГДА)           │
│     → Без классификации, без паттернов              │
│                                                     │
│  3. Execute + Self-Correction (до 3 попыток)        │
│                                                     │
│  4. POST-VALIDATION                                 │
│     → GPT проверяет релевантность ответа            │
│     → Если нет → retry с уточнением                 │
│                                                     │
└─────────────────────────────────────────────────────┘

Преимущества:
- Нет ограничений паттернов
- GPT понимает любые запросы
- Self-correction при ошибках
- Post-validation для качества
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
import os
import time
import logging
import re
import ast

from .schema_extractor import SchemaExtractor, get_schema_extractor

logger = logging.getLogger(__name__)


class SimpleGPTProcessor:
    """
    Упрощённый процессор на базе GPT-4o.
    Всё через LLM, без паттернов и классификации.
    """

    MODEL = "gpt-4o"  # Best quality
    MAX_RETRIES = 2

    # Безопасность: разрешённые модули
    ALLOWED_IMPORTS = {'pandas', 'pd', 'numpy', 'np', 'datetime', 'timedelta', 're', 'math'}

    # Запрещённые паттерны
    FORBIDDEN_PATTERNS = [
        r'\bexec\b', r'\beval\b', r'\bcompile\b',
        r'\b__\w+__\b', r'\bopen\b', r'\bfile\b',
        r'\bos\b', r'\bsys\b', r'\bsubprocess\b',
        r'\brequests\b', r'\burllib\b', r'\bsocket\b', r'\bpickle\b',
    ]

    SYSTEM_PROMPT = """Ты эксперт по анализу данных в Python/Pandas.

ЗАДАЧА: Напиши Python код для ответа на запрос пользователя.

ПРАВИЛА:
1. DataFrame уже загружен в переменную `df`
2. Используй ТОЛЬКО pandas, numpy, datetime, math
3. Результат сохрани в переменную `result`
4. НЕ используй print(), просто присвой результат
5. Обрабатывай NaN значения (dropna() или fillna())
6. Для чисел: pd.to_numeric(df[col], errors='coerce')

ВАЖНО - ПОНИМАЙ НАМЕРЕНИЕ:
- "какие/какой/что" → возвращай СПИСОК конкретных значений, НЕ количество!
- "сколько" → возвращай число (count)
- "покажи/выведи" → возвращай DataFrame или список
- "сумма/среднее/макс/мин" → возвращай число
- "топ N" → возвращай DataFrame с N строками
- "отсортируй" → возвращай отсортированный DataFrame
- "выдели/highlight" → возвращай DataFrame с отфильтрованными строками (сохраняй оригинальные индексы!)

ПРИМЕРЫ:

Запрос: "Какие продукты продал Иванов"
```python
result = df[df['Менеджер'] == 'Иванов']['Продукт'].unique().tolist()
```

Запрос: "Сколько продаж у Иванова"
```python
result = len(df[df['Менеджер'] == 'Иванов'])
```

Запрос: "Топ 5 менеджеров по продажам"
```python
result = df.groupby('Менеджер')['Сумма'].sum().nlargest(5).reset_index()
```

Запрос: "Покажи все заказы из Москвы"
```python
result = df[df['Город'] == 'Москва']
```

Возвращай ТОЛЬКО код внутри ```python ... ```, без объяснений.
"""

    VALIDATION_PROMPT = """Ты проверяешь качество ответа на запрос пользователя.

ЗАПРОС ПОЛЬЗОВАТЕЛЯ: {query}

РЕЗУЛЬТАТ: {result}

ЗАДАЧА: Ответь одним словом:
- "OK" - если результат отвечает на запрос пользователя
- "BAD" - если результат НЕ отвечает на запрос (неправильный тип данных, не та информация, пустой ответ)

Примеры:
- Запрос "какие продукты" → Результат ["Телефон", "Ноутбук"] → OK
- Запрос "какие продукты" → Результат 5 (число) → BAD (нужен список, не число)
- Запрос "сколько продаж" → Результат 42 → OK
- Запрос "сколько продаж" → Результат ["продукт1", "продукт2"] → BAD (нужно число)

Ответь ТОЛЬКО "OK" или "BAD":
"""

    # Ключевые слова для действий над данными (не анализ, а модификация)
    SORT_KEYWORDS = ['отсортируй', 'сортируй', 'сортировка', 'упорядочь', 'упорядочи', 'sort', 'order by']
    SORT_DESC_KEYWORDS = ['убыван', 'desc', 'z-a', 'я-а', 'больш к меньш', 'от большего', 'по убыванию']
    SORT_ASC_KEYWORDS = ['возраст', 'asc', 'a-z', 'а-я', 'меньш к больш', 'от меньшего', 'по возрастанию']

    # Freeze keywords
    FREEZE_KEYWORDS = ['заморозь', 'заморозить', 'закрепи', 'закрепить', 'freeze', 'pin']
    UNFREEZE_KEYWORDS = ['разморозь', 'разморозить', 'открепи', 'открепить', 'unfreeze', 'unpin']

    # Format keywords
    FORMAT_BOLD_KEYWORDS = ['жирн', 'bold', 'выдели жирным']
    FORMAT_HEADER_KEYWORDS = ['заголов', 'header', 'шапк', 'первую строку']
    FORMAT_COLOR_KEYWORDS = ['цвет', 'color', 'покрась', 'закрась']

    # Chart keywords
    CHART_KEYWORDS = ['диаграмм', 'график', 'chart', 'graph', 'построй', 'визуализ', 'plot']
    CHART_TYPES = {
        # Line charts
        'линейн': 'LINE', 'line': 'LINE', 'линия': 'LINE', 'тренд': 'LINE',
        # Bar charts (horizontal)
        'горизонтальн': 'BAR', 'bar': 'BAR',
        # Column charts (vertical bars) - default
        'столбч': 'COLUMN', 'column': 'COLUMN', 'столбик': 'COLUMN', 'гистограмм': 'COLUMN',
        # Pie charts
        'круговой': 'PIE', 'pie': 'PIE', 'пирог': 'PIE', 'долей': 'PIE', 'процент': 'PIE',
        # Area charts
        'область': 'AREA', 'area': 'AREA', 'заливк': 'AREA',
        # Scatter plots
        'точечн': 'SCATTER', 'scatter': 'SCATTER', 'разброс': 'SCATTER', 'корреляц': 'SCATTER',
        # Combo charts
        'комбинир': 'COMBO', 'combo': 'COMBO', 'смешан': 'COMBO',
    }

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Try loading from .env
            from pathlib import Path
            env_path = Path(__file__).parent.parent.parent / ".env"
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("OPENAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip()
                            os.environ["OPENAI_API_KEY"] = api_key
                            break

        self.client = AsyncOpenAI(api_key=api_key)
        self.schema_extractor = get_schema_extractor()

    def _detect_sort_action(self, query: str, column_names: List[str]) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой сортировки.
        Возвращает параметры сортировки или None.
        """
        query_lower = query.lower()

        # Проверяем наличие ключевых слов сортировки
        is_sort_query = any(kw in query_lower for kw in self.SORT_KEYWORDS)
        if not is_sort_query:
            return None

        logger.info(f"[SimpleGPT] Sort action detected: {query}")

        # Определяем порядок сортировки
        is_descending = any(kw in query_lower for kw in self.SORT_DESC_KEYWORDS)
        is_ascending = any(kw in query_lower for kw in self.SORT_ASC_KEYWORDS)

        # По умолчанию - по возрастанию, если явно не указано убывание
        sort_order = "DESCENDING" if is_descending and not is_ascending else "ASCENDING"

        # Ищем название колонки в запросе
        sort_column = None
        sort_column_index = None

        # Нормализуем названия колонок для поиска
        for idx, col_name in enumerate(column_names):
            col_lower = col_name.lower()
            # Проверяем точное вхождение или частичное
            if col_lower in query_lower or col_name in query:
                sort_column = col_name
                sort_column_index = idx
                logger.info(f"[SimpleGPT] Found sort column: '{col_name}' at index {idx}")
                break

        # Если колонка не найдена, пробуем найти по частичному совпадению
        if not sort_column:
            for idx, col_name in enumerate(column_names):
                # Разбиваем название колонки на слова
                col_words = col_name.lower().split()
                for word in col_words:
                    if len(word) > 2 and word in query_lower:
                        sort_column = col_name
                        sort_column_index = idx
                        logger.info(f"[SimpleGPT] Found sort column by partial match: '{col_name}' at index {idx}")
                        break
                if sort_column:
                    break

        if not sort_column:
            logger.warning(f"[SimpleGPT] Sort column not found in query. Available columns: {column_names}")
            return None

        return {
            "action_type": "sort",
            "column_name": sort_column,
            "column_index": sort_column_index,
            "sort_order": sort_order,
            "message": f"Сортировка по колонке '{sort_column}' ({('по убыванию' if sort_order == 'DESCENDING' else 'по возрастанию')})"
        }

    def _detect_freeze_action(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой заморозки строк/столбцов.
        """
        query_lower = query.lower()

        # Check for unfreeze first
        is_unfreeze = any(kw in query_lower for kw in self.UNFREEZE_KEYWORDS)
        if is_unfreeze:
            logger.info(f"[SimpleGPT] Unfreeze action detected: {query}")
            return {
                "action_type": "freeze",
                "freeze_rows": 0,
                "freeze_columns": 0,
                "message": "Закрепление снято"
            }

        # Check for freeze
        is_freeze = any(kw in query_lower for kw in self.FREEZE_KEYWORDS)
        if not is_freeze:
            return None

        logger.info(f"[SimpleGPT] Freeze action detected: {query}")

        # Determine what to freeze
        freeze_rows = 0
        freeze_columns = 0

        # Check for row freeze
        if any(word in query_lower for word in ['строк', 'строку', 'row', 'первую', 'шапку', 'заголов']):
            # Try to find number
            import re
            numbers = re.findall(r'(\d+)\s*(?:строк|строку|row)', query_lower)
            if numbers:
                freeze_rows = int(numbers[0])
            else:
                freeze_rows = 1  # Default to 1 row (header)

        # Check for column freeze
        if any(word in query_lower for word in ['столб', 'колонк', 'column', 'первый столб', 'первую колонк']):
            import re
            numbers = re.findall(r'(\d+)\s*(?:столб|колонк|column)', query_lower)
            if numbers:
                freeze_columns = int(numbers[0])
            else:
                freeze_columns = 1  # Default to 1 column

        # If nothing specific mentioned, freeze first row
        if freeze_rows == 0 and freeze_columns == 0:
            freeze_rows = 1

        message_parts = []
        if freeze_rows > 0:
            message_parts.append(f"{freeze_rows} строк" if freeze_rows > 1 else "первая строка")
        if freeze_columns > 0:
            message_parts.append(f"{freeze_columns} столбцов" if freeze_columns > 1 else "первый столбец")

        return {
            "action_type": "freeze",
            "freeze_rows": freeze_rows,
            "freeze_columns": freeze_columns,
            "message": f"Закреплено: {', '.join(message_parts)}"
        }

    def _detect_format_action(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой форматирования.
        """
        query_lower = query.lower()

        # Check for bold formatting
        is_bold = any(kw in query_lower for kw in self.FORMAT_BOLD_KEYWORDS)
        is_header = any(kw in query_lower for kw in self.FORMAT_HEADER_KEYWORDS)

        if not (is_bold or is_header):
            return None

        logger.info(f"[SimpleGPT] Format action detected: {query}")

        # Determine format type
        format_type = "bold_header" if (is_bold and is_header) or is_header else "bold"

        # Check for color
        color = None
        if any(kw in query_lower for kw in self.FORMAT_COLOR_KEYWORDS):
            # Try to detect color
            color_map = {
                'красн': '#FF0000', 'red': '#FF0000',
                'синий': '#0000FF', 'blue': '#0000FF',
                'зелен': '#00FF00', 'green': '#00FF00',
                'желт': '#FFFF00', 'yellow': '#FFFF00',
                'оранж': '#FFA500', 'orange': '#FFA500',
                'серый': '#808080', 'сер': '#808080', 'gray': '#808080', 'grey': '#808080',
            }
            for color_word, color_code in color_map.items():
                if color_word in query_lower:
                    color = color_code
                    break

        return {
            "action_type": "format",
            "format_type": format_type,
            "target_row": 1,  # First row (header)
            "bold": is_bold or is_header,
            "background_color": color,
            "message": f"Заголовки отформатированы" + (f" (цвет: {color})" if color else "")
        }

    def _detect_chart_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой создания диаграммы.
        Анализирует данные и определяет лучшие колонки для осей.
        """
        query_lower = query.lower()

        # Check for chart keywords
        is_chart_query = any(kw in query_lower for kw in self.CHART_KEYWORDS)
        if not is_chart_query:
            return None

        logger.info(f"[SimpleGPT] Chart action detected: {query}")

        # Determine chart type
        chart_type = 'COLUMN'  # Default
        for type_keyword, type_value in self.CHART_TYPES.items():
            if type_keyword in query_lower:
                chart_type = type_value
                logger.info(f"[SimpleGPT] Chart type detected: {type_value}")
                break

        # Analyze columns to find best X and Y axes
        numeric_cols = []
        categorical_cols = []
        date_cols = []

        for idx, col in enumerate(column_names):
            if idx >= len(df.columns):
                continue
            col_data = df.iloc[:, idx]

            # Check if column is numeric
            try:
                numeric_data = pd.to_numeric(col_data, errors='coerce')
                non_null_ratio = numeric_data.notna().sum() / len(numeric_data) if len(numeric_data) > 0 else 0
                if non_null_ratio > 0.5:
                    numeric_cols.append({'name': col, 'index': idx})
                    continue
            except:
                pass

            # Check if column is date-like
            col_lower = col.lower()
            if any(d in col_lower for d in ['дата', 'date', 'месяц', 'month', 'год', 'year', 'день', 'day', 'период', 'time']):
                date_cols.append({'name': col, 'index': idx})
                continue

            # Otherwise it's categorical
            categorical_cols.append({'name': col, 'index': idx})

        logger.info(f"[SimpleGPT] Column analysis: numeric={[c['name'] for c in numeric_cols]}, "
                   f"categorical={[c['name'] for c in categorical_cols]}, date={[c['name'] for c in date_cols]}")

        # Find columns mentioned in query
        mentioned_cols = []
        for idx, col in enumerate(column_names):
            col_lower = col.lower()
            # Check if column name or any significant word from it is in query
            if col_lower in query_lower or col in query:
                mentioned_cols.append({'name': col, 'index': idx})
            else:
                # Check for partial match
                for word in col_lower.split():
                    if len(word) > 2 and word in query_lower:
                        mentioned_cols.append({'name': col, 'index': idx})
                        break

        logger.info(f"[SimpleGPT] Columns mentioned in query: {[c['name'] for c in mentioned_cols]}")

        # Determine X and Y axes
        x_column = None
        y_columns = []

        # Priority for X axis: date > categorical mentioned > first categorical
        if date_cols:
            x_column = date_cols[0]
        elif categorical_cols:
            # Prefer mentioned categorical column
            for cat in categorical_cols:
                if cat in mentioned_cols:
                    x_column = cat
                    break
            if not x_column:
                x_column = categorical_cols[0]

        # Y axis: mentioned numeric columns, or all numeric if none mentioned
        for num in numeric_cols:
            if num in mentioned_cols:
                y_columns.append(num)

        if not y_columns and numeric_cols:
            # Take first 1-3 numeric columns
            y_columns = numeric_cols[:3]

        # For PIE charts, we need exactly one Y column and one X column
        if chart_type == 'PIE' and y_columns:
            y_columns = [y_columns[0]]

        # Generate title from query or columns
        title = ""
        if y_columns and x_column:
            y_names = ", ".join([c['name'] for c in y_columns])
            title = f"{y_names} по {x_column['name']}"
        elif y_columns:
            title = ", ".join([c['name'] for c in y_columns])

        # Build chart spec
        chart_spec = {
            "chart_type": chart_type,
            "title": title,
            "x_column_index": x_column['index'] if x_column else 0,
            "x_column_name": x_column['name'] if x_column else column_names[0],
            "y_column_indices": [c['index'] for c in y_columns] if y_columns else [1] if len(column_names) > 1 else [0],
            "y_column_names": [c['name'] for c in y_columns] if y_columns else [column_names[1] if len(column_names) > 1 else column_names[0]],
            "row_count": len(df),
            "col_count": len(column_names)
        }

        chart_type_names = {
            'LINE': 'линейный график',
            'BAR': 'горизонтальную гистограмму',
            'COLUMN': 'столбчатую диаграмму',
            'PIE': 'круговую диаграмму',
            'AREA': 'диаграмму с областями',
            'SCATTER': 'точечную диаграмму',
            'COMBO': 'комбинированный график'
        }

        message = f"Создаю {chart_type_names.get(chart_type, 'диаграмму')}: {title}"

        return {
            "action_type": "chart",
            "chart_spec": chart_spec,
            "message": message
        }

    async def process(
        self,
        query: str,
        df: pd.DataFrame,
        column_names: List[str],
        custom_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Главный метод обработки запроса.
        """
        start_time = time.time()

        try:
            # 0. Check for direct actions (sort, format, etc.) - no GPT needed
            sort_action = self._detect_sort_action(query, column_names)
            if sort_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning sort action: {sort_action}")
                return {
                    "success": True,
                    "action_type": "sort",
                    "result_type": "action",
                    "sort_column": sort_action["column_name"],
                    "sort_column_index": sort_action["column_index"],
                    "sort_order": sort_action["sort_order"],
                    "summary": sort_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for freeze action
            freeze_action = self._detect_freeze_action(query)
            if freeze_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning freeze action: {freeze_action}")
                return {
                    "success": True,
                    "action_type": "freeze",
                    "result_type": "action",
                    "freeze_rows": freeze_action["freeze_rows"],
                    "freeze_columns": freeze_action["freeze_columns"],
                    "summary": freeze_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for format action
            format_action = self._detect_format_action(query)
            if format_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning format action: {format_action}")
                return {
                    "success": True,
                    "action_type": "format",
                    "result_type": "action",
                    "format_type": format_action["format_type"],
                    "target_row": format_action["target_row"],
                    "bold": format_action["bold"],
                    "background_color": format_action["background_color"],
                    "summary": format_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # Check for chart action (needs df for column analysis)
            chart_action = self._detect_chart_action(query, column_names, df)
            if chart_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Returning chart action: {chart_action}")
                return {
                    "success": True,
                    "action_type": "chart",
                    "result_type": "action",
                    "chart_spec": chart_action["chart_spec"],
                    "summary": chart_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }

            # 1. Schema extraction
            logger.info(f"[SimpleGPT] Processing: {query[:50]}...")
            schema = self.schema_extractor.extract_schema(df)
            schema_prompt = self.schema_extractor.schema_to_prompt(schema)
            logger.info(f"[SimpleGPT] Schema: {schema['column_count']} cols, {schema['row_count']} rows")

            # 2. Generate and execute code (with retries)
            result = await self._generate_and_execute(
                query=query,
                df=df,
                schema_prompt=schema_prompt,
                custom_context=custom_context
            )

            if not result["success"]:
                return self._create_error_response(result.get("error", "Unknown error"), time.time() - start_time)

            # 3. Post-validation
            validation = await self._validate_result(query, result["result"])

            if validation == "BAD":
                logger.warning(f"[SimpleGPT] Post-validation failed, retrying with clarification...")
                # Retry with explicit clarification
                result = await self._generate_and_execute(
                    query=query,
                    df=df,
                    schema_prompt=schema_prompt,
                    custom_context=custom_context,
                    clarification="Предыдущий результат не соответствовал запросу. Убедись что возвращаешь правильный тип данных: список для 'какие', число для 'сколько', DataFrame для 'покажи'."
                )

            # 4. Format response
            elapsed = time.time() - start_time
            formatted_result = self._format_result(result["result"])
            result_type = self._get_result_type(result["result"])

            # Generate human-readable summary
            summary = self._generate_summary(result["result"], result_type, query)

            response = {
                "success": True,
                "result": formatted_result,
                "result_type": result_type,
                "summary": summary,
                "code": result.get("code"),
                "processing_time": f"{elapsed:.2f}s",
                "processor": "SimpleGPT v1.0",
                "validation": validation
            }

            # Check if this is a highlight query
            query_lower = query.lower()
            is_highlight_query = any(kw in query_lower for kw in ['выдели', 'выделить', 'подсвети', 'подсветить', 'highlight', 'mark'])

            if is_highlight_query:
                logger.info(f"[SimpleGPT] Highlight query detected: {query[:50]}")
                # Extract row indices from the result for highlighting
                highlight_rows = self._extract_highlight_rows(result["result"])
                if highlight_rows:
                    response["highlight_rows"] = highlight_rows
                    response["highlighted_count"] = len(highlight_rows)
                    response["highlight_color"] = "#FFFF00"  # Yellow
                    response["highlight_message"] = f"Выделено {len(highlight_rows)} строк"
                    response["result_type"] = "highlight"
                    logger.info(f"[SimpleGPT] Generated highlight_rows: {highlight_rows[:10]}... (total: {len(highlight_rows)})")

            # Add structured_data for tables/lists (only if NOT highlight query)
            if not is_highlight_query and result_type == "table" and isinstance(formatted_result, list):
                # Extract headers from first row keys (rows are dicts from DataFrame)
                headers = list(formatted_result[0].keys()) if formatted_result else []
                response["structured_data"] = {
                    "headers": headers,
                    "rows": formatted_result,
                    "display_mode": "sidebar_only" if len(formatted_result) <= 20 else "create_sheet"
                }
            elif result_type == "list" and isinstance(formatted_result, list):
                response["key_findings"] = formatted_result

            return response

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[SimpleGPT] Error: {str(e)}")
            return self._create_error_response(str(e), elapsed)

    async def _generate_and_execute(
        self,
        query: str,
        df: pd.DataFrame,
        schema_prompt: str,
        custom_context: Optional[str] = None,
        clarification: Optional[str] = None,
        previous_error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Генерирует и выполняет код с retry."""

        for attempt in range(self.MAX_RETRIES + 1):
            # Generate code
            code = await self._generate_code(
                query=query,
                schema_prompt=schema_prompt,
                custom_context=custom_context,
                clarification=clarification,
                previous_error=previous_error
            )

            if not code:
                return {"success": False, "error": "Не удалось сгенерировать код"}

            # Validate code safety
            is_safe, safety_error = self._validate_code_safety(code)
            if not is_safe:
                previous_error = f"Небезопасный код: {safety_error}"
                continue

            # Execute code
            try:
                result = self._execute_code(code, df)
                return {"success": True, "result": result, "code": code}
            except Exception as e:
                previous_error = f"{type(e).__name__}: {str(e)}"
                logger.warning(f"[SimpleGPT] Attempt {attempt + 1} failed: {previous_error}")
                continue

        return {"success": False, "error": previous_error}

    async def _generate_code(
        self,
        query: str,
        schema_prompt: str,
        custom_context: Optional[str] = None,
        clarification: Optional[str] = None,
        previous_error: Optional[str] = None
    ) -> Optional[str]:
        """Генерирует Pandas код через GPT-4o."""

        user_prompt = f"""СХЕМА ДАННЫХ:
{schema_prompt}

ЗАПРОС: {query}
"""

        if custom_context:
            user_prompt += f"\nКОНТЕКСТ: {custom_context}\n"

        if clarification:
            user_prompt += f"\nВАЖНО: {clarification}\n"

        if previous_error:
            user_prompt += f"\nПРЕДЫДУЩАЯ ОШИБКА (избегай её): {previous_error}\n"

        try:
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            content = response.choices[0].message.content

            # Extract code from markdown
            code_match = re.search(r'```python\s*(.*?)\s*```', content, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()

            # Try without markdown
            if 'result' in content and '=' in content:
                return content.strip()

            return None

        except Exception as e:
            logger.error(f"[SimpleGPT] Code generation error: {e}")
            return None

    async def _validate_result(self, query: str, result: Any) -> str:
        """Post-validation: проверяет релевантность результата."""

        # Format result for validation
        result_str = self._format_for_validation(result)

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cheaper model for validation
                messages=[
                    {"role": "user", "content": self.VALIDATION_PROMPT.format(
                        query=query,
                        result=result_str
                    )}
                ],
                temperature=0,
                max_tokens=10
            )

            answer = response.choices[0].message.content.strip().upper()
            return "OK" if "OK" in answer else "BAD"

        except Exception as e:
            logger.warning(f"[SimpleGPT] Validation error: {e}")
            return "OK"  # Default to OK if validation fails

    def _validate_code_safety(self, code: str) -> tuple:
        """Проверяет безопасность кода."""
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Forbidden pattern: {pattern}"

        # Check AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        return True, None

    def _execute_code(self, code: str, df: pd.DataFrame) -> Any:
        """Выполняет код в sandbox."""

        # Create safe namespace
        namespace = {
            'df': df.copy(),
            'pd': pd,
            'np': np,
            'result': None,
            'datetime': __import__('datetime'),
            'timedelta': __import__('datetime').timedelta,
            're': __import__('re'),
            'math': __import__('math'),
        }

        exec(code, namespace)

        result = namespace.get('result')
        if result is None:
            raise ValueError("Код не вернул результат (result = None)")

        return result

    def _format_result(self, result: Any) -> Any:
        """Форматирует результат для JSON."""

        if isinstance(result, pd.DataFrame):
            # Convert to list of dicts
            return result.to_dict(orient='records')
        elif isinstance(result, pd.Series):
            return result.tolist()
        elif isinstance(result, np.ndarray):
            return result.tolist()
        elif isinstance(result, (np.integer, np.floating)):
            return float(result)
        elif isinstance(result, list):
            return result
        else:
            return result

    def _format_for_validation(self, result: Any) -> str:
        """Форматирует результат для валидации."""

        if isinstance(result, pd.DataFrame):
            if len(result) > 5:
                return f"DataFrame с {len(result)} строками. Первые 3: {result.head(3).to_dict(orient='records')}"
            return str(result.to_dict(orient='records'))
        elif isinstance(result, (list, pd.Series)):
            items = list(result)[:10]
            return f"Список: {items}" + (f" (всего {len(result)})" if len(result) > 10 else "")
        elif isinstance(result, (int, float, np.integer, np.floating)):
            return f"Число: {result}"
        else:
            return str(result)[:500]

    def _get_result_type(self, result: Any) -> str:
        """Определяет тип результата."""

        if isinstance(result, pd.DataFrame):
            return "table"
        elif isinstance(result, (list, pd.Series)):
            return "list"
        elif isinstance(result, (int, float, np.integer, np.floating)):
            return "number"
        else:
            return "text"

    def _generate_summary(self, result: Any, result_type: str, query: str) -> str:
        """Генерирует человеко-читаемое описание результата."""

        if result_type == "number":
            # Для чисел - просто значение
            if isinstance(result, float):
                return f"{result:,.2f}".replace(",", " ")
            return str(result)

        elif result_type == "list":
            # Для списков - перечисление элементов
            items = list(result) if isinstance(result, pd.Series) else result
            if len(items) == 0:
                return "Ничего не найдено"
            elif len(items) <= 5:
                return ", ".join(str(item) for item in items)
            else:
                first_items = ", ".join(str(item) for item in items[:5])
                return f"{first_items} (и ещё {len(items) - 5})"

        elif result_type == "table":
            # Для таблиц - количество строк
            if isinstance(result, pd.DataFrame):
                return f"Найдено {len(result)} записей"
            elif isinstance(result, list):
                return f"Найдено {len(result)} записей"
            return "Таблица данных"

        else:
            # Текст
            return str(result)[:200] if result else "Результат обработан"

    def _extract_highlight_rows(self, result: Any) -> List[int]:
        """
        Извлекает номера строк для выделения из результата.
        Возвращает list[int] с номерами строк (1-based для Google Sheets, +1 для header).
        """
        try:
            if isinstance(result, pd.DataFrame):
                # Get original DataFrame indices and convert to Google Sheets row numbers
                # +2 because: +1 for 1-based indexing, +1 for header row
                indices = result.index.tolist()
                row_numbers = [int(idx) + 2 for idx in indices]
                logger.info(f"[SimpleGPT] Extracted {len(row_numbers)} row indices from DataFrame")
                return row_numbers
            elif isinstance(result, pd.Series):
                # Series with row indices
                indices = result.index.tolist()
                row_numbers = [int(idx) + 2 for idx in indices]
                return row_numbers
            elif isinstance(result, list):
                # If result is a list of row numbers
                if all(isinstance(x, (int, np.integer)) for x in result):
                    return [int(x) + 2 for x in result]
                # If result is list of dicts (from DataFrame.to_dict), can't extract indices
                return []
            else:
                return []
        except Exception as e:
            logger.error(f"[SimpleGPT] Error extracting highlight rows: {e}")
            return []

    def _create_error_response(self, error: str, elapsed: float) -> Dict[str, Any]:
        """Создаёт ответ об ошибке."""
        return {
            "success": False,
            "error": error,
            "processing_time": f"{elapsed:.2f}s",
            "processor": "SimpleGPT v1.0"
        }


# Singleton
_processor = None

def get_simple_gpt_processor() -> SimpleGPTProcessor:
    global _processor
    if _processor is None:
        _processor = SimpleGPTProcessor()
    return _processor
