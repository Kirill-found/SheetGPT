"""
Тесты для Test-and-Heal loop
"""

import pytest
import asyncio
from app.services.ai_service import AIService
from app.services.formula_executor import MockFormulaExecutor

@pytest.mark.asyncio
async def test_healing_vlookup():
    """
    Тест: VLOOKUP с #N/A ошибкой
    """
    print("=== TEST: Healing VLOOKUP ===\n")
    
    service = AIService(openai_api_key="test-key", enable_test_and_heal=True)
    
    # Настраиваем mock executor чтобы симулировать #N/A
    service.executor.set_mock_error("VLOOKUP", "#N/A")
    
    result = await service.generate_actions(
        query="Найди цену товара из прайс-листа",
        sheet_data={
            "columns": ["Товар", "Количество"],
            "row_count": 10,
            "sheet_id": "test-sheet-123"
        }
    )
    
    print(f"Success: {result['success']}")
    
    if result.get("actions"):
        action = result["actions"][0]
        print(f"Formula: {action['config']['formula']}")
        
        if action.get("execution"):
            exec_info = action["execution"]
            print(f"Execution tested: {exec_info.get('tested')}")
            print(f"Execution success: {exec_info.get('success')}")
            print(f"Attempts: {exec_info.get('attempts')}")
            print(f"Healed: {exec_info.get('healed')}")
    
    print()


@pytest.mark.asyncio
async def test_healing_date():
    """
    Тест: Дата с #VALUE! ошибкой
    """
    print("=== TEST: Healing Date ===\n")
    
    service = AIService(openai_api_key="test-key", enable_test_and_heal=True)
    
    # Симулируем #VALUE! для даты
    service.executor.set_mock_error("TODAY", "#VALUE!")
    
    result = await service.generate_actions(
        query="Сколько дней прошло с даты начала?",
        sheet_data={
            "columns": ["Проект", "Дата начала"],
            "row_count": 5,
            "sheet_id": "test-sheet-456"
        }
    )
    
    print(f"Success: {result['success']}")
    
    if result.get("actions"):
        action = result["actions"][0]
        print(f"Formula: {action['config']['formula']}")
        
        if action.get("execution"):
            exec_info = action["execution"]
            print(f"Healed: {exec_info.get('healed')}")
    
    print()


@pytest.mark.asyncio
async def test_stats():
    """
    Тест: Проверка статистики
    """
    print("=== TEST: Statistics ===\n")
    
    service = AIService(openai_api_key="test-key", enable_test_and_heal=True)
    
    # Делаем несколько запросов
    for i in range(3):
        await service.generate_actions(
            f"Тест {i}",
            {
                "columns": ["A", "B"],
                "row_count": 10,
                "sheet_id": "test"
            }
        )
    
    stats = service.get_stats()
    
    print("Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print()


if __name__ == "__main__":
    asyncio.run(test_healing_vlookup())
    asyncio.run(test_healing_date())
    asyncio.run(test_stats())
    
    print("✅ All healing tests completed!")