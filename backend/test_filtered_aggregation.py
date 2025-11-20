"""
Filtered Aggregation Test - v7.8.4
Tests conditional aggregation (e.g., "средний чек в Москве")
"""
import requests
import json

API_URL = "http://localhost:8000/api/v1/formula"

# Test data with multiple cities
test_data = [
    ["Ноутбук", "Москва", "150000", "Иванов", "Оплачен"],
    ["Мышка", "Москва", "1200", "Иванов", "Оплачен"],
    ["Монитор", "Москва", "80000", "Петров", "Оплачен"],
    ["Клавиатура", "Санкт-Петербург", "3500", "Иванов", "Оплачен"],
    ["Наушники", "Москва", "5000", "Сидоров", "Отменен"],
    ["Веб-камера", "Санкт-Петербург", "7000", "Иванов", "Оплачен"],
    ["Микрофон", "Санкт-Петербург", "4500", "Сидоров", "Оплачен"],
    ["Стол", "Москва", "25000", "Сидоров", "Оплачен"],
    ["Стул", "Санкт-Петербург", "8000", "Петров", "Оплачен"],
    ["Лампа", "Москва", "3500", "Иванов", "Отменен"],
]

columns = ["Товар", "Город", "Сумма", "Менеджер", "Статус"]

# Expected results (calculated manually)
# Москва orders: 150000, 1200, 80000, 5000, 25000, 3500 (6 orders)
# Москва оплаченные: 150000, 1200, 80000, 25000 (4 orders)
# СПб orders: 3500, 7000, 4500, 8000 (4 orders)
# СПб оплаченные: 3500, 7000, 4500, 8000 (4 orders)

print("\n" + "="*80)
print("SheetGPT v7.8.4 - Filtered Aggregation Test")
print("Testing conditional aggregation with city filter")
print("="*80 + "\n")

test_cases = [
    {
        "query": "Средний чек в Москве",
        "expected_range": (43000, 45000),  # Average of all Moscow: (150000+1200+80000+5000+25000+3500)/6 = 44116.67
        "description": "Average check for all Moscow orders (paid + cancelled)"
    },
    {
        "query": "Сумма продаж в Санкт-Петербурге",
        "expected_range": (22000, 24000),  # Sum of all SPb: 3500+7000+4500+8000 = 23000
        "description": "Sum of all St. Petersburg orders"
    },
    {
        "query": "Средняя сумма оплаченных заказов в Москве",
        "expected_range": (63000, 65000),  # Average paid Moscow: (150000+1200+80000+25000)/4 = 64050
        "description": "Average of paid orders in Moscow"
    },
    {
        "query": "Сколько оплаченных заказов в Санкт-Петербурге",
        "expected_value": 4,
        "description": "Count of paid orders in St. Petersburg"
    }
]

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}: {test['query']}")
    print(f"{'='*80}")
    print(f"Description: {test['description']}")
    if 'expected_range' in test:
        print(f"Expected range: {test['expected_range'][0]:,} - {test['expected_range'][1]:,}")
    elif 'expected_value' in test:
        print(f"Expected value: {test['expected_value']}")
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
            print(f"  Summary: {result.get('summary', 'N/A')[:100]}")
            print(f"  Function: {result.get('function_used', 'N/A')}")

            # Extract numeric result
            summary = result.get('summary', '')

            # Try to parse number from summary
            import re
            number_match = re.search(r'(\d[\d\s,\.]*\d|\d)', summary.replace(' ', ''))

            if number_match:
                number_str = number_match.group(0).replace(',', '').replace('.', '')
                # Handle floats
                if '.' in summary:
                    actual_value = float(number_str) / 100  # Adjust for decimal
                else:
                    actual_value = float(number_str)

                print(f"  Actual value: {actual_value:,.2f}")

                # Check if in range
                if 'expected_range' in test:
                    if test['expected_range'][0] <= actual_value <= test['expected_range'][1]:
                        print(f"\n[PASSED] Value within expected range")
                        passed += 1
                    else:
                        print(f"\n[FAILED] Value {actual_value:,.2f} outside expected range {test['expected_range']}")
                        failed += 1
                elif 'expected_value' in test:
                    if abs(actual_value - test['expected_value']) < 1:
                        print(f"\n[PASSED] Value matches expected")
                        passed += 1
                    else:
                        print(f"\n[FAILED] Expected {test['expected_value']}, got {actual_value}")
                        failed += 1
            else:
                print(f"\n[FAILED] Could not parse numeric result from: {summary}")
                failed += 1

        else:
            print(f"[FAILED] HTTP {response.status_code}")
            print(f"Error: {response.text[:200]}")
            failed += 1

    except requests.exceptions.ConnectionError:
        print("[FAILED] Backend not running on port 8000")
        print("Start with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload --port 8000")
        break

    except Exception as e:
        print(f"[FAILED] {str(e)}")
        failed += 1

print("\n" + "="*80)
print(f"FILTERED AGGREGATION TEST SUMMARY")
print("="*80)
print(f"Total Tests: {len(test_cases)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success Rate: {(passed/len(test_cases)*100):.1f}%")
print()

if passed == len(test_cases):
    print("[SUCCESS] EXCELLENT! All filtered aggregation queries work correctly!")
    print("          v7.8.4 conditional filtering is working as expected")
elif passed >= len(test_cases) * 0.75:
    print("[SUCCESS] GOOD! Most filtered aggregations working")
    print(f"          {failed} queries need investigation")
else:
    print("[WARNING] NEEDS WORK - Several filtered aggregations failed")
print("="*80 + "\n")
