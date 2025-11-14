#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6.6.3: Добавить ОБЯЗАТЕЛЬНОЕ требование переменной result в RULES
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем правило сразу ПЕРЕД "REQUIRED OUTPUT VARIABLES"
old_section = r'REQUIRED OUTPUT VARIABLES:'

new_section = '''CRITICAL: For search/highlight queries, you MUST create a 'result' variable containing the filtered DataFrame!
Example: result = df[df['column'].str.contains("search_term", case=False)]

REQUIRED OUTPUT VARIABLES:'''

content = content.replace(old_section, new_section)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] v6.6.3: Добавлено ОБЯЗАТЕЛЬНОЕ требование result!")
print("Теперь AI ОБЯЗАН создавать переменную result для поисковых запросов")
