"""
Test v7.6.0: Smart UX - text answers for small results instead of tables
"""
import requests
import json

print("\n" + "="*80)
print("SheetGPT v7.6.0 - Test Smart UX")
print("="*80 + "\n")

# Test: "Какой самый дорогой заказ?"
# Expected: Text answer in chat, NO table creation
test_request = {
    "query": "Какой самый дорогой заказ?",
    "column_names": ["Товар", "Менеджер", "Сумма"],
    "sheet_data": [
        ["Ноутбук", "Петров", "150000"],
        ["Мышка", "Иванов", "1200"],
        ["Монитор", "Сидоров", "80000"],
    ]
}

print(f"Query: {test_request['query']}")
print(f"Expected: Text answer like 'Максимальное значение: Ноутбук | Петров | Сумма: 150 000'")
print(f"NOT expected: Table creation (structured_data)")
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
        print(f"Summary: {result.get('summary', 'N/A')}")
        print()

        # Check for structured_data (should NOT be present)
        if "structured_data" in result and result["structured_data"]:
            print("[FAIL] structured_data is present - table will be created!")
            print(f"Table: {result['structured_data'].get('table_title', 'N/A')}")
        else:
            print("[SUCCESS] No structured_data - answer shown in chat only!")

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
