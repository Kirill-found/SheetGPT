"""
Тесты для Interactive Builder API endpoints
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ai_service import AIService


@pytest.mark.asyncio
async def test_generate_action_high_certainty():
    """
    Тест: API generate_action с высокой certainty

    Ожидание: Сразу возвращает action без вопросов
    """
    print("\n=== TEST: API generate_action (High Certainty) ===\n")

    service = AIService()

    query = "Посчитай сумму продаж"
    sheet_data = {
        "columns": ["Товар", "Продажи", "Регион"],
        "sample_data": [
            ["Товар A", 1000, "Москва"],
            ["Товар B", 2000, "СПб"]
        ],
        "row_count": 10,
        "sheet_id": "test"
    }

    result = await service.generate_actions(query, sheet_data)

    print(f"Result: {result}")

    # Проверки
    assert result["success"] == True
    assert "actions" in result
    assert len(result["actions"]) > 0

    action = result["actions"][0]
    assert action["type"] == "insert_formula"
    assert "SUM" in action["config"]["formula"]  # Английская формула
    assert result["source"] == "interactive_builder"

    print("\n[OK] API returned action immediately!")


@pytest.mark.asyncio
async def test_generate_action_needs_clarification():
    """
    Тест: API generate_action с низкой certainty

    Ожидание: Возвращает вопросы для clarification
    """
    print("\n=== TEST: API generate_action (Needs Clarification) ===\n")

    service = AIService()

    query = "Найди цену товара"
    sheet_data = {
        "columns": ["Товар", "Цена", "Количество"],
        "sample_data": [
            ["Товар A", 100, 5],
            ["Товар B", 200, 3]
        ],
        "row_count": 10,
        "sheet_id": "test"
    }

    result = await service.generate_actions(query, sheet_data)

    print(f"Result keys: {result.keys()}")
    print(f"Needs clarification: {result.get('needs_clarification')}")

    if result.get("needs_clarification"):
        print(f"Intent ID: {result.get('intent_id')}")
        print(f"Questions: {len(result.get('questions', []))}")

    # Проверки
    assert result["success"] == False
    assert result.get("needs_clarification") == True
    assert "intent_id" in result
    assert "questions" in result
    assert len(result["questions"]) > 0

    print("\n[OK] API returned clarification questions!")


@pytest.mark.asyncio
async def test_clarification_flow_end_to_end():
    """
    Тест: Полный flow с clarification

    1. Запрос возвращает вопросы
    2. Отправляем ответы
    3. Получаем action
    """
    print("\n=== TEST: Full Clarification Flow ===\n")

    service = AIService()

    # ШАГ 1: Запрос возвращает вопросы
    query = "Найди цену товара"
    sheet_data = {
        "columns": ["Товар", "Цена", "Количество"],
        "sample_data": [
            ["Товар A", 100, 5],
            ["Товар B", 200, 3]
        ],
        "row_count": 10,
        "sheet_id": "test"
    }

    result1 = await service.generate_actions(query, sheet_data)

    print("STEP 1: Got clarification questions")
    assert result1.get("needs_clarification") == True
    assert "intent_id" in result1

    intent_id = result1["intent_id"]

    # ШАГ 2: Отправляем ответы
    answers = {
        "lookup_column": "Товар",
        "result_column": "Цена"
    }

    result2 = await service.apply_clarification(intent_id, answers)

    print("STEP 2: Applied answers, got action")
    print(f"Result: {result2}")

    # Проверки
    assert result2["success"] == True
    assert "actions" in result2
    assert len(result2["actions"]) > 0

    action = result2["actions"][0]
    assert action["type"] == "insert_formula"
    assert "VLOOKUP" in action["config"]["formula"]  # Английская формула
    assert action["confidence"] >= 0.90

    print("\n[OK] Full clarification flow works!")


if __name__ == "__main__":
    import asyncio

    print("=" * 60)
    print("  API ACTIONS TESTS")
    print("=" * 60)

    asyncio.run(test_generate_action_high_certainty())
    asyncio.run(test_generate_action_needs_clarification())
    asyncio.run(test_clarification_flow_end_to_end())

    print("\n" + "=" * 60)
    print("  [SUCCESS] ALL API TESTS PASSED!")
    print("=" * 60)
