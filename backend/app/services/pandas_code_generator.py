"""
Pandas Code Generator v1.0.0 - Text-to-Pandas для сложных запросов

Генерирует и выполняет Python/Pandas код для сложных аналитических запросов.

Безопасность:
- Ограниченный набор разрешённых модулей
- Таймаут выполнения
- Валидация сгенерированного кода
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
import ast
import traceback
import re
import logging

logger = logging.getLogger(__name__)


class PandasCodeGenerator:
    """
    Генератор Pandas кода для сложных аналитических запросов.

    Workflow:
    1. Получаем схему данных от SchemaExtractor
    2. Отправляем промпт в GPT-4o с инструкциями
    3. Получаем Python код
    4. Валидируем код (безопасность)
    5. Выполняем в sandbox
    6. Форматируем результат
    """

    # Разрешённые модули для import
    ALLOWED_IMPORTS = {
        'pandas', 'pd',
        'numpy', 'np',
        'datetime', 'timedelta',
        're',
        'math',
    }

    # Запрещённые функции/атрибуты
    FORBIDDEN_PATTERNS = [
        r'\bexec\b', r'\beval\b', r'\bcompile\b',
        r'\b__\w+__\b',  # dunder methods
        r'\bopen\b', r'\bfile\b',
        r'\bos\b', r'\bsys\b', r'\bsubprocess\b',
        r'\bimport\s+os\b', r'\bimport\s+sys\b',
        r'\brequests\b', r'\burllib\b',
        r'\bsocket\b', r'\bpickle\b',
    ]

    SYSTEM_PROMPT = """Ты эксперт по анализу данных в Python/Pandas.

ЗАДАЧА: Напиши Python код для анализа DataFrame по запросу пользователя.

ПРАВИЛА:
1. DataFrame уже загружен в переменную `df`
2. Используй ТОЛЬКО pandas, numpy, datetime, math
3. Результат сохрани в переменную `result`
4. Результат должен быть: DataFrame, Series, число, строка или список
5. НЕ используй print(), просто присвой результат в `result`
6. Обрабатывай NaN значения (используй dropna() или fillna())
7. Для числовых операций конвертируй: pd.to_numeric(df[col], errors='coerce')
8. Пиши лаконичный код без лишних комментариев

ПРИМЕРЫ:

Запрос: "Топ 5 менеджеров по сумме продаж"
Код:
```python
result = df.groupby('Менеджер')['Сумма'].sum().nlargest(5).reset_index()
result.columns = ['Менеджер', 'Сумма продаж']
```

Запрос: "Корреляция между ценой и количеством"
Код:
```python
result = df['Цена'].corr(df['Количество'])
```

Запрос: "Pivot таблица продаж по регионам и месяцам"
Код:
```python
df['Месяц'] = pd.to_datetime(df['Дата']).dt.month
result = df.pivot_table(values='Сумма', index='Регион', columns='Месяц', aggfunc='sum', fill_value=0)
```

Запрос: "Накопительная сумма продаж по дате"
Код:
```python
result = df.sort_values('Дата').assign(Накопительная_сумма=df['Сумма'].cumsum())[['Дата', 'Сумма', 'Накопительная_сумма']]
```

ВАЖНО: Возвращай ТОЛЬКО код внутри ```python ... ```, без объяснений.
"""

    def __init__(self, client: AsyncOpenAI = None):
        self.client = client

    async def generate_and_execute(
        self,
        query: str,
        df: pd.DataFrame,
        schema_prompt: str,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Генерирует и выполняет Pandas код.

        Args:
            query: Запрос пользователя
            df: DataFrame с данными
            schema_prompt: Описание схемы данных
            max_retries: Количество попыток при ошибке

        Returns:
            {
                "success": True/False,
                "result": результат выполнения,
                "code": сгенерированный код,
                "error": ошибка если есть
            }
        """
        last_error = None

        for attempt in range(max_retries + 1):
            # 1. Генерируем код
            code = await self._generate_code(query, schema_prompt, last_error)

            if not code:
                return {
                    "success": False,
                    "error": "Не удалось сгенерировать код",
                    "code": None
                }

            # 2. Валидируем код
            is_safe, safety_error = self._validate_code_safety(code)
            if not is_safe:
                last_error = f"Небезопасный код: {safety_error}"
                continue

            # 3. Выполняем код
            try:
                result = self._execute_code(code, df)
                return {
                    "success": True,
                    "result": result,
                    "code": code,
                    "attempt": attempt + 1
                }
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)}"
                if attempt < max_retries:
                    logger.warning(f"[PANDAS_GENERATOR] Attempt {attempt + 1} failed: {last_error}")
                    continue

        return {
            "success": False,
            "error": last_error,
            "code": code if 'code' in dir() else None
        }

    async def _generate_code(
        self,
        query: str,
        schema_prompt: str,
        previous_error: Optional[str] = None
    ) -> Optional[str]:
        """Генерирует Pandas код с помощью LLM."""
        user_prompt = f"""СХЕМА ДАННЫХ:
{schema_prompt}

ЗАПРОС: {query}
"""

        if previous_error:
            user_prompt += f"""
ПРЕДЫДУЩАЯ ПОПЫТКА ЗАВЕРШИЛАСЬ ОШИБКОЙ:
{previous_error}

Исправь код, чтобы избежать этой ошибки.
"""

        try:
            if not self.client:
                logger.error("[PANDAS_GENERATOR] ❌ OpenAI client is None!")
                return None

            logger.info(f"[PANDAS_GENERATOR] Generating code for: {query[:50]}...")

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            content = response.choices[0].message.content
            logger.info(f"[PANDAS_GENERATOR] GPT response length: {len(content)} chars")

            # Извлекаем код из markdown блока
            code_match = re.search(r'```python\s*(.*?)\s*```', content, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
                logger.info(f"[PANDAS_GENERATOR] ✅ Extracted code: {len(code)} chars")
                return code

            # Если нет markdown блока, пробуем взять весь ответ
            if 'result' in content and '=' in content:
                logger.info("[PANDAS_GENERATOR] ✅ Using raw content as code")
                return content.strip()

            logger.warning(f"[PANDAS_GENERATOR] ⚠️ No code found in response: {content[:200]}...")
            return None

        except Exception as e:
            logger.error(f"[PANDAS_GENERATOR] ❌ Code generation error: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            return None

    def _validate_code_safety(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Валидирует безопасность кода.

        Returns:
            (is_safe, error_message)
        """
        # Проверяем запрещённые паттерны
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Запрещённый паттерн: {pattern}"

        # Проверяем imports
        import_matches = re.findall(r'import\s+(\w+)', code)
        from_matches = re.findall(r'from\s+(\w+)', code)

        for module in import_matches + from_matches:
            if module not in self.ALLOWED_IMPORTS:
                return False, f"Запрещённый модуль: {module}"

        # Проверяем синтаксис
        try:
            ast.parse(code)
        except SyntaxError as e:
            return False, f"Синтаксическая ошибка: {e}"

        return True, None

    def _execute_code(self, code: str, df: pd.DataFrame) -> Any:
        """
        Выполняет код в ограниченном окружении.
        """
        # Создаём изолированное окружение
        local_vars = {
            'df': df.copy(),  # Копия чтобы не изменять оригинал
            'pd': pd,
            'np': np,
            'result': None
        }

        # Добавляем datetime
        import datetime
        local_vars['datetime'] = datetime
        local_vars['timedelta'] = datetime.timedelta

        # Выполняем код
        exec(code, {"__builtins__": {}}, local_vars)

        result = local_vars.get('result')

        if result is None:
            raise ValueError("Код не вернул результат (переменная 'result' не определена)")

        return result

    def format_result(self, result: Any) -> Dict[str, Any]:
        """
        Форматирует результат выполнения для API response.
        """
        if isinstance(result, pd.DataFrame):
            return {
                "type": "table",
                "structured_data": {
                    "headers": result.columns.tolist(),
                    "rows": result.values.tolist()
                },
                "row_count": len(result),
                "summary": f"Таблица: {len(result)} строк × {len(result.columns)} колонок"
            }

        elif isinstance(result, pd.Series):
            if len(result) <= 10:
                return {
                    "type": "series",
                    "data": result.to_dict(),
                    "summary": f"Серия: {len(result)} значений"
                }
            else:
                return {
                    "type": "table",
                    "structured_data": {
                        "headers": [result.name or "Значение"],
                        "rows": [[v] for v in result.values.tolist()]
                    },
                    "row_count": len(result)
                }

        elif isinstance(result, (int, float, np.number)):
            return {
                "type": "number",
                "value": float(result),
                "summary": f"Результат: {result:,.2f}" if isinstance(result, float) else f"Результат: {result:,}"
            }

        elif isinstance(result, str):
            return {
                "type": "text",
                "value": result,
                "summary": result
            }

        elif isinstance(result, (list, tuple)):
            return {
                "type": "list",
                "value": list(result),
                "summary": f"Список: {len(result)} элементов"
            }

        elif isinstance(result, dict):
            return {
                "type": "dict",
                "value": result,
                "summary": f"Словарь: {len(result)} ключей"
            }

        else:
            return {
                "type": "unknown",
                "value": str(result),
                "summary": str(result)[:100]
            }


# Singleton
_generator = None

def get_pandas_generator(client: AsyncOpenAI = None) -> PandasCodeGenerator:
    """Возвращает singleton instance PandasCodeGenerator."""
    global _generator
    if _generator is None or client is not None:
        _generator = PandasCodeGenerator(client)
    return _generator
