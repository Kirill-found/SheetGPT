"""
Query Validation Test - v7.8.3
Tests that nonsensical queries are rejected
"""
import requests
import json

API_URL = "http://localhost:8000/api/v1/formula"

# Minimal test data
test_data = [
    ["Ноутбук", "Москва", "150000", "Иванов", "Оплачен"],
    ["Монитор", "Москва", "80000", "Петров", "Оплачен"],
]

columns = ["Товар", "Город", "Сумма", "Менеджер", "Статус"]

print("\n" + "="*80)
print("SheetGPT v7.8.3 - Query Validation Test")
print("Testing that nonsensical queries are rejected")
print("="*80 + "\n")

test_queries = [
    {
        "query": "asdfghjkl",
        "should_reject": True,
        "reason": "No vowels - gibberish"
    },
    {
        "query": "qwrtpsdfg",
        "should_reject": True,
        "reason": "No vowels - random consonants"
    },
    {
        "query": "???",
        "should_reject": True,
        "reason": "No letters"
    },
    {
        "query": "ab",
        "should_reject": True,
        "reason": "Too short (<3 chars)"
    },
    {
        "query": "сумма заказов",
        "should_reject": False,
        "reason": "Valid Russian query"
    },
    {
        "query": "top 5 orders",
        "should_reject": False,
        "reason": "Valid English query"
    }
]

passed = 0
failed = 0

for i, test in enumerate(test_queries, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}: {test['query']}")
    print(f"{'='*80}")
    print(f"Expected: {'REJECT' if test['should_reject'] else 'ACCEPT'}")
    print(f"Reason: {test['reason']}")
    print()

    try:
        response = requests.post(
            API_URL,
            json={
                "query": test['query'],
                "column_names": columns,
                "sheet_data": test_data
            },
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            is_error = result.get('response_type') == 'error'

            if test['should_reject']:
                # Should be rejected
                if is_error:
                    print(f"[PASS] CORRECTLY REJECTED")
                    print(f"Error message: {result.get('summary')}")
                    passed += 1
                else:
                    print(f"[FAIL] Should reject but accepted")
                    print(f"Summary: {result.get('summary', 'N/A')[:100]}")
                    failed += 1
            else:
                # Should be accepted
                if not is_error:
                    print(f"[PASS] CORRECTLY ACCEPTED")
                    print(f"Summary: {result.get('summary', 'N/A')[:100]}")
                    passed += 1
                else:
                    print(f"[FAIL] Should accept but rejected")
                    print(f"Error: {result.get('summary')}")
                    failed += 1
        else:
            print(f"[FAIL] HTTP {response.status_code}")
            failed += 1

    except requests.exceptions.ConnectionError:
        print("[FAIL] Backend not running on port 8000")
        print("Start with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload --port 8000")
        break

    except Exception as e:
        print(f"[FAIL] {str(e)}")
        failed += 1

print("\n" + "="*80)
print(f"QUERY VALIDATION TEST SUMMARY")
print("="*80)
print(f"Total Tests: {len(test_queries)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success Rate: {(passed/len(test_queries)*100):.1f}%")
print()

if passed == len(test_queries):
    print("[SUCCESS] EXCELLENT! All queries validated correctly!")
    print("         v7.8.3 Query Validation works as expected")
else:
    print(f"[WARNING] {failed} tests failed")
print("="*80 + "\n")
