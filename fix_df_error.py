#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправление ошибки 'df' is not defined в ai_code_executor.py
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

# Читаем файл
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Добавляем sheet_data в сигнатуру _format_response
content = re.sub(
    r'def _format_response\(self, exec_result: Dict\[str, Any\], code: str, query: str, custom_context: Optional\[str\] = None\)',
    'def _format_response(self, exec_result: Dict[str, Any], code: str, query: str, sheet_data: List[List[Any]], custom_context: Optional[str] = None)',
    content
)

# 2. Обновляем вызов _format_response чтобы передавать sheet_data
content = re.sub(
    r'final_response = self\._format_response\(result, generated_code, query, safe_custom_context\)',
    'final_response = self._format_response(result, generated_code, query, sheet_data, safe_custom_context)',
    content
)

# 3. Создаем df из sheet_data в начале _format_response
# Находим место после "Форматирует финальный ответ"
pattern = r'(def _format_response.*?\n.*?Форматирует финальный ответ.*?\n.*?\""")'
replacement = r'''\1
        # Создаем DataFrame для поиска по данным
        if sheet_data:
            # Получаем column_names из первой строки exec_result если есть
            column_names = exec_result.get('column_names', [f'col_{i}' for i in range(len(sheet_data[0]))] if sheet_data else [])
            df = pd.DataFrame(sheet_data, columns=column_names)
        else:
            df = None'''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Записываем обратно
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed 'df' is not defined error!")
print("📋 Changes made:")
print("1. Added sheet_data parameter to _format_response")
print("2. Updated _format_response call to pass sheet_data")
print("3. Created df from sheet_data inside _format_response")