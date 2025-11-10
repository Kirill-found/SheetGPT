"""
Интеграционный тест для AIService с validator + fixer
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock


# Мокаем OpenAI для тестов
class MockAIService:
    """Упрощенная версия AIService для тестирования validator+fixer"""

    def __init__(self):
        from app.services.template_matcher import TemplateMatcher
        from app.services.formula_validator import FormulaValidator
        from app.services.formula_fixer import FormulaFixer

        self.template_matcher = TemplateMatcher()
        self.validator = FormulaValidator()
        self.fixer = FormulaFixer()

    def validate_and_fix_formula(self, formula: str, context: dict = None) -> dict:
        """
        Валидирует и чинит формулу

        Returns:
            {
                "original": str,
                "fixed": str,
                "issues": List[ValidationIssue],
                "was_fixed": bool
            }
        """
        context = context or {}

        # Валидация
        issues = self.validator.validate(formula, context)

        # Если есть проблемы - чиним
        fixed_formula = formula
        if issues:
            fixable_issues = [i for i in issues if i.auto_fixable]
            if fixable_issues:
                fixed_formula = self.fixer.fix(formula, fixable_issues, context)

        return {
            "original": formula,
            "fixed": fixed_formula,
            "issues": issues,
            "was_fixed": fixed_formula != formula
        }


def test_validate_arrayformula_open_range():
    """Тест: ARRAYFORMULA с open range автоматически исправляется"""
    service = MockAIService()

    bad_formula = "=ARRAYFORMULA(A2:A&\" \"&B2:B)"

    result = service.validate_and_fix_formula(
        bad_formula,
        {"row_count": 100}
    )

    print(f"Original: {result['original']}")
    print(f"Fixed:    {result['fixed']}")
    print(f"Issues found: {len(result['issues'])}")

    assert result['was_fixed'] == True
    assert "A2:A100" in result['fixed']
    assert "B2:B100" in result['fixed']
    assert result['issues'][0].severity == "critical"

    print("✓ Test validate_arrayformula passed")


def test_validate_vlookup_without_false():
    """Тест: VLOOKUP без FALSE автоматически добавляется"""
    service = MockAIService()

    bad_formula = "=VLOOKUP(A2,Sheet2!B:C,2)"

    result = service.validate_and_fix_formula(bad_formula)

    print(f"Original: {result['original']}")
    print(f"Fixed:    {result['fixed']}")

    assert result['was_fixed'] == True
    assert "FALSE" in result['fixed']
    assert "IFERROR" in result['fixed']

    print("✓ Test validate_vlookup passed")


def test_template_with_validation():
    """Тест: Template формула тоже проходит валидацию"""
    service = MockAIService()

    # Найдем template для суммы
    query = "Посчитай сумму продаж"
    columns = ["Товар", "Продажи", "Регион"]

    template_result = service.template_matcher.find_template(query, columns)

    assert template_result is not None

    template, params = template_result

    # Генерируем формулу из template
    formula = template.formula_pattern.format(**params)

    print(f"Template formula: {formula}")

    # Валидируем
    result = service.validate_and_fix_formula(formula, {"row_count": 100})

    print(f"Validation issues: {len(result['issues'])}")

    # Template формулы должны быть чистыми (без критичных ошибок)
    critical_issues = [i for i in result['issues'] if i.severity == "critical"]
    assert len(critical_issues) == 0

    print("✓ Test template_with_validation passed")


def test_concatenation_fix():
    """Тест: Конкатенация получает проверки пустых и TRIM"""
    service = MockAIService()

    bad_formula = "=A2&\" \"&B2&\" \"&C2"

    result = service.validate_and_fix_formula(bad_formula)

    print(f"Original: {result['original']}")
    print(f"Fixed:    {result['fixed']}")

    assert result['was_fixed'] == True
    assert "TRIM" in result['fixed']
    assert "IF" in result['fixed'] or "LEN" in result['fixed']

    print("✓ Test concatenation_fix passed")


def test_good_formula_no_changes():
    """Тест: Хорошая формула остается без изменений"""
    service = MockAIService()

    good_formula = "=IFERROR(VLOOKUP(A2,Sheet2!B:C,2,FALSE),\"Не найдено\")"

    result = service.validate_and_fix_formula(good_formula)

    print(f"Formula: {result['original']}")
    print(f"Issues: {len(result['issues'])}")

    # Не должно быть критичных ошибок
    critical = [i for i in result['issues'] if i.severity == "critical"]
    assert len(critical) == 0

    print("✓ Test good_formula passed")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("AI SERVICE INTEGRATION TESTS (Validator + Fixer)")
    print("="*70 + "\n")

    test_validate_arrayformula_open_range()
    print()
    test_validate_vlookup_without_false()
    print()
    test_template_with_validation()
    print()
    test_concatenation_fix()
    print()
    test_good_formula_no_changes()

    print("\n" + "="*70)
    print("✓ ALL AI SERVICE INTEGRATION TESTS PASSED!")
    print("="*70)
