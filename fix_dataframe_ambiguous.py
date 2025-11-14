#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправление ошибки "The truth value of a DataFrame is ambiguous"
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

# Читаем файл
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем проблемную проверку DataFrame
# Строка: if names_found and exec_result.get("result"):
content = re.sub(
    r'if names_found and exec_result\.get\("result"\):',
    'if names_found:',
    content
)

# Записываем обратно
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] Fixed 'DataFrame is ambiguous' error!")
print("Removed problematic DataFrame boolean check")