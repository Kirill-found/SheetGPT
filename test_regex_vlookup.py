# -*- coding: utf-8 -*-
"""Тест regex для VLOOKUP постпроцессинга"""
import re

formula = '=ARRAYFORMULA(IF(C2:C=""; ""; IF(C2:C<5; VLOOKUP(B2:B; G:H; 2; FALSE); VLOOKUP(B2:B; G:H; 2; FALSE)*1.05)))'

print("=== ТЕСТ REGEX ДЛЯ VLOOKUP ===")
print(f"Формула: {formula}")
print()

# Проверка условий
has_arrayformula = 'ARRAYFORMULA' in formula.upper()
has_vlookup = 'VLOOKUP' in formula.upper()

print(f"Содержит ARRAYFORMULA: {has_arrayformula}")
print(f"Содержит VLOOKUP: {has_vlookup}")
print()

if has_arrayformula and has_vlookup:
    vlookup_pattern = r'VLOOKUP\(([^;]+);\s*([^;]+);\s*(\d+);?\s*([^)]*)\)'

    print(f"Паттерн: {vlookup_pattern} (с \\s* для учета пробелов)")
    print()

    matches = list(re.finditer(vlookup_pattern, formula, flags=re.IGNORECASE))

    print(f"Найдено совпадений: {len(matches)}")
    print()

    for i, match in enumerate(matches, 1):
        print(f"Совпадение {i}:")
        print(f"  Полное: {match.group(0)}")
        print(f"  lookup_value: {match.group(1).strip()}")
        print(f"  table_range: {match.group(2).strip()}")
        print(f"  col_index: {match.group(3).strip()}")
        print()

    # Применяем замену
    def replace_vlookup_with_index_match(match):
        lookup_value = match.group(1).strip()
        table_range = match.group(2).strip()
        col_index = int(match.group(3).strip())

        if ':' in table_range:
            parts = table_range.split(':')
            first_col = parts[0].strip()
            last_col = parts[1].strip()

            has_dollar = '$' in first_col or '$' in last_col
            dollar_prefix = '$' if has_dollar else ''

            first_col_letter = ''.join([c for c in first_col if c.isalpha()])
            last_col_letter = ''.join([c for c in last_col if c.isalpha()])

            if col_index == 1:
                result_col_letter = first_col_letter
            elif col_index == 2:
                result_col_letter = last_col_letter
            else:
                first_col_num = ord(first_col_letter.upper()) - ord('A')
                result_col_num = first_col_num + col_index - 1
                result_col_letter = chr(ord('A') + result_col_num)

            search_col = f"{dollar_prefix}{first_col_letter}:{dollar_prefix}{first_col_letter}"
            result_col = f"{dollar_prefix}{result_col_letter}:{dollar_prefix}{result_col_letter}"

            return f'INDEX({result_col}; MATCH({lookup_value}; {search_col}; 0))'
        else:
            return match.group(0)

    result = re.sub(vlookup_pattern, replace_vlookup_with_index_match, formula, flags=re.IGNORECASE)

    print("РЕЗУЛЬТАТ ПОСЛЕ ЗАМЕНЫ:")
    print(result)
    print()
    print(f"Содержит INDEX: {'INDEX' in result}")
    print(f"Содержит MATCH: {'MATCH' in result}")
    print(f"Больше нет VLOOKUP: {'VLOOKUP' not in result}")
else:
    print("Условия не выполнены - постпроцессинг не применяется")
