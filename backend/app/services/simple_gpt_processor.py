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
