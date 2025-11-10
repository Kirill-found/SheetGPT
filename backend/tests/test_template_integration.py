"""
Интеграционные тесты для template engine + AI service
"""

import pytest
from app.services.ai_service import AIService

@pytest.mark.asyncio
async def test_formula_uses_template():
    """Тест: простая формула использует шаблон вместо AI"""
    service = AIService()

    query = "Посчитай сумму продаж"
    columns = ["Товар", "Продажи", "Регион"]

    result = await service.generate_formula(query, columns)

    # Проверяем что использован шаблон
    assert result["type"] == "formula"
    assert result["source"] == "template"
    # PHASE 2.4: Confidence теперь динамический (зависит от validation issues)
    assert result["confidence"] >= 0.9  # Высокая уверенность для templates

    # Проверяем что формула правильная
    assert "SUM" in result["formula"] or "СУММ" in result["formula"]
    assert "B:B" in result["formula"]  # Столбец "Продажи"

    print("[OK] Test formula_uses_template passed")
    print(f"   Formula: {result['formula']}")
    print(f"   Explanation: {result['explanation']}")


@pytest.mark.asyncio
async def test_full_name_template():
    """Тест: объединение ФИО использует шаблон"""
    service = AIService()

    query = "Создай полное ФИО в столбце D"
    columns = ["Фамилия", "Имя", "Отчество"]

    result = await service.generate_formula(query, columns)

    assert result["type"] == "formula"
    assert result["source"] == "template"

    # Проверяем что используется ЕСЛИ для обработки пустых ячеек
    formula = result["formula"]
    assert "ЕСЛИ" in formula or "IF" in formula
    assert "A" in formula  # Фамилия
    assert "B" in formula  # Имя
    assert "C" in formula  # Отчество

    print("[OK] Test full_name_template passed")
    print(f"   Formula: {result['formula']}")


@pytest.mark.asyncio
async def test_average_template():
    """Тест: среднее значение использует шаблон"""
    service = AIService()

    query = "Найди среднее по ценам"
    columns = ["Товар", "Цена", "Количество"]

    result = await service.generate_formula(query, columns)

    assert result["type"] == "formula"
    assert result["source"] == "template"

    formula = result["formula"]
    assert "AVERAGE" in formula or "СРЗНАЧ" in formula
    assert "B:B" in formula  # Столбец "Цена"

    print("[OK] Test average_template passed")
    print(f"   Formula: {result['formula']}")


@pytest.mark.asyncio
async def test_fallback_to_ai_for_complex_query():
    """Тест: сложный запрос без подходящего шаблона использует AI"""
    service = AIService()

    # Сложный запрос который не покрывается шаблонами
    query = "Создай динамическую таблицу с группировкой по категориям и сортировкой"
    columns = ["Категория", "Продукт", "Продажи", "Дата"]
    sample_data = [
        ["Фрукты", "Яблоко", 1000, "2024-01-01"],
        ["Овощи", "Морковь", 500, "2024-01-02"],
        ["Фрукты", "Банан", 800, "2024-01-03"]
    ]

    result = await service.generate_formula(query, columns, sample_data)

    assert result["type"] == "formula"
    # Так как шаблон не найден, source не будет "template"
    # AI должен был сгенерировать формулу
    assert "formula" in result

    print("[OK] Test fallback_to_ai passed")
    print(f"   Formula: {result['formula']}")
    print(f"   Source: {result.get('source', 'AI')}")


@pytest.mark.asyncio
async def test_template_localization():
    """Тест: формулы используют английские названия (Google Sheets автоматически переводит)"""
    service = AIService()

    query = "Если продажи больше 1000 пиши Выполнено"
    columns = ["Товар", "Продажи"]

    result = await service.generate_formula(query, columns)

    formula = result["formula"]

    # Используем английские формулы - Google Sheets сам переведет
    assert "IF" in formula
    assert "," in formula  # Английский разделитель аргументов

    print("[OK] Test template_localization passed")
    print(f"   Formula: {result['formula']}")


if __name__ == "__main__":
    import asyncio

    print("\n" + "="*60)
    print("TEMPLATE INTEGRATION TESTS")
    print("="*60 + "\n")

    async def run_all():
        await test_formula_uses_template()
        await test_full_name_template()
        await test_average_template()
        await test_fallback_to_ai_for_complex_query()
        await test_template_localization()

        print("\n" + "="*60)
        print("[SUCCESS] ALL INTEGRATION TESTS PASSED!")
        print("="*60)

    asyncio.run(run_all())
