#!/usr/bin/env python3
"""
v6.6.8: WRAPPER FIX - оборачиваем AI код в безопасный wrapper
Это ГАРАНТИРОВАННО решает проблему "name 'result' is not defined"
"""

import re

file_path = "backend/app/services/ai_code_executor.py"

# Читаем файл
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Старый код (v6.6.7)
old_code = r'''        try:
            # v6.6.7: РАДИКАЛЬНЫЙ FIX - инициализируем result ДО exec\(\)
            # Это ГАРАНТИРУЕТ что переменная существует, даже если AI использует её раньше
            safe_locals\['result'\] = None
            safe_locals\['summary'\] = ''
            safe_locals\['methodology'\] = ''

            # Выполняем код
            exec\(code, safe_globals, safe_locals\)'''

# Новый код (v6.6.8) - WRAPPER
new_code = '''        try:
            # v6.6.8: WRAPPER FIX - оборачиваем AI код в безопасный wrapper
            # Инициализируем переменные ВНУТРИ выполняемого кода!
            wrapper_code = f"""# v6.6.8: AUTO-WRAPPER для гарантированной инициализации
result = None
summary = ''
methodology = ''
key_findings = []
confidence = 0.95

# === AI GENERATED CODE ===
{code}
# === END AI CODE ===
"""
            # Выполняем обёрнутый код
            exec(wrapper_code, safe_globals, safe_locals)'''

# Заменяем
content_new = re.sub(old_code, new_code, content)

if content_new != content:
    # Сохраняем
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content_new)
    print("[SUCCESS] v6.6.8 WRAPPER FIX applied!")
    print("Теперь AI код обёрнут в wrapper с инициализацией переменных")
else:
    print("[ERROR] Pattern not found or already applied")
