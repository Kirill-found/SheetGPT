"""
Query Complexity Classifier v7.8.0 - TIER 2
Использует GPT-4o-mini для определения сложности запроса (simple vs complex)
Это позволяет выбирать между Function Calling (TIER 3A) и Code Generation (TIER 3B)
"""

from pathlib import Path
import os
import logging
from typing import List
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


async def classify_query_complexity(query: str, columns: List[str]) -> str:
    """
    Классифицирует сложность запроса с помощью GPT-4o-mini

    Returns:
        "simple" - запрос решается одной функцией (TIER 3A - Function Calling)
        "complex" - требует нескольких операций (TIER 3B - Code Generation)

    Args:
        query: Пользовательский запрос
        columns: Список названий колонок в таблице

    Cost: ~100 tokens (~$0.00001 per call)
    Speed: ~200ms
    """

    prompt = f"""Оцени сложность запроса для pandas DataFrame.

КРИТЕРИИ КЛАССИФИКАЦИИ:

SIMPLE - запрос решается ОДНОЙ функцией:
✅ "сумма всех заказов" → одна операция sum()
✅ "топ 5 клиентов по выручке" → одна операция nlargest()
✅ "средняя цена товаров" → одна операция mean()
✅ "сколько заказов у каждого менеджера" → одна операция groupby().count()
✅ "найди заказы где статус = Оплачен" → одна операция filter
✅ "максимальная сумма" → одна операция max()

COMPLEX - требует НЕСКОЛЬКИХ операций или кастомной логики:
❌ "найди заказы выше среднего в каждом городе" → нужно: 1) вычислить среднее, 2) отфильтровать внутри групп
❌ "сравни средние суммы по менеджерам и выдели лучшего" → нужно: 1) группировка, 2) сравнение, 3) выбор максимума
❌ "посчитай долю каждой категории в общей сумме" → нужно: 1) сумма по категориям, 2) общая сумма, 3) деление
❌ "топ 3 заказа в каждом городе" → нужно: 1) группировка по городам, 2) топ внутри каждой группы
❌ "средняя сумма оплаченных заказов у каждого менеджера, если больше 3 заказов" → нужно: 1) фильтр, 2) группировка, 3) условие на количество

ТЕКУЩИЙ ЗАПРОС:
Query: {query}
Columns: {columns}

ИНСТРУКЦИЯ:
Ответь ТОЛЬКО одним словом без объяснений:
- "simple" - если запрос решается одной функцией
- "complex" - если требуется несколько операций или условная логика

Твой ответ:"""

    try:
        logger.info(f"[TIER 2 CLASSIFIER] Analyzing query complexity: '{query[:50]}...'")

        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Дешёвая модель для классификации
            messages=[{"role": "user", "content": prompt}],
            temperature=0,  # Детерминированный результат
            max_tokens=10  # Нужно только одно слово
        )

        result = response.choices[0].message.content.strip().lower()

        # Validate response
        if "simple" in result:
            complexity = "simple"
        elif "complex" in result:
            complexity = "complex"
        else:
            # Default to simple if unclear (Function Calling safer fallback)
            logger.warning(f"[TIER 2 CLASSIFIER] Unclear response: '{result}', defaulting to 'simple'")
            complexity = "simple"

        logger.info(f"[TIER 2 CLASSIFIER] Result: {complexity.upper()}")
        logger.info(f"[TIER 2 CLASSIFIER] Tokens used: ~{response.usage.total_tokens}")

        return complexity

    except Exception as e:
        logger.error(f"[TIER 2 CLASSIFIER] Error: {str(e)}")
        # Fallback to simple on error (safer)
        logger.warning("[TIER 2 CLASSIFIER] Error occurred, defaulting to 'simple'")
        return "simple"


# Test function
async def test_classifier():
    """Тестовая функция для проверки классификатора"""

    test_cases = [
        {
            "query": "сумма всех заказов",
            "columns": ["Товар", "Сумма", "Статус"],
            "expected": "simple"
        },
        {
            "query": "топ 5 клиентов по выручке",
            "columns": ["Клиент", "Выручка", "Город"],
            "expected": "simple"
        },
        {
            "query": "сколько оплаченных заказов у каждого менеджера",
            "columns": ["Товар", "Менеджер", "Сумма", "Статус"],
            "expected": "simple"
        },
        {
            "query": "найди заказы выше среднего в каждом городе",
            "columns": ["Товар", "Город", "Сумма"],
            "expected": "complex"
        },
        {
            "query": "сравни средние суммы по менеджерам и выдели лучшего",
            "columns": ["Товар", "Менеджер", "Сумма"],
            "expected": "complex"
        },
        {
            "query": "топ 3 заказа в каждом городе",
            "columns": ["Товар", "Город", "Сумма"],
            "expected": "complex"
        }
    ]

    print("\n" + "="*80)
    print("TIER 2 Query Complexity Classifier - Test")
    print("="*80 + "\n")

    correct = 0
    total = len(test_cases)

    for test in test_cases:
        result = await classify_query_complexity(test["query"], test["columns"])
        status = "✅ PASS" if result == test["expected"] else "❌ FAIL"

        print(f"{status} Query: {test['query']}")
        print(f"      Expected: {test['expected']}, Got: {result}")
        print()

        if result == test["expected"]:
            correct += 1

    print("="*80)
    print(f"Results: {correct}/{total} correct ({correct/total*100:.1f}%)")
    print("="*80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_classifier())
