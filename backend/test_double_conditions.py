"""
Double Conditions Test - v7.8.6
Tests queries with multiple conditions (filter + sort + limit)

BUG REPORT: "Топ 3 самых дорогих оплаченных заказа"
Returns orders with status "Ожидает" when should only return "Оплачен"
"""
import requests
import json

API_URL = "http://localhost:8000/api/v1/formula"

# Test data with mixed statuses
test_data = [
    ["Ноутбук", "Екатеринбург", "145000", "Петров", "Ожидает оплаты", "2024-02-05"],
    ["Монитор", "Москва", "180000", "Иванов", "Оплачен", "2024-02-01"],
    ["Сервер", "Санкт-Петербург", "250000", "Сидоров", "Оплачен", "2024-02-03"],
    ["Мышка", "Москва", "1200", "Иванов", "Оплачен", "2024-02-02"],
    ["Клавиатура", "Москва", "3500", "Петров", "Ожидает оплаты", "2024-02-04"],
    ["Принтер", "Екатеринбург", "85000", "Сидоров", "Оплачен", "2024-02-06"],
    ["Стол", "Москва", "25000", "Иванов", "Отменен", "2024-02-07"],
    ["Ноутбук Premium", "Москва", "220000", "Петров", "Оплачен", "2024-02-08"],
]

columns = ["Товар", "Город", "Сумма", "Менеджер", "Статус", "Дата"]

print("\n" + "="*80)
print("SheetGPT v7.8.6 - Double Conditions Test")
print("Testing queries with filter + sort + limit")
print("="*80 + "\n")

# Expected results (manually calculated)
# Оплаченные заказы: Монитор (180k), Сервер (250k), Мышка (1.2k), Принтер (85k), Ноутбук Premium (220k)
# Топ 3 оплаченных: Сервер (250k), Ноутбук Premium (220k), Монитор (180k)

test_cases = [
    {
        "query": "Топ 3 самых дорогих оплаченных заказа",
        "expected_products": ["Сервер", "Ноутбук Premium", "Монитор"],
        "must_not_include": ["Ноутбук"],  # Status = "Ожидает оплаты"
        "description": "Top 3 paid orders by price (filter + sort + limit)"
    },
    {
        "query": "5 самых дешевых оплаченных заказов",
        "expected_products": ["Мышка", "Принтер", "Монитор", "Ноутбук Premium", "Сервер"],
        "must_not_include": ["Клавиатура", "Стол"],
        "description": "Bottom 5 paid orders (filter + sort + limit)"
    },
    {
        "query": "Топ 2 заказа в Москве по сумме среди оплаченных",
        "expected_products": ["Ноутбук Premium", "Монитор"],
        "must_not_include": ["Ноутбук", "Клавиатура", "Стол"],
        "description": "Top 2 paid orders in Moscow (double filter + sort + limit)"
    }
]

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}: {test['query']}")
    print(f"{'='*80}")
    print(f"Description: {test['description']}")
    print(f"Expected products: {', '.join(test['expected_products'])}")
    print(f"Must NOT include: {', '.join(test['must_not_include'])}")
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
            print(f"  Summary: {result.get('summary', 'N/A')[:200]}")
            print()

            # Extract structured data or parse summary
            structured_data = result.get('structured_data')
            returned_products = []

            if structured_data:
                rows = structured_data.get('rows', [])
                # Assuming first column is product name
                returned_products = [row[0] if row else None for row in rows]
                print(f"[STRUCTURED DATA] {len(rows)} rows:")
                for row in rows[:5]:  # Show first 5
                    print(f"  - {row}")
            else:
                # Try to parse from summary
                summary = result.get('summary', '')
                print(f"[SUMMARY] {summary}")

            # Check for forbidden products
            forbidden_found = []
            for forbidden in test['must_not_include']:
                if structured_data:
                    if forbidden in returned_products:
                        forbidden_found.append(forbidden)
                else:
                    # v7.8.6 FIX: Use exact matching with "Товар: {name} |" pattern
                    # Prevents "Ноутбук" from matching "Ноутбук Premium"
                    # Pattern checks for "Товар: {name}" followed by " |" or end of string
                    import re
                    pattern = rf'Товар:\s*{re.escape(forbidden)}(?:\s*\||$)'
                    if re.search(pattern, summary):
                        forbidden_found.append(forbidden)

            if forbidden_found:
                print(f"\n[FAIL] BUG CONFIRMED: Found forbidden products: {', '.join(forbidden_found)}")
                print(f"       These products should NOT be in result (wrong status/city)")
                print(f"       This proves the filter is not working correctly!")
                failed += 1
            else:
                # Check if expected products are present
                expected_found = 0
                for expected in test['expected_products']:
                    if structured_data:
                        if expected in returned_products:
                            expected_found += 1
                    else:
                        if expected in summary:
                            expected_found += 1

                if expected_found >= len(test['expected_products']) * 0.6:
                    print(f"\n[PASS] Correct filtering: {expected_found}/{len(test['expected_products'])} expected products found")
                    print(f"       No forbidden products detected")
                    passed += 1
                else:
                    print(f"\n[PARTIAL] Only {expected_found}/{len(test['expected_products'])} expected products found")
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
print(f"DOUBLE CONDITIONS TEST SUMMARY")
print("="*80)
print(f"Total Tests: {len(test_cases)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success Rate: {(passed/len(test_cases)*100):.1f}%")
print()

if passed == len(test_cases):
    print("[SUCCESS] EXCELLENT! All double condition queries work correctly!")
    print("          v7.8.6 compound filtering is working as expected")
elif failed > 0:
    print("[CRITICAL BUG] Double condition queries failing!")
    print("               System not properly filtering before sorting/limiting")
    print("               Need to investigate which tier/function is handling these queries")
print("="*80 + "\n")
