"""
Тесты для Conversation History функциональности

Демонстрируют работу контекстных запросов (reference queries)
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ai_service import AIService
from app.services.intent_store import intent_store


@pytest.mark.asyncio
async def test_retry_reference_query():
    """
    Тест: "попробуй еще раз" - повторяет предыдущий запрос

    Сценарий:
    1. Пользователь: "Посчитай сумму продаж" -> Action создан
    2. Пользователь: "попробуй еще раз" -> Тот же action создан
    """
    print("\n=== TEST: Retry Reference Query ===\n")

    service = AIService()

    sheet_data = {
        "columns": ["Товар", "Продажи", "Регион"],
        "sample_data": [
            ["Ноутбук", 45000, "Москва"],
            ["Монитор", 15000, "СПб"]
        ],
        "row_count": 10,
        "sheet_id": "test"
    }

    # ШАГ 1: Первый запрос
    print("STEP 1: Initial query")
    result1 = await service.generate_actions(
        query="Посчитай сумму продаж",
        sheet_data=sheet_data
    )

    print(f"Result 1: {result1.get('success')}")
    assert result1["success"] == True
    assert "conversation_id" in result1

    conversation_id = result1["conversation_id"]
    formula1 = result1["actions"][0]["config"]["formula"]
    print(f"Formula 1: {formula1}")
    print(f"Conversation ID: {conversation_id}")

    # ШАГ 2: Reference query "попробуй еще раз"
    print("\nSTEP 2: Retry query")
    result2 = await service.generate_actions(
        query="попробуй еще раз",
        sheet_data=sheet_data,
        conversation_id=conversation_id
    )

    print(f"Result 2: {result2.get('success')}")
    assert result2["success"] == True

    formula2 = result2["actions"][0]["config"]["formula"]
    print(f"Formula 2: {formula2}")

    # Проверки: формулы должны быть одинаковыми
    assert formula1 == formula2
    assert result2["actions"][0]["type"] == result1["actions"][0]["type"]

    print("\n[OK] Retry query correctly repeated the action!")


@pytest.mark.asyncio
async def test_modify_reference_query():
    """
    Тест: "измени на X" - модифицирует предыдущий запрос

    Сценарий:
    1. Пользователь: "Посчитай сумму продаж" -> SUM(B2:B10)
    2. Пользователь: "измени на среднее" -> AVERAGE(B2:B10)
    """
    print("\n=== TEST: Modify Reference Query ===\n")

    service = AIService()

    sheet_data = {
        "columns": ["Товар", "Продажи", "Регион"],
        "sample_data": [
            ["Ноутбук", 45000, "Москва"],
            ["Монитор", 15000, "СПб"]
        ],
        "row_count": 10,
        "sheet_id": "test"
    }

    # ШАГ 1: Первый запрос (сумма)
    print("STEP 1: Initial query (SUM)")
    result1 = await service.generate_actions(
        query="Посчитай сумму продаж",
        sheet_data=sheet_data
    )

    assert result1["success"] == True
    conversation_id = result1["conversation_id"]
    formula1 = result1["actions"][0]["config"]["formula"]
    print(f"Formula 1: {formula1}")
    assert "SUM" in formula1

    # ШАГ 2: Modify query "измени на среднее"
    print("\nSTEP 2: Modify query (AVERAGE)")
    result2 = await service.generate_actions(
        query="измени на среднее",
        sheet_data=sheet_data,
        conversation_id=conversation_id
    )

    assert result2["success"] == True
    formula2 = result2["actions"][0]["config"]["formula"]
    print(f"Formula 2: {formula2}")

    # Проверки: формула должна измениться на AVERAGE
    assert "AVERAGE" in formula2
    assert result2["actions"][0]["type"] == "insert_formula"

    print("\n[OK] Modify query correctly changed the operation!")


@pytest.mark.asyncio
async def test_conversation_without_history():
    """
    Тест: Запрос без conversation_id создает новый разговор

    Сценарий:
    1. Пользователь: "Посчитай сумму" (без conversation_id)
    2. Результат должен содержать новый conversation_id
    """
    print("\n=== TEST: New Conversation ===\n")

    service = AIService()

    sheet_data = {
        "columns": ["Товар", "Продажи"],
        "sample_data": [
            ["Товар A", 1000],
            ["Товар B", 2000]
        ],
        "row_count": 10,
        "sheet_id": "test"
    }

    # Запрос без conversation_id
    result = await service.generate_actions(
        query="Посчитай сумму продаж",
        sheet_data=sheet_data
    )

    # Проверки
    assert result["success"] == True
    assert "conversation_id" in result
    assert result["conversation_id"] is not None

    conversation_id = result["conversation_id"]
    print(f"Created conversation_id: {conversation_id}")

    # Проверяем что conversation создан в store
    conversation = intent_store.get_conversation(conversation_id)
    assert conversation is not None
    assert len(conversation.turns) == 1  # Один turn

    print("\n[OK] New conversation created successfully!")


@pytest.mark.asyncio
async def test_reference_query_without_previous_intent():
    """
    Тест: Reference query без предыдущего intent обрабатывается как обычный запрос

    Сценарий:
    1. Пользователь: "попробуй еще раз" (но нет предыдущего успешного intent)
    2. Система должна обработать как обычный запрос (вероятно попросит clarification)
    """
    print("\n=== TEST: Reference Query Without Previous Intent ===\n")

    service = AIService()

    sheet_data = {
        "columns": ["Товар", "Продажи"],
        "sample_data": [
            ["Товар A", 1000],
            ["Товар B", 2000]
        ],
        "row_count": 10,
        "sheet_id": "test"
    }

    # Создаем новый conversation
    conversation_id = intent_store.create_conversation()

    # Reference query без предыдущего intent
    result = await service.generate_actions(
        query="попробуй еще раз",
        sheet_data=sheet_data,
        conversation_id=conversation_id
    )

    # Результат: система не может обработать reference query без контекста
    # Так что либо success=False с clarification, либо fallback на GPT
    print(f"Result: {result.get('success')}, needs_clarification: {result.get('needs_clarification')}")

    # Это нормальное поведение - без контекста "попробуй еще раз" не имеет смысла
    assert result.get("success") == False or result.get("needs_clarification") == True

    print("\n[OK] Reference query without context handled correctly!")


@pytest.mark.asyncio
async def test_conversation_turn_saved():
    """
    Тест: Проверяем что turns сохраняются в conversation history

    Сценарий:
    1. Делаем 3 запроса в одном conversation
    2. Проверяем что все 3 turn сохранены
    """
    print("\n=== TEST: Conversation Turns Saved ===\n")

    service = AIService()

    sheet_data = {
        "columns": ["Товар", "Продажи", "Регион"],
        "sample_data": [
            ["Ноутбук", 45000, "Москва"],
            ["Монитор", 15000, "СПб"]
        ],
        "row_count": 10,
        "sheet_id": "test"
    }

    # ШАГ 1: Первый запрос
    result1 = await service.generate_actions(
        query="Посчитай сумму продаж",
        sheet_data=sheet_data
    )
    assert result1["success"] == True
    conversation_id = result1["conversation_id"]

    # ШАГ 2: Второй запрос
    result2 = await service.generate_actions(
        query="попробуй еще раз",
        sheet_data=sheet_data,
        conversation_id=conversation_id
    )
    assert result2["success"] == True

    # ШАГ 3: Третий запрос
    result3 = await service.generate_actions(
        query="измени на среднее",
        sheet_data=sheet_data,
        conversation_id=conversation_id
    )
    assert result3["success"] == True

    # Проверяем conversation history
    conversation = intent_store.get_conversation(conversation_id)
    assert conversation is not None
    assert len(conversation.turns) == 3

    print(f"\nConversation turns:")
    for i, turn in enumerate(conversation.turns, 1):
        print(f"  Turn {i}: {turn.query} -> success={turn.result.get('success')}")

    print("\n[OK] All turns saved in conversation history!")


if __name__ == "__main__":
    import asyncio

    print("=" * 60)
    print("  CONVERSATION HISTORY TESTS")
    print("=" * 60)

    asyncio.run(test_retry_reference_query())
    print("\n" + "=" * 60)

    asyncio.run(test_modify_reference_query())
    print("\n" + "=" * 60)

    asyncio.run(test_conversation_without_history())
    print("\n" + "=" * 60)

    asyncio.run(test_reference_query_without_previous_intent())
    print("\n" + "=" * 60)

    asyncio.run(test_conversation_turn_saved())
    print("\n" + "=" * 60)

    print("\n[SUCCESS] All Conversation History tests passed!")
    print("=" * 60)
