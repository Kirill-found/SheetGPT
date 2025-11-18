#!/usr/bin/env python3
"""
Test v7.2.1 с запросом пользователя который вызывал .dtype ошибку
Query: "выдели строки где ОП меньше 20 тысяч"
"""

import requests
import json

API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

# Данные пользователя с колонкой "ОП" (операционная прибыль)
test_data = {
    "query": "выдели строки где ОП меньше 20 тысяч",
    "column_names": ["Щетки", "Заказали на сумму", "ОП", "ОП в %", "Товар", "Сумма продаж", "ABC по прибыли"],
    "sheet_data": [
        ["Щетка 1", "р.100 000", 15000, "15%", "Товар A", "р.120 000", "A"],
        ["Щетка 2", "р.200 000", 35000, "17.5%", "Товар B", "р.220 000", "A"],
        ["Щетка 3", "р.50 000", 8000, "16%", "Товар C", "р.55 000", "B"],
        ["Щетка 4", "р.150 000", 25000, "16.7%", "Товар D", "р.160 000", "A"],
        ["Щетка 5", "р.80 000", 12000, "15%", "Товар E", "р.90 000", "B"]
    ]
}

print("="*80)
print("TEST v7.2.1 - User Query (previously failed with .dtype error)")
print("="*80)
print(f"Query: {test_data['query']}")
print(f"Testing against: {API_URL}")
print("\nExpected result: Highlight rows where OP < 20000")
print("Should highlight rows: 0, 2, 4 (OP: 15000, 8000, 12000)")
print("\nSending request...")

try:
    response = requests.post(API_URL, json=test_data, timeout=60)

    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()

        print("\n[SUCCESS] No error!")

        # Проверка результата
        if "highlight_rows" in result:
            print(f"\n[RESULT] Highlight rows: {result['highlight_rows']}")
            print(f"[RESULT] Color: {result.get('highlight_color', 'N/A')}")
            print(f"[RESULT] Message: {result.get('highlight_message', 'N/A')}")

        if "error" in result or "Ошибка" in str(result):
            print(f"\n[FAIL] Response contains error!")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("\n[TEST PASSED] v7.2.1 correctly handles user's query!")
            print("\nFull response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print(f"\n[FAIL] Status {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n[ERROR] {e}")
