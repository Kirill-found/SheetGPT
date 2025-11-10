# -*- coding: utf-8 -*-
"""Тест INDEX/MATCH постпроцессинга с анализом типов данных"""
import sys
sys.path.append('C:\\SheetGPT\\backend')

from app.services.ai_service import AIService

# Тестовые данные - точно как у пользователя
column_names = ["ФИО", "Отдел", "Стаж работы (лет)", "Оклад", "", "", "Отделы", "Базовый оклад"]
sample_data = [
    ["Иванов И.И.", "Аналитика", 3, "", "", "", "Аналитика", 55000],
    ["Петров П.П.", "HR", 7, "", "", "", "HR", 45000],
    ["Сидоров С.С.", "IT", 2, "", "", "", "IT", 70000]
]

# Создаем экземпляр сервиса
service = AIService()

print("=" * 80)
print("ТЕСТ INDEX/MATCH ПОСТПРОЦЕССИНГА С АНАЛИЗОМ ТИПОВ ДАННЫХ")
print("=" * 80)
print()

# Анализ типов данных
print("ШАГ 1: Анализ типов данных в столбцах")
print("-" * 80)
column_types = service._analyze_column_types(column_names, sample_data)
for i, (col_name, col_type) in enumerate(column_types.items()):
    col_letter = chr(ord('A') + i)
    print(f"  {col_letter}: {col_name:30} → {col_type}")
print()

# Тестовые формулы
test_cases = [
    {
        "name": "ОШИБКА #1: Поиск текста в числовом столбце (как у пользователя)",
        "formula": "=ARRAYFORMULA(IF(C2:C<5;INDEX($I:$I;MATCH(B2:B;$H:$H;0));INDEX($I:$I;MATCH(B2:B;$H:$H;0))*1.05))",
        "expected": ["INDEX($H:$H", "MATCH(B2:B;$G:$G", "не содержит $I:$I"]
    },
    {
        "name": "ОШИБКА #2: Без абсолютных ссылок",
        "formula": "=ARRAYFORMULA(IF(C2:C<5;INDEX(I:I;MATCH(B2:B;H:H;0));INDEX(I:I;MATCH(B2:B;H:H;0))*1.05))",
        "expected": ["INDEX(H:H", "MATCH(B2:B;G:G"]
    },
    {
        "name": "УЖЕ ПРАВИЛЬНО: Не должен менять",
        "formula": "=ARRAYFORMULA(IF(C2:C<5;INDEX($H:$H;MATCH(B2:B;$G:$G;0));INDEX($H:$H;MATCH(B2:B;$G:$G;0))*1.05))",
        "expected": ["INDEX($H:$H", "MATCH(B2:B;$G:$G"]
    }
]

for i, test in enumerate(test_cases, 1):
    print(f"ТЕСТ {i}: {test['name']}")
    print("-" * 80)
    print(f"До:  {test['formula'][:90]}...")

    result = service._clean_formula(test['formula'], column_names, sample_data)

    print(f"После: {result[:90]}...")
    print()

    # Проверка ожиданий
    success = all(exp in result if not exp.startswith("не содержит") else exp.split("не содержит ")[1] not in result for exp in test['expected'])

    print(f"Ожидания:")
    for exp in test['expected']:
        if exp.startswith("не содержит"):
            text = exp.split("не содержит ")[1]
            check = text not in result
            print(f"  {'✓' if check else '✗'} Не содержит {text}: {check}")
        else:
            check = exp in result
            print(f"  {'✓' if check else '✗'} Содержит {exp}: {check}")

    print(f"\nСТАТУС: {'✓ OK' if success else '✗ FAILED'}")
    print()

print("=" * 80)
print("ДЕТАЛЬНЫЙ АНАЛИЗ ФОРМУЛЫ ПОЛЬЗОВАТЕЛЯ")
print("=" * 80)

wrong = "=ARRAYFORMULA(IF(C2:C<5;INDEX($I:$I;MATCH(B2:B;$H:$H;0));INDEX($I:$I;MATCH(B2:B;$H:$H;0))*1.05))"
correct = service._clean_formula(wrong, column_names, sample_data)

print("\nПРОБЛЕМА:")
print(f"  B2:B (столбец B 'Отдел') содержит ТЕКСТ: 'Аналитика', 'HR', 'IT'")
print(f"  $H:$H (столбец H 'Базовый оклад') содержит ЧИСЛА: 55000, 45000, 70000")
print(f"  → MATCH ищет 'Аналитика' в [55000, 45000, 70000] → #ERROR!")
print()

print("РЕШЕНИЕ:")
print(f"  $G:$G (столбец G 'Отделы') содержит ТЕКСТ: 'Аналитика', 'HR', 'IT'")
print(f"  → MATCH должен искать в $G:$G (текст в тексте)")
print(f"  → INDEX должен возвращать из $H:$H (числа)")
print()

print("ФОРМУЛА ДО ПОСТПРОЦЕССИНГА:")
print(wrong)
print()

print("ФОРМУЛА ПОСЛЕ ПОСТПРОЦЕССИНГА:")
print(correct)
print()

has_correct_search = "$G:$G" in correct
has_correct_result = "$H:$H" in correct
no_wrong_col = "$I:$I" not in correct

print("ПРОВЕРКА:")
print(f"  ✓ Ищет в $G:$G (текст): {has_correct_search}")
print(f"  ✓ Возвращает из $H:$H (числа): {has_correct_result}")
print(f"  ✓ Не использует $I:$I: {no_wrong_col}")
print()

if has_correct_search and has_correct_result and no_wrong_col:
    print("🎉 УСПЕХ! Постпроцессинг работает правильно!")
else:
    print("❌ ОШИБКА! Постпроцессинг не исправил формулу!")
