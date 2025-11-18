#!/usr/bin/env python3
"""
Тест генерации формулы для merge операций (v7.2.5)
"""

import requests
import json

API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

test_data = {
    "query": "объедини ФИО в одну ячейку",
    "column_names": ["Фамилия", "Имя", "Отчество"],
    "sheet_data": [
        ["Петрова", "Татьяна", "Васильевна"],
        ["Смирнов", "Антон", "Иванович"],
        ["Шабаров", "Александр", "Владимирович"]
    ]
}

print("TEST: объедини ФИО в одну ячейку")
print("="*80)
print("\nExpected formula: =A2&\" \"&B2&\" \"&C2")
print("\nSending request...")

response = requests.post(API_URL, json=test_data, timeout=60)

if response.status_code == 200:
    result = response.json()

    print(f"\nResponse type: {result.get('response_type')}")
    print(f"Summary: {result.get('summary')}")

    # Проверяем наличие формулы
    if "formula" in result:
        formula = result["formula"]
        print(f"\n✓ Formula generated: {formula}")

        expected = '=A2&" "&B2&" "&C2'
        if formula == expected:
            print("✓ Formula CORRECT!")
        else:
            print(f"✗ Formula WRONG!")
            print(f"  Expected: {expected}")
            print(f"  Got: {formula}")
    else:
        print("\n✗ NO FORMULA in response!")

    # Проверяем structured_data
    if result.get('structured_data'):
        data = result['structured_data']
        print(f"\n✓ Structured data present")
        print(f"  Headers: {data.get('headers')}")
        print(f"  Rows count: {len(data.get('rows', []))}")
        if data.get('rows'):
            print(f"  First row: {data['rows'][0]}")
    else:
        print("\n✗ No structured data")

    print("\n" + "="*80)
    print("Full response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

else:
    print(f"HTTP {response.status_code}")
    print(response.text)
