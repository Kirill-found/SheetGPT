# -*- coding: utf-8 -*-
"""Тест VLOOKUP -> INDEX/MATCH постпроцессинга"""
import re

def clean_formula_vlookup(formula):
    """Исправляет VLOOKUP в ARRAYFORMULA"""
    if 'ARRAYFORMULA' in formula.upper() and 'VLOOKUP' in formula.upper():
        vlookup_pattern = r'VLOOKUP\(([^;]+);([^;]+);(\d+);?([^)]*)\)'

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

        formula = re.sub(vlookup_pattern, replace_vlookup_with_index_match, formula, flags=re.IGNORECASE)

    return formula

# ТЕСТЫ
tests = [
    ("VLOOKUP с $", "=ARRAYFORMULA(IF(B2:B=\"\";\"\"VLOOKUP(B2:B;$H:$I;2;FALSE)))", ["INDEX", "$I:$I", "$H:$H"]),
    ("VLOOKUP без $", "=ARRAYFORMULA(IF(B2:B=\"\";\"\"VLOOKUP(B2:B;H:I;2;FALSE)))", ["INDEX", "I:I", "H:H"]),
    ("VLOOKUP с IF", "=ARRAYFORMULA(IF(B2:B=\"\";\"\"IF(C2:C<5;VLOOKUP(B2:B;H:I;2;FALSE);VLOOKUP(B2:B;H:I;2;FALSE)*1.05)))", ["INDEX", "MATCH"]),
    ("Без ARRAYFORMULA (не менять)", "=VLOOKUP(B2;$H:$I;2;FALSE)", ["VLOOKUP"]),
]

print("=" * 80)
print("VLOOKUP -> INDEX/MATCH POSTPROCESSING TEST")
print("=" * 80)

for i, (name, input_f, expected) in enumerate(tests, 1):
    print(f"\nTest {i}: {name}")
    print("-" * 80)
    result = clean_formula_vlookup(input_f)
    print(f"Input:  {input_f[:80]}...")
    print(f"Output: {result[:80]}...")

    success = all(exp in result for exp in expected)
    print(f"Status: {'OK' if success else 'FAILED'}")
    if not success:
        print(f"Expected: {expected}")

print("\n" + "=" * 80)
print("ПРИМЕР ЗАДАЧИ ПОЛЬЗОВАТЕЛЯ:")
print("=" * 80)
wrong = "=ARRAYFORMULA(IF(B2:B=\"\";\"\"IF(C2:C<5;VLOOKUP(B2:B;H:I;2;FALSE);VLOOKUP(B2:B;H:I;2;FALSE)*1.05)))"
correct = clean_formula_vlookup(wrong)
print("\nНеправильно (с VLOOKUP):")
print(wrong)
print("\nПравильно (с INDEX/MATCH):")
print(correct)
print("\nСодержит INDEX:", "INDEX" in correct)
print("Содержит MATCH:", "MATCH" in correct)
print("НЕ содержит VLOOKUP:", "VLOOKUP" not in correct)
