#!/usr/bin/env python3
"""
Тест с точными данными пользователя из скриншота
Query: "выдели строки где ОП меньше 20 тысяч"
"""

import requests
import json
import time

API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

# ТОЧНЫЕ данные как в скриншоте пользователя
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
print("EXACT USER DATA TEST - Production v7.2.1")
print("="*80)
print(f"Query: {test_data['query']}")
print(f"API: {API_URL}")
print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("\nSending request...")

try:
    response = requests.post(API_URL, json=test_data, timeout=60)

    print(f"\nHTTP Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()

        # Check for dtype error
        result_str = json.dumps(result, ensure_ascii=False)

        if "dtype" in result_str.lower():
            print("\n[FAIL] DTYPE ERROR FOUND IN RESPONSE!")
            print("="*80)
            print(result_str)
            print("="*80)
        elif "error" in result or "Ошибка" in result_str:
            print("\n[FAIL] ERROR IN RESPONSE!")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("\n[SUCCESS] No dtype error!")

            if "highlight_rows" in result:
                print(f"\nHighlight rows: {result['highlight_rows']}")
                print(f"Color: {result.get('highlight_color')}")

            print("\nFull response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n[FAIL] HTTP {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
