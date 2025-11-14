#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Добавляет пример кода для поиска русских имён с учётом падежей
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем пример после примера с топ-3 товаров
example_section = r'''warnings = \["Критическая зависимость от ограниченного числа SKU"\]
```

NOW GENERATE CODE FOR THIS QUESTION:'''

new_example = r'''warnings = ["Критическая зависимость от ограниченного числа SKU"]
```

EXAMPLE CODE FOR "выдели Капустина" or "highlight Shilov":
```python
# For Russian names: use partial matching to handle word forms (Капустин/Капустина/Капустину)
search_name = "Капустин"  # Extract base form (remove common endings like -а, -у, -ой)

# Find rows containing the name (partial match)
result = df[df.iloc[:, 0].astype(str).str.contains(search_name[:6], case=False, na=False)]

summary = f"Найдено записей с '{search_name}': {len(result)}"
methodology = f"Поиск по частичному совпадению имени/фамилии в первой колонке"
```

NOW GENERATE CODE FOR THIS QUESTION:'''

content = re.sub(example_section, new_example, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] Добавлен пример поиска русских имён!")
