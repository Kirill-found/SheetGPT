#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6.6.6: КРИТИЧЕСКИЙ FIX - ЖЁСТКИЙ порядок создания переменных
AI постоянно использует result ДО того как создаёт его, вызывая NameError
Добавляем МАКСИМАЛЬНО ЯВНОЕ требование о порядке переменных
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем КРИТИЧЕСКОЕ правило о порядке ПЕРЕД примером
old_example_start = r'''EXAMPLE CODE FOR "выдели Капустина" or "highlight Shilov":'''

new_rules_and_example = r'''CRITICAL VARIABLE ORDER - ALWAYS FOLLOW THIS SEQUENCE:
========================================================
1. FIRST: Create 'result' variable (DO NOT use it before creating!)
2. SECOND: Create 'summary' variable (now you can safely use 'result')
3. THIRD: Create 'methodology' variable

WRONG ORDER (causes NameError):
```python
summary = f"Found: {len(result)}"  # ERROR! 'result' not defined yet
result = df[mask]
```

CORRECT ORDER:
```python
result = df[mask]  # Create result FIRST
summary = f"Found: {len(result)}"  # Now can use result safely
```

EXAMPLE CODE FOR "выдели Капустина" or "highlight Shilov":'''

content = content.replace(old_example_start, new_rules_and_example)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] v6.6.6: Добавлено КРИТИЧЕСКОЕ правило о порядке переменных!")
print("Теперь AI ОБЯЗАН создать result ПЕРЕД тем как использовать его")
