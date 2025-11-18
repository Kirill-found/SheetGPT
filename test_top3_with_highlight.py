#!/usr/bin/env python3
"""
Тест с явным запросом на выделение
"""

import requests
import json

API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

test_data = {
    "query": "выдели топ 3 товара по продажам",
    "column_names": ["Название", "Значение"],
    "sheet_data": [
        ["Товар 14", 588530.04],
        ["Товар 13", 487634.84],
        ["Товар 2", 411281.76],
        ["Товар 8", 378191.85],
        ["Товар 3", 343950.23],
        ["Товар 1", 278988.32],
        ["Товар 19", 262513.44],
        ["Товар 20", 227400.15]
    ]
}

print("TEST: выдели топ 3 товара по продажам")
print(f"Expected highlight: [2, 3, 4] (Товар 14, 13, 2)\n")

response = requests.post(API_URL, json=test_data, timeout=60)

if response.status_code == 200:
    result = response.json()

    print(f"Response type: {result.get('response_type')}")
    print(f"Highlight rows: {result.get('highlight_rows')}")
    print(f"Highlight color: {result.get('highlight_color')}")

    expected = [2, 3, 4]
    actual = result.get('highlight_rows')

    if actual == expected:
        print("\n✓ SUCCESS - Highlight correct!")
    else:
        print(f"\n✗ FAIL - Expected {expected}, got {actual}")

    print(f"\nSummary: {result.get('summary')}")
else:
    print(f"HTTP {response.status_code}")
