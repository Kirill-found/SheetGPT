#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Добавляет передачу полей подсветки в main.py
"""

import re

# Читаем файл
with open('C:/SheetGPT/backend/app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Паттерн для вставки после structured_data
pattern = r'(        # Add structured_data for table/chart creation.*?\n.*?response_dict\["structured_data"\] = result\["structured_data"\])'

replacement = r'''\1

        # Add highlighting data (v6.5.6: CRITICAL for row highlighting)
        if "highlight_rows" in result:
            response_dict["highlight_rows"] = result["highlight_rows"]
        if "highlight_color" in result:
            response_dict["highlight_color"] = result["highlight_color"]
        if "highlight_message" in result:
            response_dict["highlight_message"] = result["highlight_message"]
        if "action_type" in result:
            response_dict["action_type"] = result["action_type"]'''

# Заменяем
if 'highlight_rows' not in content:
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    print("Added highlighting fields to main.py")
else:
    print("Highlighting fields already present")

# Записываем обратно
with open('C:/SheetGPT/backend/app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")