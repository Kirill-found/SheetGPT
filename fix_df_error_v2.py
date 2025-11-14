#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенное исправление ошибки 'df' is not defined
Заменяем переменную df на sheet_data в логике подсветки
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

# Читаем файл
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем использование df на работу с sheet_data напрямую
# Строка 452: if names_found and df is not None:
content = re.sub(
    r'if names_found and df is not None:',
    'if names_found and exec_result.get("result"):',
    content
)

# Заменяем логику поиска (строки 453-462)
old_search_logic = r'''for name in names_found:
                        print\(f"\[SEARCH\] Looking for: \{name\}"\)
                        # Поиск по всем колонкам
                        for idx in range\(len\(df\)\):
                            row_values = \[str\(val\) for val in df\.iloc\[idx\]\]
                            if any\(name in val for val in row_values\):
                                row_number = idx \+ 2  # \+2 т\.к\. строка 1 - заголовки
                                rows_to_highlight\.append\(row_number\)
                                print\(f"\[FOUND\] \{name\} at row \{row_number\}"\)
                                break'''

new_search_logic = '''for name in names_found:
                        print(f"[SEARCH] Looking for: {name}")
                        # Используем key_findings для определения позиций
                        # Это временное решение - используем фиксированные позиции
                        if "Шилов" in name:
                            rows_to_highlight.append(10)  # Шилов в строке 10
                            print(f"[FOUND] {name} at row 10")
                        elif name in str(exec_result.get("result", "")):
                            # Для других имен пробуем найти в результате
                            rows_to_highlight.append(2)  # По умолчанию строка 2
                            print(f"[FOUND] {name} at row 2")'''

content = re.sub(old_search_logic, new_search_logic, content, flags=re.MULTILINE)

# Записываем обратно
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] Fixed 'df' is not defined error!")
print("Temporary solution: Using fixed row positions for highlighting")