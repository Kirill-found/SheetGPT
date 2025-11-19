"""
Test: Check if v7.8.0 fixes the original two problems
"""
import requests
import json

print("\n" + "="*80)
print("Testing Original Problems - v7.8.0 Hybrid Intelligence")
print("="*80 + "\n")

# Problem 1: "top 3 zakaza v Moskve"
test1 = {
    "query": "top 3 zakaza v Moskve",
    "column_names": ["Tovar", "Gorod", "Summa"],
    "sheet_data": [
        ["Noutbuk", "Moskva", "150000"],
        ["Myshka", "Moskva", "1200"],
        ["Monitor", "Moskva", "80000"],
        ["Klaviatura", "Moskva", "3500"],
        ["Naushniki", "Moskva", "5000"],
        ["Veb-kamera", "Sankt-Peterburg", "7000"],
    ]
}

# Problem 2: "Skolko oplachennykh zakazov u kazhdogo menedzhera?"
test2 = {
    "query": "Skolko oplachennykh zakazov u kazhdogo menedzhera?",
    "column_names": ["Tovar", "Menedzher", "Summa", "Status", "Data"],
    "sheet_data": [
        ["Noutbuk", "Ivanov", "150000", "Oplachen", "2024-01-15"],
        ["Myshka", "Ivanov", "1200", "Oplachen", "2024-01-16"],
        ["Monitor", "Petrov", "80000", "Oplachen", "2024-01-17"],
        ["Klaviatura", "Ivanov", "3500", "Oplachen", "2024-01-18"],
        ["Naushniki", "Sidorov", "5000", "Otmenen", "2024-01-19"],
        ["Veb-kamera", "Ivanov", "7000", "Oplachen", "2024-01-20"],
        ["Mikrofon", "Sidorov", "4500", "Oplachen", "2024-01-21"],
        ["Stol", "Sidorov", "25000", "Oplachen", "2024-01-22"],
    ]
}

tests = [
    {
        "name": "PROBLEM 1: 'top 3 zakaza v Moskve'",
        "request": test1,
        "expected_function": "filter_top_n",
        "wrong_function": "filter_rows",
        "description": "Should call filter_top_n, NOT filter_rows"
    },
    {
        "name": "PROBLEM 2: 'Skolko oplachennykh zakazov u kazhdogo menedzhera?'",
        "request": test2,
        "expected_function": "aggregate_by_group",
        "wrong_function": "calculate_sum",
        "description": "Should call aggregate_by_group, NOT calculate_sum"
    }
]

print("These are the EXACT queries that failed in v7.7.0")
print("If v7.8.0 works, both should call the CORRECT function\n")

passed = 0
failed = 0

for test in tests:
    print("="*80)
    print(f"TEST: {test['name']}")
    print("="*80)
    print(f"Query: {test['request']['query']}")
    print(f"Expected: {test['expected_function']}")
    print(f"Must NOT call: {test['wrong_function']}")
    print()

    try:
        response = requests.post(
            "http://localhost:8000/api/v1/formula",
            json=test['request'],
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            function_used = result.get('function_used', 'N/A')
            summary = result.get('summary', 'N/A')

            print(f"[RESULT]")
            print(f"  Function called: {function_used}")
            print(f"  Summary: {summary[:150]}...")
            print()

            # Check if correct function was called
            if function_used == test['expected_function']:
                print(f"SUCCESS - Correct function '{function_used}' was called!")
                passed += 1
            elif function_used == test['wrong_function']:
                print(f"FAILED - Wrong function '{function_used}' was called (same as v7.7.0)")
                print(f"         Expected: {test['expected_function']}")
                failed += 1
            else:
                print(f"PARTIAL - Different function '{function_used}' was called")
                print(f"          Expected: {test['expected_function']}")
                print(f"          This is different from v7.7.0, but still not ideal")
                failed += 1

            # Show methodology
            if result.get('methodology'):
                print(f"\n[METHODOLOGY]")
                print(f"  {result['methodology'][:200]}...")

        else:
            print(f"FAILED - HTTP {response.status_code}")
            print(f"Error: {response.text[:300]}")
            failed += 1

    except requests.exceptions.ConnectionError:
        print("FAILED - Backend not running on port 8000")
        print("Start with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload --port 8000")
        failed += 1

    except Exception as e:
        print(f"FAILED - {str(e)}")
        failed += 1

    print()

print("="*80)
print(f"FINAL RESULTS: {passed}/2 tests passed, {failed}/2 tests failed")
print("="*80)

if passed == 2:
    print("\nSUCCESS! v7.8.0 FIXED BOTH ORIGINAL PROBLEMS!")
    print("The Hybrid Intelligence system is working correctly.\n")
elif passed == 1:
    print("\nPARTIAL SUCCESS - One problem fixed, one still failing")
    print("Review the failed test above for details.\n")
else:
    print("\nFAILURE - Both problems still exist")
    print("v7.8.0 needs debugging.\n")
