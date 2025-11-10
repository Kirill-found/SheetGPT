# -*- coding: utf-8 -*-
"""Тест постпроцессинга русских формул ИНДЕКС/ПОИСКПОЗ"""
import sys
import json
import subprocess
import time

print("=== ОЖИДАНИЕ ДЕПЛОЯ RAILWAY (3 минуты) ===")
print()
time.sleep(180)

print("=== ТЕСТ РУССКОЙ ФОРМУЛЫ ИНДЕКС/ПОИСКПОЗ ===")
print()

# Запрос к API
result = subprocess.run([
    'curl', '-s', '-X', 'POST',
    'https://sheetgpt-production.up.railway.app/api/v1/formula',
    '-H', 'Content-Type: application/json',
    '-d', '@C:/SheetGPT/test_russian_formula.json'
], capture_output=True, text=True, encoding='utf-8')

response = json.loads(result.stdout)
insights = response.get('insights', [])

if insights and len(insights) > 0:
    formula = insights[0].get('config', {}).get('formula', '')
else:
    formula = response.get('formula', '')

print(f'Формула: {formula}')
print()

# Проверки
has_ru_index = 'ИНДЕКС' in formula or 'INDEX' in formula
has_ru_match = 'ПОИСКПОЗ' in formula or 'MATCH' in formula
search_in_g = 'G:G' in formula or '$G:' in formula
return_from_h = 'H:H' in formula or '$H:' in formula
no_wrong_col = '$I:' not in formula and 'I:I' not in formula
is_russian = 'ИНДЕКС' in formula and 'ПОИСКПОЗ' in formula

print(f'✓ Содержит ИНДЕКС/INDEX: {has_ru_index}')
print(f'✓ Содержит ПОИСКПОЗ/MATCH: {has_ru_match}')
print(f'✓ Использует РУССКИЕ названия: {is_russian}')
print(f'✓ Ищет в G:G (текст): {search_in_g}')
print(f'✓ Возвращает из H:H (числа): {return_from_h}')
print(f'✓ НЕ использует I:I: {no_wrong_col}')
print()

status = 'ОТЛИЧНО!' if (has_ru_index and has_ru_match and search_in_g and return_from_h and no_wrong_col) else 'ОШИБКА'
print(f'РЕЗУЛЬТАТ: {status}')
