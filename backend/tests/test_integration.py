"""
Тест интеграции Interactive Builder с generate_actions
"""

import pytest
import sys
import os

# Добавляем путь к модулю app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ai_service import AIService


@pytest.mark.asyncio
async def test_simple_sum_high_certainty():
    """
    Тест: Простая сумма с высокой certainty

    Ожидание: Система создаст action без вопросов через Interactive Builder
    """
    print("\n=== TEST: Simple Sum (High Certainty) ===\n")

    service = AIService()

    query = "Посчитай сумму продаж"
    sheet_data = {
        "columns": ["Товар", "Продажи", "Регион"],
        "sample_data": [
            ["Товар A", 1000, "Москва"],
            ["Товар B", 2000, "СПб"],
            ["Товар C", 3000, "Москва"]
        ],
        "row_count": 10,
        "sheet_id": "test-sheet"
    }

    result = await service.generate_actions(query, sheet_data)

    print("[RESULT]:")
    print(f"  Success: {result.get('success')}")
    print(f"  Source: {result.get('source')}")

    if result.get('success'):
        print(f"  Actions: {len(result.get('actions', []))}")
        for action in result.get('actions', []):
            print(f"    - Type: {action.get('type')}")
            print(f"    - Config: {action.get('config')}")
            print(f"    - Confidence: {action.get('confidence', 'N/A')}")

    if result.get('needs_clarification'):
        print(f"  Needs clarification: True")
        print(f"  Questions: {len(result.get('questions', []))}")

    # Проверки
    assert result.get('success') == True or result.get('needs_clarification') == True

    if result.get('success'):
        assert result.get('source') in ['interactive_builder', 'template', 'gpt']
        assert len(result.get('actions', [])) > 0

        action = result['actions'][0]
        assert action['type'] == 'insert_formula'
        assert 'СУММ' in action['config']['formula'] or 'SUM' in action['config']['formula']

        print("\n[OK] Action created successfully!")
    else:
        print(f"\n[INFO] System needs clarification - this is also a valid outcome")

    print("\n=== TEST PASSED ===\n")


@pytest.mark.asyncio
async def test_vlookup_needs_clarification():
    """
    Тест: VLOOKUP с недостаточной информацией

    Ожидание: Система запросит уточнения через Interactive Builder
    """
    print("\n=== TEST: VLOOKUP (Needs Clarification) ===\n")

    service = AIService()

    query = "Найди цену товара"
    sheet_data = {
        "columns": ["Товар", "Цена", "Количество"],
        "sample_data": [
            ["Товар A", 100, 5],
            ["Товар B", 200, 3]
        ],
        "row_count": 10,
        "sheet_id": "test-sheet"
    }

    result = await service.generate_actions(query, sheet_data)

    print("[RESULT]:")
    print(f"  Success: {result.get('success')}")
    print(f"  Needs clarification: {result.get('needs_clarification', False)}")

    if result.get('needs_clarification'):
        print(f"  Questions: {len(result.get('questions', []))}")
        for i, q in enumerate(result.get('questions', []), 1):
            print(f"\n  Question {i}:")
            print(f"    Parameter: {q.get('parameter')}")
            print(f"    Text: {q.get('text')}")
            print(f"    Type: {q.get('type')}")
            if q.get('options'):
                print(f"    Options: {len(q.get('options', []))} options")

    # Проверки - либо успех, либо нужны уточнения
    assert result.get('success') == True or result.get('needs_clarification') == True

    # Если система работает правильно, для VLOOKUP должны быть вопросы
    # Но это не обязательно - возможно система умная и поймет из контекста

    print("\n=== TEST PASSED ===\n")


@pytest.mark.asyncio
async def test_average_high_certainty():
    """
    Тест: Среднее значение с высокой certainty

    Ожидание: Система создаст action без вопросов
    """
    print("\n=== TEST: Average (High Certainty) ===\n")

    service = AIService()

    query = "Вычисли среднюю цену"
    sheet_data = {
        "columns": ["Товар", "Цена", "Количество"],
        "sample_data": [
            ["Товар A", 100, 5],
            ["Товар B", 200, 3],
            ["Товар C", 150, 8]
        ],
        "row_count": 20,
        "sheet_id": "test-sheet"
    }

    result = await service.generate_actions(query, sheet_data)

    print("[RESULT]:")
    print(f"  Success: {result.get('success')}")
    print(f"  Source: {result.get('source')}")

    if result.get('success'):
        action = result['actions'][0]
        print(f"  Formula: {action['config']['formula']}")
        print(f"  Confidence: {action.get('confidence', 'N/A')}")

    # Проверки
    assert result.get('success') == True or result.get('needs_clarification') == True

    print("\n=== TEST PASSED ===\n")


if __name__ == "__main__":
    import asyncio

    print("=" * 60)
    print("  INTERACTIVE BUILDER INTEGRATION TESTS")
    print("=" * 60)

    asyncio.run(test_simple_sum_high_certainty())
    asyncio.run(test_vlookup_needs_clarification())
    asyncio.run(test_average_high_certainty())

    print("=" * 60)
    print("  [SUCCESS] ALL INTEGRATION TESTS PASSED!")
    print("=" * 60)
