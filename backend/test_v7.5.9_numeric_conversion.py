"""
Тест v7.5.9: Автоматическая конвертация числовых колонок
"""
import requests
import json
import time

print("\n" + "="*80)
print("SheetGPT v7.5.9 - Тест автоматической конвертации чисел")
print("="*80 + "\n")

# Test 1: calculate_sum (раньше конкатенировал строки)
test1 = {
    "query": "Какая общая сумма продаж?",
    "column_names": ["Менеджер", "Сумма продаж", "Дата"],
    "sheet_data": [
        ["Иван", "150000", "2024-01-01"],
        ["Мария", "80000", "2024-01-02"],
        ["Петр", "45000", "2024-01-03"],
    ]
}

# Test 2: filter_top_n (раньше падал с dtype error)
test2 = {
    "query": "Какой самый дорогой заказ?",
    "column_names": ["Товар", "Менеджер", "Сумма"],
    "sheet_data": [
        ["Ноутбук", "Петров", "150000"],
        ["Мышка", "Иванов", "1200"],
        ["Монитор", "Сидоров", "80000"],
    ]
}

tests = [
    ("TEST 1: calculate_sum", test1, "275,000"),
    ("TEST 2: filter_top_n", test2, "150,000"),
]

passed = 0
failed = 0

for test_name, test_request, expected_substring in tests:
    print(f"\n{test_name}")
    print(f"   Query: {test_request['query']}")
    print(f"   Expected: soderzhit '{expected_substring}'")

    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:8000/api/v1/formula",
            json=test_request,
            timeout=30
        )
        duration_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            result = response.json()
            summary = result.get('summary', '')

            # Проверяем, что результат содержит ожидаемое число
            if expected_substring.replace(',', '') in summary.replace(',', '').replace(' ', ''):
                print(f"   [OK] PASSED ({duration_ms:.0f}ms)")
                print(f"   Summary: {summary}")
                passed += 1
            else:
                print(f"   [FAIL] FAILED - Unexpected result")
                print(f"   Summary: {summary}")
                failed += 1
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
    print("\n[SUCCESS] v7.5.9 WORKS! Auto conversion fixed all numeric functions.\n")
else:
    print("\n[WARNING] Problems found. Check backend logs.\n")
