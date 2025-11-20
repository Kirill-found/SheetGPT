"""
Revenue Temporal Queries Test - v7.8.8
Tests that revenue queries with dates work correctly
FIX: calculate_sum now recognizes "выручка" and supports date filtering via contains
"""
import requests
import json

API_URL = "http://localhost:8000/api/v1/formula"

# Test data with dates in February and March
test_data = [
    ["Ноутбук", "Москва", "150000", "Иванов", "Оплачен", "2024-02-05"],
    ["Монитор", "Москва", "80000", "Петров", "Оплачен", "2024-02-10"],
    ["Мышка", "Санкт-Петербург", "1200", "Иванов", "Оплачен", "2024-02-15"],
    ["Клавиатура", "Москва", "3500", "Петров", "Оплачен", "2024-03-01"],
    ["Наушники", "Москва", "5000", "Сидоров", "Оплачен", "2024-03-05"],
    ["Веб-камера", "Санкт-Петербург", "7000", "Иванов", "Отменен", "2024-02-20"],
]

columns = ["Товар", "Город", "Сумма", "Менеджер", "Статус", "Дата"]

print("\n" + "="*80)
print("SheetGPT v7.8.8 - Revenue Temporal Queries Test")
print("Testing that 'выручка в феврале' works correctly")
print("="*80 + "\n")

# Expected results (manually calculated)
# February revenue (Оплачен only): 150000 + 80000 + 1200 = 231,200
# March revenue (Оплачен only): 3500 + 5000 = 8,500
# February ALL (including Отменен): 150000 + 80000 + 1200 + 7000 = 238,200

test_cases = [
    {
        "query": "выручка в феврале",
        "expected_range": (230000, 240000),  # Should sum February paid orders
        "description": "Revenue in February (paid orders)",
        "must_use_function": "calculate_sum"
    },
    {
        "query": "выручка за март",
        "expected_range": (8000, 9000),  # Should sum March paid orders
        "description": "Revenue in March (paid orders)",
        "must_use_function": "calculate_sum"
    },
    {
        "query": "доход в феврале",
        "expected_range": (230000, 240000),  # "доход" is synonym for "выручка"
        "description": "Income in February (paid orders)",
        "must_use_function": "calculate_sum"
    },
    {
        "query": "оборот за март",
        "expected_range": (8000, 9000),  # "оборот" is another synonym
        "description": "Turnover in March (paid orders)",
        "must_use_function": "calculate_sum"
    },
    {
        "query": "продажи в феврале",
        "expected_range": (230000, 240000),  # "продажи" should also work
        "description": "Sales in February (paid orders)",
        "must_use_function": "calculate_sum"
    }
]

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}: {test['query']}")
    print(f"{'='*80}")
    print(f"Description: {test['description']}")
    print(f"Expected range: {test['expected_range'][0]:,} - {test['expected_range'][1]:,}")
    print(f"Must use function: {test['must_use_function']}")
    print()

    try:
        response = requests.post(
            API_URL,
            json={
                "query": test['query'],
                "column_names": columns,
                "sheet_data": test_data
            },
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()

            print(f"[RESPONSE]")
            print(f"  Function: {result.get('function_used', 'N/A')}")
            print(f"  Tier: {result.get('tier_used', 'N/A')}")
            print(f"  Summary: {result.get('summary', 'N/A')[:150]}")
            print()

            function_used = result.get('function_used', '')

            # Check if correct function was used
            if test['must_use_function'] not in function_used:
                print(f"\n[FAIL] Wrong function: {function_used}")
                print(f"       Expected: {test['must_use_function']}")
                print(f"       BUG: System not recognizing revenue keywords!")
                failed += 1
                continue

            # Extract numeric result from summary
            import re
            summary = result.get('summary', '')
            # Match numbers with spaces, commas, or plain (e.g., "231 200" or "231,200" or "231200")
            number_match = re.search(r'(\d[\d\s,]*\d|\d)', summary)

            if number_match:
                number_str = number_match.group(0).replace(',', '').replace(' ', '')
                actual_value = float(number_str)
                print(f"  Extracted value: {actual_value:,.2f}")

                # Check if in range
                if test['expected_range'][0] <= actual_value <= test['expected_range'][1]:
                    print(f"\n[PASS] Correct revenue calculation")
                    print(f"   Used: {function_used}")
                    passed += 1
                else:
                    print(f"\n[FAIL] Value {actual_value:,.2f} outside expected range {test['expected_range']}")
                    print(f"   Used: {function_used}")
                    failed += 1
            else:
                print(f"\n[FAIL] Could not parse numeric result from: {summary}")
                failed += 1

        else:
            print(f"[FAIL] HTTP {response.status_code}")
            print(f"Error: {response.text[:200]}")
            failed += 1

    except requests.exceptions.ConnectionError:
        print("[FAIL] Backend not running on port 8000")
        print("Start with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload --port 8000")
        break

    except Exception as e:
        print(f"[FAIL] {str(e)}")
        failed += 1

print("\n" + "="*80)
print(f"REVENUE TEMPORAL QUERIES TEST SUMMARY")
print("="*80)
print(f"Total Tests: {len(test_cases)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success Rate: {(passed/len(test_cases)*100):.1f}%")
print()

if passed == len(test_cases):
    print("[SUCCESS] EXCELLENT! All revenue temporal queries work correctly!")
    print("          v7.8.8 calculate_sum now recognizes revenue keywords and date filtering")
elif passed >= len(test_cases) * 0.75:
    print("[SUCCESS] GOOD! Most revenue queries working")
    print(f"          {failed} queries need investigation")
else:
    print("[WARNING] NEEDS WORK - Several revenue queries failed")
    print("          calculate_sum may still be missing revenue keywords or date support")
print("="*80 + "\n")
