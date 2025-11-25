"""
Тест двухэтапной архитектуры v8.0.0

Тестирует проблемные запросы:
1. "выдели строки где статус Ожидает" - должен выбрать highlight_rows
2. "топ 3 менеджера по сумме" - должен выбрать filter_top_n
3. "сколько у каждого менеджера оплаченных заказов" - должен выбрать aggregate_by_group
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent))

# Загружаем .env или используем hardcoded ключ для теста
env_path = Path(__file__).parent / ".env"
API_KEY = None

if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value
                if key == "OPENAI_API_KEY":
                    API_KEY = value

# Fallback: use environment variable or prompt user
if not API_KEY:
    API_KEY = os.getenv("OPENAI_API_KEY")
    if not API_KEY:
        print("ERROR: OPENAI_API_KEY not found. Set it in .env or environment.")
        sys.exit(1)

import pandas as pd
from openai import AsyncOpenAI
from app.services.two_stage_processor import TwoStageProcessor
from app.services.function_registry import FunctionRegistry


async def test_two_stage():
    print("=" * 70)
    print("ТЕСТ ДВУХЭТАПНОЙ АРХИТЕКТУРЫ v8.0.0")
    print("=" * 70)

    # Создаем клиент и процессор
    client = AsyncOpenAI(api_key=API_KEY)
    processor = TwoStageProcessor(client)
    registry = FunctionRegistry()

    # Тестовые данные
    df = pd.DataFrame({
        "Менеджер": ["Иванов", "Петров", "Сидоров", "Иванов", "Петров", "Козлов"],
        "Сумма": [10000, 15000, 8000, 12000, 9000, 25000],
        "Статус": ["Оплачен", "Ожидает", "Оплачен", "Отменен", "Оплачен", "Ожидает"],
        "Город": ["Москва", "Москва", "СПб", "Москва", "СПб", "Казань"]
    })

    column_names = df.columns.tolist()
    all_functions = registry.get_function_definitions()

    print(f"\n[DATA] Тестовая таблица:")
    print(df.to_string())
    print(f"\nКолонки: {column_names}")
    print(f"Всего функций: {len(all_functions)}")

    # Проблемные запросы для теста
    test_cases = [
        {
            "query": "выдели строки где статус Ожидает",
            "expected_function": "highlight_rows",
            "description": "Подсветка строк"
        },
        {
            "query": "топ 3 менеджера по сумме",
            "expected_function": "filter_top_n",
            "description": "Топ N"
        },
        {
            "query": "сколько у каждого менеджера заказов",
            "expected_function": "aggregate_by_group",
            "description": "Группировка с подсчетом"
        },
        {
            "query": "отсортируй по сумме от большего к меньшему",
            "expected_function": "sort_data",
            "description": "Сортировка"
        },
        {
            "query": "покажи заказы из Москвы",
            "expected_function": "filter_rows",
            "description": "Фильтрация"
        },
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'#' * 70}")
        print(f"ТЕСТ {i}: {test['description']}")
        print(f"Запрос: {test['query']}")
        print(f"Ожидаемая функция: {test['expected_function']}")
        print("#" * 70)

        try:
            result = await processor.process(
                query=test["query"],
                df=df,
                column_names=column_names,
                all_functions=all_functions
            )

            if result:
                selected_function = result["name"]
                is_correct = selected_function == test["expected_function"]

                status = "[PASS]" if is_correct else "[FAIL]"
                print(f"\n{status}")
                print(f"Выбрана функция: {selected_function}")
                print(f"Аргументы: {result['arguments']}")

                if result.get("understanding"):
                    print(f"Понимание: {result['understanding'].get('action_type')}")
                    print(f"Колонки: {result['understanding'].get('target_columns')}")
                    print(f"Условия: {result['understanding'].get('conditions')}")

                results.append({
                    "test": test["description"],
                    "passed": is_correct,
                    "expected": test["expected_function"],
                    "actual": selected_function
                })
            else:
                print("\n[FAIL] - функция не выбрана")
                results.append({
                    "test": test["description"],
                    "passed": False,
                    "expected": test["expected_function"],
                    "actual": None
                })

        except Exception as e:
            print(f"\n[ERROR]: {e}")
            results.append({
                "test": test["description"],
                "passed": False,
                "expected": test["expected_function"],
                "actual": f"ERROR: {e}"
            })

    # Итоги
    print("\n" + "=" * 70)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 70)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    for r in results:
        status = "[+]" if r["passed"] else "[-]"
        print(f"{status} {r['test']}: ожидалось {r['expected']}, получено {r['actual']}")

    print(f"\nРезультат: {passed}/{total} тестов пройдено ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n*** ВСЕ ТЕСТЫ ПРОЙДЕНЫ! ***")
    else:
        print(f"\n!!! {total - passed} тестов провалено !!!")


if __name__ == "__main__":
    asyncio.run(test_two_stage())
