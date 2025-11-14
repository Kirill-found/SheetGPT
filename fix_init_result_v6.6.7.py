#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6.6.7: РАДИКАЛЬНЫЙ FIX - инициализация result ДО exec()
AI игнорирует все инструкции, поэтому делаем result = None ПЕРЕД выполнением кода
Это ГАРАНТИРУЕТ что переменная существует, даже если AI использует её раньше времени
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Находим строку exec(code, safe_globals, safe_locals)
old_exec = r'''        try:
            # Выполняем код
            exec\(code, safe_globals, safe_locals\)'''

new_exec = '''        try:
            # v6.6.7: РАДИКАЛЬНЫЙ FIX - инициализируем result ДО exec()
            # Это ГАРАНТИРУЕТ что переменная существует, даже если AI использует её раньше
            safe_locals['result'] = None
            safe_locals['summary'] = ''
            safe_locals['methodology'] = ''

            # Выполняем код
            exec(code, safe_globals, safe_locals)'''

content = re.sub(old_exec, new_exec, content, flags=re.MULTILINE)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] v6.6.7: Инициализация result, summary, methodology ДО exec()!")
print("Теперь переменные ВСЕГДА существуют, даже если AI использует их в неправильном порядке")
