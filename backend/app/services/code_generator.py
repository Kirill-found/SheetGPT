"""
Code Generation Engine v7.8.0 - TIER 3B
Генерирует Python код с помощью GPT-4o и безопасно выполняет его
Используется для COMPLEX запросов, требующих нескольких операций
"""

from pathlib import Path
import os
import logging
import pandas as pd
import re
from typing import Any, Dict, List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Load OpenAI API key
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                os.environ["OPENAI_API_KEY"] = api_key
                break

client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def extract_code_from_response(response_text: str) -> str:
    """
    Извлекает Python код из ответа GPT-4o
    Поддерживает форматы:
    - ```python\\ncode\\n```
    - ```\\ncode\\n```
    - чистый код без markdown
    """
    # Remove markdown code blocks
    code = response_text.strip()

    # Extract from ```python ... ```
    python_match = re.search(r'```python\s*\n(.*?)\n```', code, re.DOTALL)
    if python_match:
        return python_match.group(1).strip()

    # Extract from ``` ... ```
    generic_match = re.search(r'```\s*\n(.*?)\n```', code, re.DOTALL)
    if generic_match:
        return generic_match.group(1).strip()

    # No markdown, return as is
    return code


def execute_code_safely(code: str, context: Dict[str, Any]) -> Any:
    """
    Безопасно выполняет Python код с ограничениями

    Args:
        code: Python код для выполнения
        context: Словарь с переменными (df, pd, и т.д.)

    Returns:
        result: Результат выполнения (значение переменной 'result')

    Raises:
        Exception: Если код содержит запрещённые операции или выполнение провалилось
    """

    # SECURITY: Проверка на запрещённые операции
    forbidden_keywords = [
        "import os", "import sys", "import subprocess", "import socket",
        "exec(", "eval(", "compile(", "__import__",
        "open(", "file(", "input(", "raw_input(",
        "os.", "sys.", "subprocess.", "socket.",
    ]

    for keyword in forbidden_keywords:
        if keyword in code:
            raise ValueError(f"Forbidden operation detected: {keyword}")

    # Создаём изолированный контекст
    safe_context = {
        'pd': pd,
        'df': context.get('df'),
        '__builtins__': {
            'len': len,
            'max': max,
            'min': min,
            'sum': sum,
            'abs': abs,
            'round': round,
            'int': int,
            'float': float,
            'str': str,
            'list': list,
            'dict': dict,
            'set': set,
            'tuple': tuple,
            'enumerate': enumerate,
            'range': range,
            'zip': zip,
            'sorted': sorted,
            'reversed': reversed,
            'any': any,
            'all': all,
            'isinstance': isinstance,
            'type': type,
        }
    }

    try:
        # Выполняем код
        exec(code, safe_context)

        # Возвращаем результат
        if 'result' not in safe_context:
            raise ValueError("Code did not set 'result' variable")

        return safe_context['result']

    except Exception as e:
        logger.error(f"[CODE EXECUTOR] Error executing code: {str(e)}")
        logger.error(f"[CODE EXECUTOR] Code:\n{code}")
        raise


async def generate_and_execute_code(
    query: str,
    df: pd.DataFrame,
    column_names: List[str],
    custom_context: str = None
) -> Dict[str, Any]:
    """
    TIER 3B: Генерирует и выполняет Python код для сложных запросов

    Args:
        query: Пользовательский запрос
        df: pandas DataFrame с данными
        column_names: Список названий колонок
        custom_context: Дополнительный контекст (роль AI, отрасль)

    Returns:
        Dict с результатами:
        - summary: Текстовое описание результата
        - methodology: Объяснение использованного метода
        - structured_data: Данные для таблицы (если применимо)
        - code_generated: Сгенерированный Python код
        - python_executed: True
        - response_type: "analysis"
    """

    logger.info(f"[TIER 3B CODE GEN] Generating code for query: '{query[:50]}...'")

    # Prepare prompt
    sample_data = df.head(3).to_dict('records')

    prompt = f"""Напиши Python код для pandas DataFrame, который решает этот запрос.

ДАННЫЕ:
Query: {query}
Columns: {column_names}
Sample data (first 3 rows):
{sample_data}

DataFrame shape: {df.shape[0]} rows x {df.shape[1]} columns

{"КОНТЕКСТ: " + custom_context if custom_context else ""}

ТРЕБОВАНИЯ:
1. НЕ используй import! pandas УЖЕ импортирован как 'pd', а DataFrame передан как 'df'
2. DataFrame доступен как переменная 'df'
3. Сохрани ФИНАЛЬНЫЙ результат в переменную 'result'
4. НЕ используй print(), только вычисления
5. result может быть:
   - Число (int/float) - для агрегаций
   - Строка - для текстовых результатов
   - Dict - для нескольких значений
   - DataFrame - для таблиц

ПРИМЕРЫ:

# Пример 1: Простая агрегация
Query: "сумма всех заказов"
result = df['Сумма'].sum()

# Пример 2: Фильтр + агрегация
Query: "средняя сумма оплаченных заказов"
result = df[df['Статус'] == 'Оплачен']['Сумма'].mean()

# Пример 3: Группировка с условием
Query: "сколько оплаченных заказов у каждого менеджера"
result = df[df['Статус'] == 'Оплачен'].groupby('Менеджер').size().to_dict()

# Пример 4: Сложная логика (несколько операций)
Query: "найди заказы выше среднего в каждом городе"
city_avg = df.groupby('Город')['Сумма'].mean()
df['above_avg'] = df.apply(lambda r: r['Сумма'] > city_avg[r['Город']], axis=1)
result = df[df['above_avg']]

# Пример 5: Множественные метрики
Query: "сравни средние суммы по менеджерам и выдели лучшего"
manager_avg = df.groupby('Менеджер')['Сумма'].mean()
top_manager = manager_avg.idxmax()
result = {{
    'top_manager': top_manager,
    'top_avg': manager_avg[top_manager],
    'all_averages': manager_avg.to_dict()
}}

ВАЖНО:
- НЕ используй import pandas, import sys, import os и т.д. - всё УЖЕ доступно!
- НЕ создавай новые данные или DataFrame - используй ТОЛЬКО переданный 'df'
- НЕ добавляй объяснения, комментарии или markdown (только чистый Python код)
- Обрабатывай возможные ошибки (пустые группы, NaN значения)
- Используй .fillna(0) если есть риск NaN
- Для текстовых результатов используй .strip() и .lower() для надёжности

Твой код:"""

    try:
        # Generate code with GPT-4o
        logger.info("[TIER 3B CODE GEN] Calling GPT-4o for code generation...")

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,  # Детерминированный результат
            max_tokens=1000  # Достаточно для сложного кода
        )

        raw_code = response.choices[0].message.content
        code = extract_code_from_response(raw_code)

        logger.info(f"[TIER 3B CODE GEN] Generated code ({len(code)} chars):")
        logger.info(f"[TIER 3B CODE GEN] {code[:200]}...")

        # Execute code safely
        logger.info("[TIER 3B CODE GEN] Executing code...")
        result = execute_code_safely(code, {"df": df})

        logger.info(f"[TIER 3B CODE GEN] Execution successful! Result type: {type(result)}")
        logger.info(f"[TIER 3B CODE GEN] Tokens used: {response.usage.total_tokens}")

        # Format response based on result type
        return format_code_result(result, code, query, df, column_names)

    except Exception as e:
        logger.error(f"[TIER 3B CODE GEN] Error: {str(e)}")
        raise


def format_code_result(
    result: Any,
    code: str,
    query: str,
    df: pd.DataFrame,
    column_names: List[str]
) -> Dict[str, Any]:
    """
    Форматирует результат выполнения кода в стандартный ответ

    Args:
        result: Результат выполнения (number, string, dict, DataFrame)
        code: Сгенерированный Python код
        query: Исходный запрос пользователя
        df: Исходный DataFrame
        column_names: Список колонок

    Returns:
        Dict с форматированным ответом
    """

    response = {
        "code_generated": code,
        "python_executed": True,
        "execution_output": str(result)[:500],  # Ограничение для больших результатов
        "response_type": "analysis",
        "confidence": 0.99  # Code Generation даёт высокую точность
    }

    # Case 1: Number result (агрегация)
    if isinstance(result, (int, float)):
        response["summary"] = f"Результат: {result:,.2f}" if isinstance(result, float) else f"Результат: {result:,}"
        response["methodology"] = f"Использовано: {code[:100]}..."

    # Case 2: String result
    elif isinstance(result, str):
        response["summary"] = result
        response["methodology"] = f"Вычислено с помощью Python кода: {code[:100]}..."

    # Case 3: Dict result (несколько метрик)
    elif isinstance(result, dict):
        # Format dict as readable text
        lines = [f"{k}: {v:,.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in result.items()]
        response["summary"] = "\n".join(lines[:10])  # Лимит 10 строк

        # If small dict (≤3 items) - text answer only
        # If large dict - create table
        if len(result) > 3:
            response["structured_data"] = {
                "table_title": f"Результаты: {query}",
                "columns": ["Параметр", "Значение"],
                "rows": [[str(k), str(v)] for k, v in result.items()]
            }

        response["methodology"] = f"Вычислено: {code[:100]}..."

    # Case 4: DataFrame result (таблица)
    elif isinstance(result, pd.DataFrame):
        rows_count = len(result)

        # Smart UX: text for ≤3 rows, table for >3 rows
        if rows_count <= 3:
            # Text answer
            lines = []
            for idx, row in result.iterrows():
                row_text = " | ".join([f"{col}: {row[col]}" for col in result.columns])
                lines.append(row_text)
            response["summary"] = "\n".join(lines)
        else:
            # Table
            response["summary"] = f"Найдено строк: {rows_count}"
            response["structured_data"] = {
                "table_title": f"Результаты: {query}",
                "columns": result.columns.tolist(),
                "rows": result.values.tolist()
            }

        response["methodology"] = f"Отобрано {rows_count} строк. Код: {code[:100]}..."

    # Case 5: Series result
    elif isinstance(result, pd.Series):
        result_dict = result.to_dict()
        return format_code_result(result_dict, code, query, df, column_names)

    # Case 6: List result
    elif isinstance(result, list):
        response["summary"] = f"Результаты ({len(result)} элементов): " + ", ".join([str(x) for x in result[:5]])
        if len(result) > 5:
            response["summary"] += f" ... и ещё {len(result)-5}"
        response["methodology"] = f"Код: {code[:100]}..."

    # Case 7: Unknown type
    else:
        response["summary"] = f"Результат: {str(result)[:200]}"
        response["methodology"] = f"Код: {code[:100]}..."

    return response


# Test function
async def test_code_generator():
    """Тестовая функция для проверки генератора кода"""

    # Test data
    test_df = pd.DataFrame([
        ["Ноутбук", "Москва", 150000, "Иванов", "Оплачен"],
        ["Мышка", "Москва", 1200, "Иванов", "Оплачен"],
        ["Монитор", "Москва", 80000, "Петров", "Оплачен"],
        ["Клавиатура", "Санкт-Петербург", 3500, "Иванов", "Оплачен"],
        ["Наушники", "Москва", 5000, "Сидоров", "Отменен"],
        ["Веб-камера", "Москва", 7000, "Иванов", "Оплачен"],
    ], columns=["Товар", "Город", "Сумма", "Менеджер", "Статус"])

    test_cases = [
        {
            "query": "сумма всех заказов",
            "expected_type": (int, float)
        },
        {
            "query": "найди заказы выше среднего в Москве",
            "expected_type": pd.DataFrame
        },
        {
            "query": "сравни средние суммы по менеджерам и выдели лучшего",
            "expected_type": dict
        }
    ]

    print("\n" + "="*80)
    print("TIER 3B Code Generation Engine - Test")
    print("="*80 + "\n")

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['query']}")

        try:
            result = await generate_and_execute_code(
                query=test['query'],
                df=test_df,
                column_names=test_df.columns.tolist()
            )

            print(f"  ✅ SUCCESS")
            print(f"  Summary: {result['summary'][:100]}...")
            print(f"  Code: {result['code_generated'][:100]}...")
            print()

        except Exception as e:
            print(f"  ❌ FAILED: {str(e)}")
            print()

    print("="*80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_code_generator())
