"""
Тест для проверки постпроцессинга VLOOKUP → INDEX/MATCH
"""
import re

def clean_formula_vlookup(formula: str) -> str:
    """Исправляет VLOOKUP в ARRAYFORMULA"""

    # ИСПРАВЛЕНИЕ VLOOKUP В ARRAYFORMULA: VLOOKUP → INDEX/MATCH
    if 'ARRAYFORMULA' in formula.upper() and 'VLOOKUP' in formula.upper():
        # Паттерн для поиска VLOOKUP(lookup_value; table_range; col_index; [FALSE])
        vlookup_pattern = r'VLOOKUP\(([^;]+);([^;]+);(\d+);?([^)]*)\)'

        def replace_vlookup_with_index_match(match):
            lookup_value = match.group(1).strip()
            table_range = match.group(2).strip()
            col_index = int(match.group(3).strip())

            # Разбираем table_range на колонки
            if ':' in table_range:
                parts = table_range.split(':')
                first_col = parts[0].strip()
                last_col = parts[1].strip()

                # Сохраняем $ если они были
                has_dollar = '$' in first_col or '$' in last_col
                dollar_prefix = '$' if has_dollar else ''

                # Извлекаем буквы колонок (убираем цифры и $)
                first_col_letter = ''.join([c for c in first_col if c.isalpha()])
                last_col_letter = ''.join([c for c in last_col if c.isalpha()])

                # Определяем result_col по col_index
                if col_index == 1:
                    result_col_letter = first_col_letter
                elif col_index == 2:
                    result_col_letter = last_col_letter
                else:
                    # Для col_index > 2 вычисляем нужную колонку
                    first_col_num = ord(first_col_letter.upper()) - ord('A')
                    result_col_num = first_col_num + col_index - 1
                    result_col_letter = chr(ord('A') + result_col_num)

                # Формируем диапазоны с сохранением абсолютных ссылок
                search_col = f"{dollar_prefix}{first_col_letter}:{dollar_prefix}{first_col_letter}"
                result_col = f"{dollar_prefix}{result_col_letter}:{dollar_prefix}{result_col_letter}"

                return f'INDEX({result_col}; MATCH({lookup_value}; {search_col}; 0))'
            else:
                # Если table_range не содержит :, оставляем как есть
                return match.group(0)

        formula = re.sub(vlookup_pattern, replace_vlookup_with_index_match, formula, flags=re.IGNORECASE)

    return formula


# ТЕСТЫ
test_cases = [
    {
        "name": "VLOOKUP с абсолютными ссылками",
        "input": "=ARRAYFORMULA(IF(B2:B=\"\";\"\"VLOOKUP(B2:B;$H:$I;2;FALSE)))",
        "expected_contains": ["INDEX", "MATCH", "$H:$H", "$I:$I"]
    },
    {
        "name": "VLOOKUP без абсолютных ссылок",
        "input": "=ARRAYFORMULA(IF(B2:B=\"\";\"\"VLOOKUP(B2:B;H:I;2;FALSE)))",
        "expected_contains": ["INDEX", "MATCH", "H:H", "I:I"]
    },
    {
        "name": "VLOOKUP с условием (задача пользователя)",
        "input": "=ARRAYFORMULA(IF(B2:B=\"\";\"\"IF(C2:C<5;VLOOKUP(B2:B;H:I;2;FALSE);VLOOKUP(B2:B;H:I;2;FALSE)*1.05)))",
        "expected_contains": ["INDEX", "MATCH"]
    },
    {
        "name": "Обычная формула без ARRAYFORMULA (не должна меняться)",
        "input": "=VLOOKUP(B2;$H:$I;2;FALSE)",
        "expected_contains": ["VLOOKUP"]
    }
]

print("=" * 80)
print("ТЕСТИРОВАНИЕ VLOOKUP -> INDEX/MATCH ПОСТПРОЦЕССИНГА")
print("=" * 80)

for i, test in enumerate(test_cases, 1):
    print(f"\n{i}. {test['name']}")
    print("-" * 80)
    print(f"Вход:  {test['input']}")

    result = clean_formula_vlookup(test['input'])
    print(f"Выход: {result}")

    # Проверяем что результат содержит ожидаемые подстроки
    success = all(expected in result for expected in test['expected_contains'])

    if success:
        print("✅ ТЕСТ ПРОШЕЛ")
    else:
        print("❌ ТЕСТ НЕ ПРОШЕЛ")
        print(f"Ожидалось наличие: {test['expected_contains']}")

print("\n" + "=" * 80)
print("КОНКРЕТНЫЙ ПРИМЕР ДЛЯ ЗАДАЧИ ПОЛЬЗОВАТЕЛЯ:")
print("=" * 80)
print("\nЗадача: вписать оклад, с условием:")
print("- если стаж работы < 5 лет → используй оклады из второй таблицы")
print("- если стаж работы >= 5 лет → к базовому окладу прибавь 5%")
print("\nНЕПРАВИЛЬНАЯ ФОРМУЛА (с VLOOKUP):")
wrong = "=ARRAYFORMULA(IF(B2:B=\"\";\"\"IF(C2:C<5;VLOOKUP(B2:B;H:I;2;FALSE);VLOOKUP(B2:B;H:I;2;FALSE)*1.05)))"
print(wrong)
print("\nПРАВИЛЬНАЯ ФОРМУЛА (с INDEX/MATCH):")
correct = clean_formula_vlookup(wrong)
print(correct)
