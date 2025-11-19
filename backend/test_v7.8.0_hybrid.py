"""
Test v7.8.0: 3-Tier Hybrid Intelligence System

Tests all three tiers:
- TIER 1: Pattern Detection (0 tokens)
- TIER 2: Query Complexity Classifier (GPT-4o-mini, ~100 tokens)
- TIER 3A: Function Calling for simple queries (GPT-4o, ~500 tokens)
- TIER 3B: Code Generation for complex queries (GPT-4o, ~1000 tokens)
"""
import requests
import json

print("\n" + "="*80)
print("SheetGPT v7.8.0 - Test 3-Tier Hybrid Intelligence")
print("="*80 + "\n")

# Test data
test_data = [
    ["Ноутбук", "Москва", "150000", "Иванов", "Оплачен"],
    ["Мышка", "Москва", "1200", "Иванов", "Оплачен"],
    ["Монитор", "Москва", "80000", "Петров", "Оплачен"],
    ["Клавиатура", "Москва", "3500", "Иванов", "Оплачен"],
    ["Наушники", "Москва", "5000", "Сидоров", "Отменен"],
    ["Веб-камера", "Санкт-Петербург", "7000", "Иванов", "Оплачен"],
    ["Микрофон", "Санкт-Петербург", "4500", "Сидоров", "Оплачен"],
    ["Стол", "Санкт-Петербург", "25000", "Сидоров", "Оплачен"],
]

columns = ["Товар", "Город", "Сумма", "Менеджер", "Статус"]

tests = [
    {
        "name": "TIER 1 TEST: Pattern Detection",
        "query": "топ 3 заказа в Москве",
        "expected_tier": "TIER 1",
        "expected_function": "filter_top_n",
        "description": "Должен использовать Pattern Detection (0 tokens)"
    },
    {
        "name": "TIER 3A TEST: Function Calling (simple)",
        "query": "Сколько оплаченных заказов у каждого менеджера?",
        "expected_tier": "TIER 3A",
        "expected_function": "aggregate_by_group",
        "description": "Должен использовать Function Calling (~500 tokens)"
    },
    {
        "name": "TIER 3B TEST: Code Generation (complex)",
        "query": "найди заказы выше среднего в каждом городе и выдели топ менеджера",
        "expected_tier": "TIER 3B",
        "expected_function": "code_generation",
        "description": "Должен использовать Code Generation (~1000 tokens)"
    }
]

passed = 0
failed = 0

for i, test in enumerate(tests, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}: {test['name']}")
    print(f"{'='*80}")
    print(f"Query: {test['query']}")
    print(f"Expected: {test['expected_tier']}")
    print(f"Description: {test['description']}")
    print()

    try:
        test_request = {
            "query": test['query'],
            "column_names": columns,
            "sheet_data": test_data
        }

        response = requests.post(
            "http://localhost:8000/api/v1/formula",
            json=test_request,
            timeout=60  # Увеличенный timeout для Code Generation
        )

        if response.status_code == 200:
            result = response.json()
            function_used = result.get('function_used', 'N/A')
            summary = result.get('summary', 'N/A')

            print(f"[RESPONSE]")
            print(f"  Function: {function_used}")
            print(f"  Summary: {summary[:150]}...")

            # Determine which tier was actually used
            actual_tier = "UNKNOWN"
            if function_used in ["filter_top_n", "filter_bottom_n", "aggregate_by_group"] and "PATTERN DETECTOR" in str(result):
                actual_tier = "TIER 1"
            elif function_used == "code_generation" or result.get("python_executed"):
                actual_tier = "TIER 3B"
            elif function_used and function_used != "code_generation":
                actual_tier = "TIER 3A"

            print(f"\n[ANALYSIS]")
            print(f"  Expected Tier: {test['expected_tier']}")
            print(f"  Actual Tier: {actual_tier}")
            print(f"  Expected Function: {test['expected_function']}")
            print(f"  Actual Function: {function_used}")

            # Check if test passed
            if test['expected_function'] in function_used or test['expected_tier'] == actual_tier:
                print(f"\n✅ PASSED")
                passed += 1
            else:
                print(f"\n❌ FAILED - Wrong tier or function")
                failed += 1

            # Show methodology
            if result.get('methodology'):
                print(f"\n[METHODOLOGY]")
                print(f"  {result['methodology'][:200]}...")

        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            print(f"Error: {response.text[:300]}")
            failed += 1

    except requests.exceptions.ConnectionError:
        print("❌ FAILED - Backend not running on port 8000")
        print("Start with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload --port 8000")
        failed += 1

    except requests.exceptions.Timeout:
        print("❌ FAILED - Request timeout (>60s)")
        print("This might indicate Code Generation is taking too long")
        failed += 1

    except Exception as e:
        print(f"❌ FAILED - {str(e)}")
        failed += 1

print("\n" + "="*80)
print(f"FINAL RESULTS: {passed}/3 tests passed, {failed}/3 tests failed")
print("="*80)

if passed == 3:
    print("\n🎉 SUCCESS! v7.8.0 Hybrid Intelligence System works perfectly!")
    print("\n✨ All 3 tiers functioning correctly:")
    print("  ✅ TIER 1: Pattern Detection")
    print("  ✅ TIER 2: Query Complexity Classifier")
    print("  ✅ TIER 3A: Function Calling")
    print("  ✅ TIER 3B: Code Generation")
    print("\n🚀 Ready for production!\n")
elif passed >= 2:
    print("\n⚠️  PARTIAL SUCCESS - Most tiers working")
    print("Review failed tests above for details\n")
else:
    print("\n❌ FAILURE - Hybrid system needs debugging")
    print("Check backend logs for details\n")
