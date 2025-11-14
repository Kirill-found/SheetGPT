#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6.6.5: КРИТИЧЕСКИЙ FIX - except должен возвращать ответ, а не raise
Когда AI код падает с NameError, мы должны вернуть словарь с ошибкой в summary,
а не выбрасывать исключение наверх
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Находим весь except блок
old_except = r'''        except Exception as e:
            sys\.stdout = old_stdout
            error_msg = f"Ошибка выполнения кода: \{str\(e\)\}\\n\{traceback\.format_exc\(\)\}"

            # Пытаемся выполнить fallback код
            fallback_code = self\._generate_fallback_code\(df, code, error_msg\)
            if fallback_code:
                return self\._execute_python_code\(fallback_code, df\)

            raise Exception\(error_msg\)'''

new_except = '''        except Exception as e:
            sys.stdout = old_stdout
            error_msg = f"Ошибка: {str(e)}"

            # v6.6.5: RETURN вместо RAISE! Возвращаем словарь с ошибкой
            # Это позволит API вернуть ошибку в summary и продолжить работу
            print(f"[ERROR] Code execution failed: {error_msg}")

            return {
                'result': None,
                'summary': error_msg,
                'methodology': 'Выполнение кода не удалось',
                'key_findings': [],
                'confidence': 0.0,
                'professional_insights': None,
                'recommendations': None,
                'warnings': None,
                'code': code,
                'output': ''
            }'''

content = re.sub(old_except, new_except, content, flags=re.MULTILINE)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] v6.6.5: Except блок теперь возвращает словарь вместо raise!")
print("Теперь ошибки AI-кода будут возвращаться в summary, а не падать")
