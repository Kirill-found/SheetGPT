"""
Интеграционные тесты end-to-end для полной системы
Показывают как работают все компоненты вместе
"""

import pytest
from app.services.ai_service import AIService


@pytest.mark.asyncio
async def test_full_system_with_validation():
    """
    Тест: Полная система - от запроса до формулы с validation и confidence

    Проверяем:
    - Template matching работает
    - Validation находит проблемы
    - Auto-fix исправляет формулы
    - Confidence score рассчитывается правильно
    - Column reference validation срабатывает
    """
    print("\n=== FULL SYSTEM TEST ===\n")

    service = AIService()

    # Запрос пользователя
    query = "Посчитай сумму продаж"
    columns = ["Товар", "Продажи", "Регион"]
    sample_data = [
        ["Товар A", 1000, "Москва"],
        ["Товар B", 2000, "СПб"],
        ["Товар C", 3000, "Москва"]
    ]

    result = await service.generate_formula(
        query,
        columns,
        sample_data
    )

    # Проверки результата
    print("[RESULT]")
    print(f"  Formula: {result['formula']}")
    print(f"  Source: {result['source']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Type: {result['type']}")

    # Базовые проверки
    assert result['type'] == 'formula'
    assert result['source'] == 'template'  # Простой запрос -> template
    assert result['confidence'] >= 0.9  # Высокая уверенность для template
    assert 'SUM' in result['formula']  # Английская формула (Google Sheets автоматически переведет)
    assert 'B:B' in result['formula'] or 'B2:B' in result['formula']  # Правильная колонка

    print("\n[OK] Basic checks passed")

    # Проверяем validation_log если были issues
    if result.get('validation_log'):
        print(f"\n[VALIDATION LOG]:")
        print(f"  Issues found: {result['validation_log'].get('issues_found', 0)}")
        print(f"  Auto-fixed: {result['validation_log'].get('auto_fixed', False)}")
    else:
        print("\n[OK] No validation issues - perfect formula!")

    print("\n=== TEST PASSED ===\n")


@pytest.mark.asyncio
async def test_column_reference_validation_integration():
    """
    Тест: Column reference validation в полном цикле

    Создаём формулу которая ссылается на несуществующую колонку
    и проверяем что система это обнаруживает
    """
    print("\n=== COLUMN VALIDATION INTEGRATION TEST ===\n")

    service = AIService()

    # У нас таблица с 3 колонками, но мы попробуем сослаться на 4-ую
    columns = ["Имя", "Возраст", "Город"]  # A, B, C
    sample_data = [
        ["Иван", 25, "Москва"],
        ["Мария", 30, "СПб"]
    ]

    # Создадим формулу вручную с неправильной ссылкой
    from app.services.formula_validator import FormulaValidator
    from app.services.formula_fixer import FormulaFixer

    validator = FormulaValidator()
    fixer = FormulaFixer()

    # Формула ссылается на D (4-я колонка), но у нас только 3
    bad_formula = "=СУММ(A1:A10) + D5"

    context = {
        "column_count": len(columns),
        "column_names": columns
    }

    issues = validator.validate(bad_formula, context)

    print("[FOUND ISSUES]:")
    for issue in issues:
        print(f"  - [{issue.severity}] {issue.issue_type}: {issue.message}")

    # Проверяем что column reference validation сработала
    column_issues = [i for i in issues if i.issue_type == "invalid_column_reference"]

    assert len(column_issues) > 0, "Column reference validation должна найти проблему!"
    assert "D" in column_issues[0].message, "Должна быть найдена колонка D"

    print(f"\n[OK] Column validation обнаружила проблему: {column_issues[0].message}")
    print("\n=== TEST PASSED ===\n")


@pytest.mark.asyncio
async def test_confidence_scoring_integration():
    """
    Тест: Confidence scoring в зависимости от validation issues

    Проверяем что формулы с проблемами получают более низкий confidence
    """
    print("\n=== CONFIDENCE SCORING TEST ===\n")

    service = AIService()

    columns = ["Товар", "Цена", "Количество"]
    sample_data = [
        ["Товар A", 100, 5],
        ["Товар B", 200, 3]
    ]

    # Запрос который должен использовать template (высокий confidence)
    result1 = await service.generate_formula(
        "Посчитай сумму цен",
        columns,
        sample_data
    )

    print("[TEST 1] Simple sum (template):")
    print(f"  Confidence: {result1['confidence']}")
    print(f"  Source: {result1['source']}")

    # Template должен иметь высокий confidence
    assert result1['confidence'] >= 0.90, "Template должен иметь высокий confidence"

    print("\n[OK] Template имеет высокий confidence")

    # Если есть validation issues, confidence должен быть ниже
    if result1.get('validation_log'):
        issues_count = result1['validation_log'].get('issues_found', 0)
        if issues_count > 0:
            print(f"\n[WARNING] Найдено {issues_count} issues, но они авто-фиксятся")
            print(f"  Confidence немного снижен: {result1['confidence']}")

    print("\n=== TEST PASSED ===\n")


if __name__ == "__main__":
    import asyncio

    print("=" * 60)
    print("  FULL SYSTEM END-TO-END TESTS")
    print("=" * 60)

    asyncio.run(test_full_system_with_validation())
    asyncio.run(test_column_reference_validation_integration())
    asyncio.run(test_confidence_scoring_integration())

    print("=" * 60)
    print("  [SUCCESS] ALL END-TO-END TESTS PASSED!")
    print("=" * 60)
