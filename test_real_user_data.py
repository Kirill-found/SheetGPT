"""
Test with exact user data from screenshot
"""

import sys
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')

import requests
import json

# Production API URL
API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

# Exact user data from screenshot
test_data = {
    "query": "выдели города с населением больше 1,7 млн",
    "column_names": ["Город", "Население (млн)"],
    "sheet_data": [
        ["Москва", "12,6"],
        ["Санкт-Петербург", "5,4"],
        ["Новосибирск", "1,6"],
        ["Екатеринбург", "1,5"],
        ["Казань", "1,3"],
        ["Нижний Новгород", "1,2"],
        ["Челябинск", "1,2"],
        ["Самара", "1,2"],
        ["Омск", "1,1"],
        ["Ростов-на-Дону", "1,1"]
    ],
    "history": []
}

print(f"\n{'='*80}")
print(f"Testing with EXACT user data from screenshot")
print(f"{'='*80}\n")

print(f"Query: {test_data['query']}")
print(f"Columns: {test_data['column_names']}")
print(f"Rows: {len(test_data['sheet_data'])}")
print(f"\nFirst 3 rows:")
for i, row in enumerate(test_data['sheet_data'][:3], 1):
    print(f"  {i}. {row[0]}: {row[1]} млн")

print(f"\nExpected result: Should highlight rows 1-2 (Москва, СПб)")
print(f"{'='*80}\n")

try:
    response = requests.post(API_URL, json=test_data, timeout=60)

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ SUCCESS - Response received")
        print(f"\nResponse keys: {list(result.keys())}")
        print(f"Response Type: {result.get('response_type')}")
        print(f"Confidence: {result.get('confidence')}")

        if 'summary' in result:
            print(f"\nSummary: {result['summary']}")

        if 'explanation' in result:
            print(f"\nExplanation: {result['explanation']}")

        if 'answer' in result:
            print(f"\nAnswer: {result['answer']}")

        if 'methodology' in result:
            print(f"\nMethodology: {result['methodology']}")

        if 'function_call' in result:
            print(f"\nFunction Call: {json.dumps(result['function_call'], indent=2, ensure_ascii=False)}")

        if 'highlight_data' in result:
            print(f"\nHighlight Data: {json.dumps(result['highlight_data'], indent=2, ensure_ascii=False)}")

        print(f"\n{'='*80}")
        print(f"Full response:")
        print(f"{'='*80}")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print(f"\n❌ ERROR - HTTP {response.status_code}")
        print(f"\nResponse:")
        try:
            error = response.json()
            print(json.dumps(error, indent=2, ensure_ascii=False))
        except:
            print(response.text)

except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
