#!/usr/bin/env python3
"""
Тест запроса "Топ 3 товара по продажам"
Проверяет правильность highlight
"""

import requests
import json

API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

# Данные из скриншота
test_data = {
    "query": "Топ 3 товара по продажам",
    "column_names": ["Название", "Значение"],
    "sheet_data": [
        ["Товар 14", 588530.04],
        ["Товар 13", 487634.84],
        ["Товар 2", 411281.76],
        ["Товар 8", 378191.85],
        ["Товар 3", 343950.23],
        ["Товар 1", 278988.32],
        ["Товар 19", 262513.44],
        ["Товар 20", 227400.15],
        ["Товар 4", 215409.04],
        ["Товар 16", 213847.33],
        ["Товар 15", 184702.95],
        ["Товар 17", 182803.92],
        ["Товар 10", 177892.2],
        ["Товар 18", 134890.56],
        ["Товар 7", 132461.84],
        ["Товар 5", 80192.3],
        ["Товар 12", 65620.65],
        ["Товар 11", 51876.48]
    ]
}

print("="*80)
print("TEST: Top 3 товара по продажам")
print("="*80)
print(f"\nExpected top 3:")
print("1. Товар 14: 588530.04 (row 2)")
print("2. Товар 13: 487634.84 (row 3)")
print("3. Товар 2: 411281.76 (row 4)")
print(f"\nSending request to: {API_URL}")

try:
    response = requests.post(API_URL, json=test_data, timeout=60)

    if response.status_code == 200:
        result = response.json()

        print(f"\n[Response Type]: {result.get('response_type')}")
        print(f"[Function Used]: {result.get('function_used', 'N/A')}")

        if "summary" in result:
            print(f"\n[Summary]: {result['summary']}")

        if "structured_data" in result and result["structured_data"]:
            data = result["structured_data"]
            print(f"\n[Structured Data]:")
            print(f"  Headers: {data.get('headers')}")
            print(f"  Rows count: {len(data.get('rows', []))}")
            if data.get('rows'):
                print(f"  First 3 rows:")
                for i, row in enumerate(data['rows'][:3]):
                    print(f"    {i+1}. {row}")

        if "highlight_rows" in result:
            print(f"\n[Highlight Rows]: {result['highlight_rows']}")
            print(f"[Highlight Color]: {result.get('highlight_color')}")

            expected_rows = [2, 3, 4]  # 1-based index with header
            actual_rows = result['highlight_rows']

            if set(actual_rows) == set(expected_rows):
                print("\n[OK] Highlight rows correct!")
            else:
                print(f"\n[FAIL] Highlight rows WRONG!")
                print(f"  Expected: {expected_rows}")
                print(f"  Actual: {actual_rows}")
                print(f"  Missing: {set(expected_rows) - set(actual_rows)}")
                print(f"  Extra: {set(actual_rows) - set(expected_rows)}")

        print("\n[Full Response]:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print(f"\n[FAIL] HTTP {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
