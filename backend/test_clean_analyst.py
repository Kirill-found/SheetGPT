"""
Тест CleanAnalyst - локальный запуск без сервера
"""

import asyncio
import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from app.services.clean_analyst import CleanAnalyst
from app.config import settings


# Тестовые данные - реальный пример
TEST_DATA = {
    "columns": ["Артикул", "Октябрь", "Ноябрь", "Декабрь"],
    "rows": [
        ["СХ_анимезхс_54", 2245, 3282, 3913],
        ["СХ_андеграунд_100шт", 1200, 1650, 2100],
        ["СХ_романтика_54", 950, 1100, 1050],
        ["СХ_андеграунд_скинхед_54", 800, 950, 1200],
        ["СХ_аниме_ДА_zxc_красный_54", 600, 850, 1100],
        ["СХ_ретро_стиль_30", 400, 500, 650],
        ["СХ_это_знак_54", 300, 400, 550],
        ["СХ_аниме_100шт", 250, 350, 500],
        ["СХ_Берсерк_54шт", 200, 400, 700],
        ["СХ_bmw_m5_f90_54шт", 150, 250, 400],
    ]
}


async def test_forecast():
    """Тест прогнозирования"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Прогноз на январь")
    print("="*60)

    df = pd.DataFrame(TEST_DATA["rows"], columns=TEST_DATA["columns"])
    print(f"\nВходные данные:\n{df.to_string()}\n")

    analyst = CleanAnalyst(api_key=settings.OPENAI_API_KEY)

    result = await analyst.analyze(
        query="Спрогнозируй заказы на январь на основе данных за предыдущие месяцы",
        df=df,
        column_names=TEST_DATA["columns"]
    )

    if not result["success"]:
        print(f"❌ ОШИБКА: {result.get('error')}")
        return False

    gpt_response = result["gpt_response"]

    print(f"⏱️ Время: {result['processing_time']}")
    print(f"\n🧠 THINKING:\n{gpt_response.get('thinking', 'N/A')}")
    print(f"\n📊 METHODOLOGY:")
    methodology = gpt_response.get('methodology', {})
    print(f"   Name: {methodology.get('name', 'N/A')}")
    print(f"   Reason: {methodology.get('reason', 'N/A')}")
    print(f"   Formula: {methodology.get('formula', 'N/A')}")

    print(f"\n📝 EXAMPLES:")
    for ex in gpt_response.get('examples', [])[:3]:
        print(f"   • {ex.get('item', 'N/A')}")
        print(f"     Input: {ex.get('input', 'N/A')}")
        print(f"     Calculation: {ex.get('calculation', 'N/A')}")
        print(f"     Result: {ex.get('result', 'N/A')}")

    print(f"\n📋 RESULT:")
    result_data = gpt_response.get('result', {})
    print(f"   Summary: {result_data.get('summary', 'N/A')}")
    print(f"   Details: {result_data.get('details', 'N/A')[:200]}...")

    print(f"\n🎯 ACTION:")
    action = gpt_response.get('action', {})
    print(f"   Type: {action.get('type', 'N/A')}")
    if action.get('type') == 'write_column':
        print(f"   Key column: {action.get('key_column', 'N/A')}")
        print(f"   New column: {action.get('new_column_name', 'N/A')}")
        values = action.get('values', [])
        print(f"   Values ({len(values)} rows):")
        for v in values[:5]:
            print(f"      {v}")
        if len(values) > 5:
            print(f"      ... и ещё {len(values) - 5}")

    print(f"\n⚠️ WARNINGS: {gpt_response.get('warnings', [])}")
    print(f"📈 CONFIDENCE: {gpt_response.get('confidence', 'N/A')}")

    # Проверяем трансформацию в формат фронтенда
    print("\n" + "-"*40)
    print("FRONTEND FORMAT:")
    frontend = analyst.transform_to_frontend_format(gpt_response, result['processing_time'])
    print(f"   action_type: {frontend.get('action_type')}")
    print(f"   merge_by_key: {frontend.get('merge_by_key')}")
    print(f"   write_headers: {frontend.get('write_headers')}")
    print(f"   write_data count: {len(frontend.get('write_data', []))}")

    return True


async def test_analysis():
    """Тест анализа данных"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Анализ данных")
    print("="*60)

    df = pd.DataFrame(TEST_DATA["rows"], columns=TEST_DATA["columns"])

    analyst = CleanAnalyst(api_key=settings.OPENAI_API_KEY)

    result = await analyst.analyze(
        query="Какой артикул показывает наибольший рост? Проанализируй динамику.",
        df=df,
        column_names=TEST_DATA["columns"]
    )

    if not result["success"]:
        print(f"❌ ОШИБКА: {result.get('error')}")
        return False

    gpt_response = result["gpt_response"]

    print(f"⏱️ Время: {result['processing_time']}")
    print(f"\n🧠 THINKING:\n{gpt_response.get('thinking', 'N/A')}")

    print(f"\n📋 RESULT:")
    result_data = gpt_response.get('result', {})
    print(f"   Summary: {result_data.get('summary', 'N/A')}")

    print(f"\n🎯 ACTION: {gpt_response.get('action', {}).get('type', 'N/A')}")

    return True


async def test_sort():
    """Тест сортировки"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Сортировка")
    print("="*60)

    df = pd.DataFrame(TEST_DATA["rows"], columns=TEST_DATA["columns"])

    analyst = CleanAnalyst(api_key=settings.OPENAI_API_KEY)

    result = await analyst.analyze(
        query="Отсортируй таблицу по декабрю по убыванию",
        df=df,
        column_names=TEST_DATA["columns"]
    )

    if not result["success"]:
        print(f"❌ ОШИБКА: {result.get('error')}")
        return False

    gpt_response = result["gpt_response"]
    action = gpt_response.get('action', {})

    print(f"⏱️ Время: {result['processing_time']}")
    print(f"🎯 ACTION: {action.get('type', 'N/A')}")

    if action.get('type') == 'sort':
        print(f"   Column: {action.get('column', 'N/A')}")
        print(f"   Column index: {action.get('column_index', 'N/A')}")
        print(f"   Order: {action.get('order', 'N/A')}")

        # Проверяем frontend format
        frontend = analyst.transform_to_frontend_format(gpt_response, result['processing_time'])
        print(f"\nFRONTEND:")
        print(f"   action_type: {frontend.get('action_type')}")
        print(f"   sort_column: {frontend.get('sort_column')}")
        print(f"   sort_column_index: {frontend.get('sort_column_index')}")
        print(f"   sort_order: {frontend.get('sort_order')}")

    return True


async def test_formula():
    """Тест генерации формулы"""
    print("\n" + "="*60)
    print("ТЕСТ 4: Формула")
    print("="*60)

    df = pd.DataFrame(TEST_DATA["rows"], columns=TEST_DATA["columns"])

    analyst = CleanAnalyst(api_key=settings.OPENAI_API_KEY)

    result = await analyst.analyze(
        query="Напиши формулу для подсчёта суммы всех заказов за декабрь",
        df=df,
        column_names=TEST_DATA["columns"]
    )

    if not result["success"]:
        print(f"❌ ОШИБКА: {result.get('error')}")
        return False

    gpt_response = result["gpt_response"]
    action = gpt_response.get('action', {})

    print(f"⏱️ Время: {result['processing_time']}")
    print(f"🎯 ACTION: {action.get('type', 'N/A')}")

    if action.get('type') == 'formula':
        print(f"   Formula: {action.get('formula', 'N/A')}")
        print(f"   Target cell: {action.get('target_cell', 'N/A')}")
        print(f"   Explanation: {action.get('explanation', 'N/A')}")

        # Проверяем frontend format
        frontend = analyst.transform_to_frontend_format(gpt_response, result['processing_time'])
        print(f"\nFRONTEND:")
        print(f"   formula: {frontend.get('formula')}")
        print(f"   target_cell: {frontend.get('target_cell')}")

    return True


async def main():
    print("🧪 ТЕСТИРОВАНИЕ CleanAnalyst v1.0")
    print("="*60)

    # Проверяем API ключ
    if not settings.OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY не установлен!")
        return

    print(f"✅ API Key: {settings.OPENAI_API_KEY[:10]}...")

    tests = [
        ("Прогноз", test_forecast),
        ("Анализ", test_analysis),
        ("Сортировка", test_sort),
        ("Формула", test_formula),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ EXCEPTION в тесте {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "="*60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print("="*60)
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"   {status} {name}")

    passed = sum(1 for _, s in results if s)
    print(f"\nПрошло: {passed}/{len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
