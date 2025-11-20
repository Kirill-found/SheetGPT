"""
Test v7.6.5: "У КАЖДОГО" = GROUP BY detection
"""
import requests
import json

print("\n" + "="*80)
print("SheetGPT v7.6.5 - Test 'У КАЖДОГО' GROUP BY Detection")
print("="*80 + "\n")

# Test: "Сколько оплаченных заказов у каждого менеджера?"
# Expected: aggregate_by_group, NOT calculate_sum or filter_rows
test_request = {
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

print(f"Query: {test_request['query']}")
print(f"Expected function: aggregate_by_group(group_by='Менеджер', agg_func='count')")
print(f"Expected result: Иванов: 4, Петров: 1, Сидоров: 2 (только оплаченные)")
print()

try:
    response = requests.post(
        "http://localhost:8000/api/v1/formula",
        json=test_request,
        timeout=30
    )

    if response.status_code == 200:
        result = response.json()

        print("[RESULT]")
        print(f"Function used: {result.get('function_used', 'N/A')}")
        print(f"Summary: {result.get('summary', 'N/A')}")
        print()

        # Check if correct function was called
        if result.get('function_used') == 'aggregate_by_group':
            print("[SUCCESS] ✅ GPT-4o вызвал aggregate_by_group!")
            print("[SUCCESS] v7.6.5 'У КАЖДОГО' detection WORKS!")
        elif result.get('function_used') == 'calculate_sum':
            print("[FAIL] ❌ GPT-4o вызвал calculate_sum (ожидалось aggregate_by_group)")
            print("[FAIL] 'У КАЖДОГО' detection NOT working")
        elif result.get('function_used') == 'filter_rows':
            print("[FAIL] ❌ GPT-4o вызвал filter_rows (ожидалось aggregate_by_group)")
            print("[FAIL] 'У КАЖДОГО' detection NOT working")
        else:
            print(f"[FAIL] ❌ Unexpected function: {result.get('function_used')}")

        print()
        print("[METHODOLOGY]")
        print(result.get('methodology', 'N/A'))

    else:
        print(f"[FAIL] HTTP {response.status_code}")
        print(response.text[:500])

except requests.exceptions.ConnectionError:
    print("[FAIL] Backend not running on port 8000")
    print("Start with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload --port 8000")

except Exception as e:
    print(f"[FAIL] {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
