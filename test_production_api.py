"""
Test production API directly to see the exact error
"""

import requests
import json

# Production API URL
API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

# Test data - same as user's query
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
print(f"Testing Production API")
print(f"URL: {API_URL}")
print(f"{'='*80}\n")

print(f"Query: {test_data['query']}")
print(f"Columns: {test_data['column_names']}")
print(f"Rows: {len(test_data['sheet_data'])}\n")

try:
    print("Sending POST request...")
    response = requests.post(
        API_URL,
        json=test_data,
        headers={"Content-Type": "application/json"},
        timeout=60
    )

    print(f"\n{'='*80}")
    print(f"Response:")
    print(f"{'='*80}\n")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}\n")

    if response.status_code == 200:
        print("[SUCCESS] Request succeeded!")
        result = response.json()
        print(f"\nResponse Type: {result.get('response_type')}")
        print(f"Confidence: {result.get('confidence')}")
        if 'summary' in result:
            print(f"\nSummary: {result['summary']}")
    else:
        print(f"[ERROR] HTTP {response.status_code}")
        print(f"\nResponse Body:")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
        except:
            print(response.text)

except requests.exceptions.RequestException as e:
    print(f"\n[EXCEPTION] Request failed: {e}")
    import traceback
    traceback.print_exc()
