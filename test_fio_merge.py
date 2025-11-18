#!/usr/bin/env python3
"""
Тест объединения ФИО
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
        ["Шабаров", "Александр", "Владимирович"],
        ["Кононова", "Светлана", "Евгеньевна"],
        ["Колпаков", "Евгений", "Олегович"]
    ]
}

print("TEST: объедини ФИО в одну ячейку")
print("="*80)

response = requests.post(API_URL, json=test_data, timeout=60)

if response.status_code == 200:
    result = response.json()

    print(f"\nResponse type: {result.get('response_type')}")
    print(f"Summary: {result.get('summary')}")
    print(f"\nStructured data: {result.get('structured_data') is not None}")

    if result.get('structured_data'):
        data = result['structured_data']
        print(f"  Headers: {data.get('headers')}")
        print(f"  Rows count: {len(data.get('rows', []))}")
        if data.get('rows'):
            print(f"  First 3 rows:")
            for row in data['rows'][:3]:
                print(f"    {row}")

    print(f"\nHighlight rows: {result.get('highlight_rows')}")

    print("\n" + "="*80)
    print("Full response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

else:
    print(f"HTTP {response.status_code}")
