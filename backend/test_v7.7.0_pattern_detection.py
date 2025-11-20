"""
Test v7.7.0: Rule-Based Pattern Detection
Tests both patterns:
1. "топ 3 заказа в Москве" → filter_top_n with condition
2. "Сколько оплаченных заказов у каждого менеджера?" → aggregate_by_group
"""
import requests
import json

print("\n" + "="*80)
print("SheetGPT v7.7.0 - Test Rule-Based Pattern Detection")
print("="*80 + "\n")

# TEST 1: "топ 3 заказа в Москве" (PATTERN 1 - TOP N with condition)
test1_request = {
    "query": "топ 3 заказа в Москве",
    "column_names": ["Товар", "Город", "Сумма"],
    "sheet_data": [
        ["Ноутбук", "Москва", "150000"],
        ["Мышка", "Москва", "1200"],
        ["Монитор", "Москва", "80000"],
        ["Клавиатура", "Москва", "3500"],
        ["Наушники", "Москва", "5000"],
        ["Веб-камера", "Санкт-Петербург", "7000"],
    ]
}

# TEST 2: "Сколько оплаченных заказов у каждого менеджера?" (PATTERN 2 - GROUP BY)
test2_request = {
    "query": "Сколько оплаченных заказов у каждого менеджера?",
    "column_names": ["Товар", "Менеджер", "Сумма", "Статус", "Дата"],
    "sheet_data": [
        ["Ноутбук", "Иванов", "150000", "Оплачен", "2024-01-15"],
        ["Мышка", "Иванов", "1200", "Оплачен", "2024-01-16"],
        ["Монитор", "Петров", "80000", "Оплачен", "2024-01-17"],
        ["Клавиатура", "Иванов", "3500", "Оплачен", "2024-01-18"],
        ["Наушники", "Сидоров", "5000", "Отменен", "2024-01-19"],
        ["Веб-камера", "Иванов", "7000", "Оплачен", "2024-01-20"],
        ["Микрофон", "Сидоров", "4500", "Оплачен", "2024-01-21"],
        ["Стол", "Сидоров", "25000", "Оплачен", "2024-01-22"],
    ]
}

tests = [
    ("TEST 1: 'топ 3 заказа в Москве'", test1_request, "filter_top_n", 3),
    ("TEST 2: 'Сколько заказов у каждого менеджера?'", test2_request, "aggregate_by_group", None),
]

passed = 0
failed = 0

for test_name, test_request, expected_function, expected_rows in tests:
    print(f"\n{test_name}")
    print(f"   Query: {test_request['query']}")
    print(f"   Expected function: {expected_function}")
    if expected_rows:
        print(f"   Expected rows: {expected_rows}")

    try:
        response = requests.post(
            "http://localhost:8000/api/v1/formula",
            json=test_request,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            function_used = result.get('function_used', 'N/A')
            summary = result.get('summary', 'N/A')

            print(f"   [RESULT] Function used: {function_used}")
            print(f"   [RESULT] Summary: {summary[:200]}...")

            # Check if correct function was called
            if function_used == expected_function:
                # Additional check for TEST 1: should return exactly 3 rows
                if expected_rows:
                    structured_data = result.get('structured_data')
                    if structured_data:
                        actual_rows = len(structured_data.get('rows', []))
                        if actual_rows == expected_rows:
                            print(f"   [OK] PASSED - Correct function and {actual_rows} rows returned!")
                            passed += 1
                        else:
                            print(f"   [FAIL] FAILED - Correct function but wrong row count: {actual_rows} (expected {expected_rows})")
                            failed += 1
                    else:
                        # Small result - check if summary mentions 3 items
                        if "3" in summary or "три" in summary.lower():
                            print(f"   [OK] PASSED - Correct function and result!")
                            passed += 1
                        else:
                            print(f"   [FAIL] FAILED - Result doesn't mention 3 items")
                            failed += 1
                else:
                    # TEST 2: just check function is correct
                    print(f"   [OK] PASSED - Correct function used!")
                    passed += 1
            else:
                print(f"   [FAIL] FAILED - Wrong function: {function_used} (expected {expected_function})")
                failed += 1

            # Show methodology
            print(f"   [METHODOLOGY] {result.get('methodology', 'N/A')[:150]}...")

        else:
            print(f"   [FAIL] FAILED - HTTP {response.status_code}")
            print(f"   Error: {response.text[:200]}")
            failed += 1

    except requests.exceptions.ConnectionError:
        print("   [FAIL] FAILED - Backend not running on port 8000")
        print("   Start with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload --port 8000")
        failed += 1

    except Exception as e:
        print(f"   [FAIL] FAILED - {str(e)}")
        failed += 1

print("\n" + "="*80)
print(f"RESULTS: {passed} passed, {failed} failed")
print("="*80)

if failed == 0:
    print("\n[SUCCESS] v7.7.0 WORKS! Pattern Detection bypasses GPT-4o successfully!\n")
else:
    print("\n[WARNING] Some tests failed. Check backend logs for details.\n")
