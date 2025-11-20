"""
Quick integration test for v7.5.0
"""
import requests
import json
import time

print("\n" + "="*80)
print("SheetGPT v7.5.0 Integration Test")
print("="*80 + "\n")

# Test data
test_request = {
    "query": "Какая средняя сумма?",
    "column_names": ["Менеджер", "Сумма продаж", "Дата"],
    "sheet_data": [
        ["Иван", 10000, "2024-01-01"],
        ["Мария", 15000, "2024-01-02"],
        ["Петр", 12000, "2024-01-03"],
    ]
}

print(f"Sending request: {test_request['query']}")
print(f"Data shape: {len(test_request['sheet_data'])} rows x {len(test_request['column_names'])} columns")
print()

# Send request
start_time = time.time()

try:
    response = requests.post(
        "http://localhost:8001/api/v1/formula",
        json=test_request,
        timeout=30
    )

    duration_ms = (time.time() - start_time) * 1000

    if response.status_code == 200:
        result = response.json()

        print(f"SUCCESS! (HTTP 200)")
        print(f"Response time: {duration_ms:.0f}ms")
        print()
        print(f"Summary: {result.get('summary', 'N/A')}")
        print(f"Confidence: {result.get('confidence', 'N/A')}")
        print(f"Response type: {result.get('response_type', 'N/A')}")

        if result.get('function_used'):
            print(f"Function used: {result['function_used']}")

        # Check for v7.5.0 improvements in debug output
        print()
        print("="*80)
        print("Checking v7.5.0 Improvements in Backend Logs")
        print("="*80)
        print("Check backend logs for '[CLASSIFIER v7.5.0]' messages")
        print("Check backend logs for '[METRICS]' messages")
        print("Check backend logs for '[FUZZY]' messages")

    else:
        print(f"FAILED! HTTP {response.status_code}")
        print(f"Error: {response.text}")

except requests.exceptions.ConnectionError:
    print("Backend not running on port 8001")
    print("Start with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload --port 8001")

except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
