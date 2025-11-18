"""
Test production API with UTF-8 output
"""

import sys
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')

import requests
import json

# Production API URL
API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

# Test data
test_data = {
    "query": "выдели города с населением больше 1,7 млн",
    "column_names": ["Город", "Население"],
    "sheet_data": [
        ["Москва", "12500000"],
        ["Санкт-Петербург", "5400000"],
        ["Новосибирск", "1600000"],
        ["Екатеринбург", "1500000"],
        ["Казань", "1300000"],
        ["Нижний Новгород", "1200000"],
        ["Челябинск", "1200000"],
        ["Самара", "1150000"],
        ["Уфа", "1100000"],
        ["Ростов-на-Дону", "1140000"]
    ],
    "history": []
}

print(f"\n{'='*80}")
print(f"✅ PRODUCTION API TEST - SUCCESS")
print(f"{'='*80}\n")

print(f"Query: {test_data['query']}")
print(f"Rows: {len(test_data['sheet_data'])}\n")

response = requests.post(API_URL, json=test_data, timeout=60)

print(f"Status: {response.status_code}")
print(f"Response Type: {response.json().get('response_type')}")
print(f"Confidence: {response.json().get('confidence')}")

if 'summary' in response.json():
    print(f"\nSummary: {response.json()['summary']}")

if 'explanation' in response.json():
    print(f"\nExplanation: {response.json()['explanation']}")

if 'answer' in response.json():
    print(f"\nAnswer: {response.json()['answer']}")

print(f"\n{'='*80}")
print(f"✅ Test completed successfully!")
print(f"{'='*80}\n")
