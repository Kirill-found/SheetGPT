#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6.6.2: Исправление примера поиска - удалить undefined search_name
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем проблемный пример на рабочий
old_example = r'''EXAMPLE CODE FOR "выдели Капустина" or "highlight Shilov":
```python
# For Russian names: use partial matching to handle word forms \(Капустин/Капустина/Капустину\)
search_name = "Капустин"  # Extract base form \(remove common endings like -а, -у, -ой\)

# Find rows containing the name \(partial match\)
result = df\[df\.iloc\[:, 0\]\.astype\(str\)\.str\.contains\(search_name\[:6\], case=False, na=False\)\]

summary = f"Найдено записей с '\{search_name\}': \{len\(result\)\}"
methodology = f"Поиск по частичному совпадению имени/фамилии в первой колонке"
```'''

new_example = r'''EXAMPLE CODE FOR "выдели Капустина" or "highlight Shilov":
```python
# For Russian names: use .str.contains() with partial match to handle word forms
# "Капустина" will match "Капустин", "Усову" will match "Усова"
# Use first 5-7 characters of the name to match different word endings

# Search in all string columns for the name (using first 6 chars for flexibility)
mask = df.iloc[:, 0].astype(str).str.contains("Капуст", case=False, na=False)
result = df[mask]

summary = f"Найдено записей: {len(result)}"
methodology = f"Поиск по частичному совпадению в первой колонке (используется начало имени/фамилии)"
```'''

content = re.sub(old_example, new_example, content, flags=re.MULTILINE)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] v6.6.2: Исправлен пример поиска!")
print("Убрана переменная search_name, используется прямое значение в str.contains()")
