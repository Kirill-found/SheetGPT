#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6.6.4: КРИТИЧЕСКИЙ FIX - добавить FALLBACK для result
AI игнорирует инструкции, поэтому создаём result автоматически если его нет
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Находим место где извлекаем result
old_extraction = r'''            # Извлекаем результаты
            result = safe_locals\.get\('result', None\)'''

new_extraction = r'''            # Извлекаем результаты
            result = safe_locals.get('result', None)

            # v6.6.4: FALLBACK если AI не создал result (что происходит постоянно)
            if result is None:
                # Проверяем есть ли другие DataFrame в locals
                for var_name, var_value in safe_locals.items():
                    if hasattr(var_value, 'index') and hasattr(var_value, 'columns'):
                        result = var_value
                        print(f"[FALLBACK] Using '{var_name}' as result (AI forgot to create 'result')")
                        break
                # Если ничего не нашли, используем весь df
                if result is None and 'df' in safe_globals:
                    result = safe_globals['df']
                    print(f"[FALLBACK] Using entire 'df' as result (AI didn't filter anything)")'''

content = re.sub(old_extraction, new_extraction, content, flags=re.MULTILINE)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] v6.6.4: Добавлен FALLBACK для result!")
print("Теперь если AI забудет создать result, используем df или любой DataFrame из locals")
