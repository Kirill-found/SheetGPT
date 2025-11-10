"""
Отладочный тест для Intent Parser
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.intent_parser import IntentParser


def test_simple_sum_intent():
    """Отладка: почему простой запрос требует clarification?"""

    print("\n=== DEBUG: Simple Sum Intent ===\n")

    parser = IntentParser()

    query = "Посчитай сумму продаж"
    context = {
        "columns": ["A", "B", "C"],
        "column_names": ["Товар", "Продажи", "Регион"],
        "sample_data": [
            ["Товар A", 1000, "Москва"],
            ["Товар B", 2000, "СПб"]
        ],
        "row_count": 10
    }

    intent = parser.parse(query, context)

    print(f"Query: {query}")
    print(f"\nIntent type: {intent.type}")
    print(f"Intent certainty: {intent.certainty}")
    print(f"\nParameters:")

    for param_name, param in intent.parameters.items():
        print(f"  {param_name}:")
        print(f"    value: {param.value}")
        print(f"    certainty: {param.certainty}")
        print(f"    source: {param.source}")
        if param.certainty < 0.9:
            print(f"    [!] Below threshold 0.9 - needs clarification!")

    # Проверяем какие параметры нужно уточнить
    unclear_params = intent.get_unclear_parameters(threshold=0.9)

    print(f"\n[SUMMARY]")
    print(f"  Unclear parameters (< 0.9): {len(unclear_params)}")
    for param_name in unclear_params:
        param = intent.parameters[param_name]
        print(f"    - {param_name}: certainty={param.certainty}, value={param.value}")

    if intent.needs_clarification(threshold=0.9):
        print(f"\n[RESULT] System will ask questions")
    else:
        print(f"\n[RESULT] System can create action immediately!")


def test_average_intent():
    """Отладка: среднее значение"""

    print("\n=== DEBUG: Average Intent ===\n")

    parser = IntentParser()

    query = "Вычисли среднюю цену"
    context = {
        "columns": ["A", "B", "C"],
        "column_names": ["Товар", "Цена", "Количество"],
        "sample_data": [
            ["Товар A", 100, 5],
            ["Товар B", 200, 3]
        ],
        "row_count": 20
    }

    intent = parser.parse(query, context)

    print(f"Query: {query}")
    print(f"\nIntent type: {intent.type}")
    print(f"Intent certainty: {intent.certainty}")
    print(f"\nParameters:")

    for param_name, param in intent.parameters.items():
        print(f"  {param_name}:")
        print(f"    value: {param.value}")
        print(f"    certainty: {param.certainty}")
        if param.certainty < 0.9:
            print(f"    [!] Below threshold!")

    unclear_params = intent.get_unclear_parameters(threshold=0.9)
    print(f"\n[SUMMARY] Unclear parameters: {len(unclear_params)}")


if __name__ == "__main__":
    print("=" * 60)
    print("  INTENT PARSER DEBUG")
    print("=" * 60)

    test_simple_sum_intent()
    test_average_intent()

    print("\n" + "=" * 60)
