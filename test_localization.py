#!/usr/bin/env python3
"""
Тестирование функции локализации формул
"""

def _clean_formula(formula: str) -> str:
    """Удаляет лишние пробелы из формулы и локализует для русской версии Google Sheets"""
    # Удаляем пробелы вокруг операторов
    formula = formula.replace(" >", ">").replace("> ", ">")
    formula = formula.replace(" <", "<").replace("< ", "<")
    formula = formula.replace(" =", "=").replace("= ", "=")
    formula = formula.replace(" ,", ",").replace(", ", ",")
    formula = formula.replace(" )", ")").replace("( ", "(")

    # Удаляем множественные пробелы
    while "  " in formula:
        formula = formula.replace("  ", "")

    # ЛОКАЛИЗАЦИЯ: Заменяем запятые на точки с запятой для русской версии Google Sheets
    # Обрабатываем умно: не трогаем запятые внутри строковых литералов
    result = []
    in_string = False

    for i, char in enumerate(formula):
        # Отслеживаем вход/выход из строковых литералов
        if char == '"':
            in_string = not in_string
            result.append(char)
        # Заменяем запятые на точки с запятой только вне строк
        elif char == ',' and not in_string:
            result.append(';')
        else:
            result.append(char)

    return ''.join(result)


# Тестовые случаи
test_cases = [
    {
        "input": '=ARRAYFORMULA(IF(A2:A="","",A2:A&" "&B2:B&" "&C2:C))',
        "expected": '=ARRAYFORMULA(IF(A2:A="";"";A2:A&" "&B2:B&" "&C2:C))',
        "description": "Конкатенация ФИО"
    },
    {
        "input": '=SORT(FILTER(A2:G,C2:C>500000),3,FALSE)',
        "expected": '=SORT(FILTER(A2:G;C2:C>500000);3;FALSE)',
        "description": "SORT и FILTER"
    },
    {
        "input": '=SUMIF(A2:A10,"Яблоко",B2:B10)',
        "expected": '=SUMIF(A2:A10;"Яблоко";B2:B10)',
        "description": "SUMIF с текстом"
    },
    {
        "input": '=IF(A2>100,"Высокий","Низкий")',
        "expected": '=IF(A2>100;"Высокий";"Низкий")',
        "description": "IF с русским текстом"
    }
]

print("=== ТЕСТИРОВАНИЕ ЛОКАЛИЗАЦИИ ФОРМУЛ ===\n")

all_passed = True
for i, test in enumerate(test_cases, 1):
    result = _clean_formula(test["input"])
    passed = result == test["expected"]
    all_passed = all_passed and passed

    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"Тест {i}: {test['description']}")
    print(f"  Входная:   {test['input']}")
    print(f"  Ожидаемая: {test['expected']}")
    print(f"  Результат: {result}")
    print(f"  Статус: {status}\n")

print("=" * 50)
if all_passed:
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
else:
    print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
