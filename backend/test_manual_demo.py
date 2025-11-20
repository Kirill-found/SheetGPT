"""
Manual Demo Test - v7.8.0 All 3 Tiers
Shows real-world examples of each tier in action
"""
import requests
import json

API_URL = "http://localhost:8000/api/v1/formula"

# Test data
test_data = [
    ["Ноутбук", "Москва", "150000", "Иванов", "Оплачен"],
    ["Мышка", "Москва", "1200", "Иванов", "Оплачен"],
    ["Монитор", "Москва", "80000", "Петров", "Оплачен"],
    ["Клавиатура", "Москва", "3500", "Иванов", "Оплачен"],
    ["Наушники", "Санкт-Петербург", "5000", "Сидоров", "Отменен"],
    ["Веб-камера", "Санкт-Петербург", "7000", "Иванов", "Оплачен"],
    ["Микрофон", "Санкт-Петербург", "4500", "Сидоров", "Оплачен"],
    ["Стол", "Санкт-Петербург", "25000", "Сидоров", "Оплачен"],
]

columns = ["Товар", "Город", "Сумма", "Менеджер", "Статус"]

print("\n" + "="*80)
print("SheetGPT v7.8.0 - Manual Demo Test")
print("Демонстрация работы всех 3 тиров Hybrid Intelligence")
print("="*80 + "\n")

tests = [
    {
        "tier": "TIER 1 - Pattern Detection (0 tokens, <100ms)",
        "query": "Сколько оплаченных заказов у каждого менеджера?",
        "description": "Русский query с pattern 'у каждого' → Pattern Detection"
    },
    {
        "tier": "TIER 3B - Code Generation (~1000 tokens, 2-4s)",
        "query": "top 3 most expensive orders in Moscow",
        "description": "Английский complex query → Code Generation"
    },
    {
        "tier": "TIER 3B - Code Generation",
        "query": "how many paid orders does each manager have?",
        "description": "Английский query с группировкой → Code Generation"
    }
]

for i, test in enumerate(tests, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}: {test['tier']}")
    print(f"{'='*80}")
    print(f"Query: {test['query']}")
    print(f"Description: {test['description']}")
    print()

    try:
        response = requests.post(
            API_URL,
            json={
                "query": test['query'],
                "column_names": columns,
                "sheet_data": test_data
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            print(f"[RESPONSE]")
            print(f"  Function: {result.get('function_used', 'N/A')}")
            print(f"  Summary:")

            # Print summary with proper formatting
            summary = result.get('summary', 'N/A')
            for line in summary.split('\n')[:5]:  # First 5 lines
                print(f"    {line}")

            if result.get('methodology'):
                print(f"\n[METHODOLOGY]")
                methodology = result['methodology'][:150]
                print(f"  {methodology}...")

            if result.get('code_generated'):
                print(f"\n[CODE GENERATED]")
                code = result['code_generated'][:200]
                print(f"  {code}...")

            print(f"\n✅ SUCCESS")

        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            print(f"Error: {response.text[:200]}")

    except requests.exceptions.ConnectionError:
        print("❌ FAILED - Backend not running on port 8000")
        print("Start with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload --port 8000")
        break

    except Exception as e:
        print(f"❌ FAILED - {str(e)}")

print("\n" + "="*80)
print("Demo Test Complete")
print("="*80 + "\n")
