#!/usr/bin/env python3
"""
Test v7.2.1 на production
Проверяет что .dtype ошибка исправлена
"""

import requests
import json

API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

# Тест 1: highlight_rows запрос (был .dtype error)
test_data = {
    "query": "выдели строки где Выручка меньше 600000 желтым цветом",
    "column_names": ["Канал", "Показы", "Клики", "CTR", "Лиды", "CPL", "Клиенты", "CAC", "Выручка"],
    "sheet_data": [
        ["Google Ads", 120000, 4800, 0.04, 1200, 250, 180, 1667, 950000],
        ["Facebook Ads", 90000, 3150, 0.035, 700, 285, 110, 2273, 510000],
        ["TikTok Ads", 150000, 6000, 0.04, 1500, 200, 210, 1428, 780000],
        ["Email", 40000, 3200, 0.08, 2600, 40, 520, 200, 520000],
        ["SEO", 80000, 4000, 0.05, 1000, 100, 150, 667, 600000]
    ]
}

print("="*80)
print("TEST v7.2.1 - Aggressive .dtype auto-fix")
print("="*80)
print(f"\nQuery: {test_data['query']}")
print(f"Testing against: {API_URL}")
print("\nSending request...")

try:
    response = requests.post(API_URL, json=test_data, timeout=60)

    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()

        print("\n[SUCCESS] No error!")
        print("\nResponse:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Проверка результата
        if "highlight_rows" in result:
            print(f"\n[OK] Highlight rows: {result['highlight_rows']}")
            print(f"[OK] Color: {result.get('highlight_color', 'N/A')}")
            print(f"[OK] Message: {result.get('highlight_message', 'N/A')}")

        if "error" in result:
            print(f"\n[FAIL] Response contains error: {result['error']}")
        else:
            print("\n[TEST PASSED] v7.2.1 works correctly!")

    else:
        print(f"\n[FAIL] Status {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n[ERROR] {e}")
