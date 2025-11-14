#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import subprocess
import sys

# Тестовые данные с разными цветами
tests = [
    ("зелёный", "#51CF66"),
    ("синий", "#339AF0"),
    ("жёлтый", "#FFD43B"),
    ("оранжевый", "#FF922B"),
]

print("=" * 70)
print("COMPREHENSIVE COLOR DETECTION TEST")
print("=" * 70)

all_passed = True

for color_name, expected_hex in tests:
    # Создаём запрос
    request = {
        "sheet_data": [
            ["Петрова", "Татьяна", "Васильевна"],
            ["Шилов", "Петр", "Семенович"],
        ],
        "column_names": ["Фамилия", "Имя", "Отчество"],
        "query": f"выдели строку с фамилией Шилов {color_name} цветом"
    }
    
    # Отправляем запрос
    result = subprocess.run(
        ['curl', '-s', '-X', 'POST', 
         'https://sheetgpt-production.up.railway.app/api/v1/formula',
         '-H', 'Content-Type: application/json',
         '-d', json.dumps(request)],
        capture_output=True,
        text=True
    )
    
    data = json.loads(result.stdout)
    actual_color = data.get('highlight_color')
    actual_rows = data.get('highlight_rows')
    
    # Проверяем результат
    if actual_rows == [2] and actual_color == expected_hex:
        print(f"✓ {color_name:12} -> {expected_hex} [OK]")
    else:
        print(f"✗ {color_name:12} -> Expected {expected_hex}, got {actual_color} [FAIL]")
        all_passed = False

print("=" * 70)
if all_passed:
    print("[SUCCESS] All colors work perfectly!")
else:
    print("[FAILED] Some colors not working correctly")
print("=" * 70)
