"""
Тесты для validator и fixer
"""

from app.services.formula_validator import FormulaValidator
from app.services.formula_fixer import FormulaFixer


def test_arrayformula_open_range():
    """Тест: ARRAYFORMULA с open range"""
    validator = FormulaValidator()
    fixer = FormulaFixer()
    
    # Плохая формула (та что GPT генерит)
    bad_formula = "=ARRAYFORMULA(A2:A&\" \"&B2:B&\" \"&C2:C)"
    
    # Валидируем
    issues = validator.validate(bad_formula, {"row_count": 50})
    
    assert len(issues) > 0
    assert any(i.issue_type == "arrayformula_open_range" for i in issues)
    print(f"✅ Found {len(issues)} issues")
    
    # Чиним
    fixed = fixer.fix(bad_formula, issues, {"row_count": 50})
    
    print(f"Original: {bad_formula}")
    print(f"Fixed:    {fixed}")
    
    # Проверяем что исправлено
    assert "A2:A50" in fixed
    assert "B2:B50" in fixed
    assert "C2:C50" in fixed
    assert "A2:A&" not in fixed
    
    print("✅ Test arrayformula_open_range passed")


def test_vlookup_missing_false():
    """Тест: VLOOKUP без FALSE"""
    validator = FormulaValidator()
    fixer = FormulaFixer()
    
    bad_formula = "=VLOOKUP(A2,Sheet2!A:B,2)"
    
    issues = validator.validate(bad_formula)
    assert len(issues) > 0
    
    fixed = fixer.fix(bad_formula, issues)
    
    print(f"Original: {bad_formula}")
    print(f"Fixed:    {fixed}")
    
    assert "FALSE" in fixed
    print("✅ Test vlookup_missing_false passed")


def test_concatenation_empty_check():
    """Тест: конкатенация без проверки пустых"""
    validator = FormulaValidator()
    fixer = FormulaFixer()
    
    bad_formula = "=A2&\" \"&B2&\" \"&C2"
    
    issues = validator.validate(bad_formula)
    
    fixed = fixer.fix(bad_formula, issues)
    
    print(f"Original: {bad_formula}")
    print(f"Fixed:    {fixed}")
    
    assert "IF" in fixed or "LEN" in fixed
    print("✅ Test concatenation_empty_check passed")


def test_date_operation_datevalue():
    """Тест: операция с датой без DATEVALUE"""
    validator = FormulaValidator()
    fixer = FormulaFixer()
    
    bad_formula = "=TODAY()-A2"
    
    issues = validator.validate(bad_formula)
    
    fixed = fixer.fix(bad_formula, issues)
    
    print(f"Original: {bad_formula}")
    print(f"Fixed:    {fixed}")
    
    assert "DATEVALUE" in fixed
    print("✅ Test date_operation_datevalue passed")


def test_multiple_fixes():
    """Тест: несколько проблем одновременно"""
    validator = FormulaValidator()
    fixer = FormulaFixer()

    # Формула с несколькими проблемами
    bad_formula = "=VLOOKUP(A2,Sheet2!B:C,2)"  # нет FALSE и нет IFERROR

    issues = validator.validate(bad_formula)

    print(f"Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - {issue.issue_type}: {issue.message}")

    fixed = fixer.fix(bad_formula, issues)

    print(f"Original: {bad_formula}")
    print(f"Fixed:    {fixed}")

    assert "FALSE" in fixed
    assert "IFERROR" in fixed
    print("✅ Test multiple_fixes passed")


def test_quote_escaping():
    """Тест: Quote escaping \" → "" (PHASE 1.1)"""
    validator = FormulaValidator()
    fixer = FormulaFixer()

    # Плохая формула с \" (не работает в Google Sheets)
    bad_formula = '=СРЗНАЧЕСЛИ(B:B;"ООО \\"Луна\\"";E:E)'

    issues = validator.validate(bad_formula)

    print(f"Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - {issue.issue_type}: {issue.message}")

    # Проверяем что нашли проблему
    assert any(i.issue_type == "wrong_quote_escaping" for i in issues)

    # Чиним
    fixed = fixer.fix(bad_formula, issues)

    print(f"Original: {bad_formula}")
    print(f"Fixed:    {fixed}")

    # Проверяем что заменили на ""
    assert '""' in fixed
    assert '\\"' not in fixed
    print("✅ Test quote_escaping passed")


def test_localization():
    """Тест: Локализация английских функций → русские"""
    validator = FormulaValidator()
    fixer = FormulaFixer()

    # Формула с английскими функциями
    bad_formula = "=IF(TODAY()-A2>30,\"Просрочено\",\"OK\")"

    issues = validator.validate(bad_formula)

    print(f"Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - {issue.issue_type}: {issue.message}")

    # Проверяем что нашли проблему с локализацией
    assert any(i.issue_type == "not_localized" for i in issues)

    # Чиним
    fixed = fixer.fix(bad_formula, issues)

    print(f"Original: {bad_formula}")
    print(f"Fixed:    {fixed}")

    # Проверяем что английские функции ОСТАЛИСЬ (локализация отключена)
    assert "IF" in fixed
    assert "TODAY" in fixed
    # Но DATEVALUE должен быть добавлен для date_operation issue
    assert "DATEVALUE" in fixed
    print("✅ Test localization passed (English formulas preserved)")


def test_unbalanced_parentheses():
    """Тест: Несбалансированные скобки (PHASE 1.2)"""
    validator = FormulaValidator()

    # Формула с лишней открывающей скобкой
    bad_formula = "=SUM(A1:A10"

    issues = validator.validate(bad_formula)

    print(f"Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - {issue.issue_type}: {issue.message}")

    # Проверяем что нашли проблему
    assert any(i.issue_type == "unbalanced_parentheses" for i in issues)
    print("✅ Test unbalanced_parentheses passed")


def test_missing_equals():
    """Тест: Отсутствует = в начале (PHASE 1.2)"""
    validator = FormulaValidator()
    fixer = FormulaFixer()

    # Формула без =
    bad_formula = "SUM(A1:A10)"

    issues = validator.validate(bad_formula)

    print(f"Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - {issue.issue_type}: {issue.message}")

    # Проверяем что нашли проблему
    assert any(i.issue_type == "missing_equals" for i in issues)

    # Чиним
    fixed = fixer.fix(bad_formula, issues)

    print(f"Original: {bad_formula}")
    print(f"Fixed:    {fixed}")

    # Проверяем что добавили =
    assert fixed.startswith('=')
    print("✅ Test missing_equals passed")


def test_invalid_cell_ranges():
    """Тест: Некорректные диапазоны ячеек (PHASE 1.2)"""
    validator = FormulaValidator()

    # Формула с некорректным диапазоном (используем русскую функцию)
    bad_formula = "=СУММ(:A10)"  # Нет начальной ячейки

    issues = validator.validate(bad_formula)

    print(f"Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - {issue.issue_type}: {issue.message}")

    # Проверяем что нашли проблему
    assert any(i.issue_type == "invalid_cell_range" for i in issues)
    print("✅ Test invalid_cell_ranges passed")


def test_invalid_column_references():
    """Тест: Ссылки на несуществующие колонки (PHASE 2.2)"""
    validator = FormulaValidator()

    # Формула ссылается на колонку D, но в таблице только 3 колонки (A, B, C)
    bad_formula = "=СУММ(A1:A10) + D5"

    # Контекст: таблица с 3 колонками
    context = {
        "column_count": 3,
        "column_names": ["Имя", "Возраст", "Город"]
    }

    issues = validator.validate(bad_formula, context)

    print(f"Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - {issue.issue_type}: {issue.message}")

    # Проверяем что нашли проблему с колонкой D
    assert any(i.issue_type == "invalid_column_reference" for i in issues)
    assert any("D" in i.message for i in issues if i.issue_type == "invalid_column_reference")
    print("✅ Test invalid_column_references passed")


if __name__ == "__main__":
    test_arrayformula_open_range()
    print()
    test_vlookup_missing_false()
    print()
    test_concatenation_empty_check()
    print()
    test_date_operation_datevalue()
    print()
    test_multiple_fixes()
    print()
    test_quote_escaping()
    print()
    test_localization()
    print()
    test_unbalanced_parentheses()
    print()
    test_missing_equals()
    print()
    test_invalid_cell_ranges()
    print()
    test_invalid_column_references()
    print("\n✅ All validator tests passed!")