#!/usr/bin/env python3
"""
Тест генерации таблиц из AI-знаний (v7.3.0)
"""

import requests
import json

API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

# Тест: создание таблицы без исходных данных
test_data = {
    "query": "создай таблицу со странами Европы и их населением в миллионах",
    "column_names": [],
    "sheet_data": []  # Пустые данные - AI сгенерирует таблицу
}

print("TEST: AI Table Generation - Страны Европы")
print("="*80)
print("Query:", test_data["query"])
print("Sheet data:", "EMPTY (AI will generate)")
print("\nSending request...")

response = requests.post(API_URL, json=test_data, timeout=90)

if response.status_code == 200:
    result = response.json()

    print(f"\nResponse type: {result.get('response_type')}")
    print(f"Summary: {result.get('summary')}")

    # Проверяем structured_data
    if result.get('structured_data'):
        data = result['structured_data']
        print(f"\n✓ Structured data generated!")
        print(f"  Headers: {data.get('headers')}")
        print(f"  Rows count: {len(data.get('rows', []))}")
        print(f"  Operation type: {data.get('operation_type')}")

        if data.get('rows'):
            print(f"\n  First 5 rows:")
            for i, row in enumerate(data['rows'][:5]):
                print(f"    {i+1}. {row}")

        print(f"\n✓ SUCCESS - AI generated table with {len(data.get('rows', []))} rows!")
    else:
        print("\n✗ No structured data in response")

    # Сохраняем полный ответ
    with open('test_ai_table_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nFull response saved to test_ai_table_result.json")

else:
    print(f"\nHTTP {response.status_code}")
    print(response.text)
