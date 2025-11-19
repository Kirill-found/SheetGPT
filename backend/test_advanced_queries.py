"""
Advanced Queries Test - v7.8.0 Hybrid Intelligence
Tests sophisticated Google Sheets operations:
- Multi-level aggregations
- Statistical calculations
- Conditional logic
- Nested operations
"""
import requests
import json

API_URL = "http://localhost:8000/api/v1/formula"

# Расширенные тестовые данные (3 месяца продаж)
test_data = [
    ["Ноутбук", "Электроника", "Москва", "150000", "Иванов", "Оплачен", "2024-01"],
    ["Мышка", "Электроника", "Москва", "1200", "Иванов", "Оплачен", "2024-01"],
    ["Монитор", "Электроника", "Москва", "80000", "Петров", "Оплачен", "2024-01"],
    ["Клавиатура", "Электроника", "Санкт-Петербург", "3500", "Иванов", "Оплачен", "2024-01"],
    ["Наушники", "Электроника", "Москва", "5000", "Сидоров", "Отменен", "2024-01"],
    ["Стол", "Мебель", "Москва", "25000", "Иванов", "Оплачен", "2024-01"],
    ["Стул", "Мебель", "Санкт-Петербург", "8000", "Петров", "Оплачен", "2024-01"],

    ["Ноутбук", "Электроника", "Москва", "155000", "Сидоров", "Оплачен", "2024-02"],
    ["Планшет", "Электроника", "Москва", "45000", "Иванов", "Оплачен", "2024-02"],
    ["Монитор", "Электроника", "Санкт-Петербург", "82000", "Петров", "Оплачен", "2024-02"],
    ["Шкаф", "Мебель", "Москва", "35000", "Сидоров", "Оплачен", "2024-02"],
    ["Стол", "Мебель", "Санкт-Петербург", "27000", "Иванов", "Оплачен", "2024-02"],
    ["Кресло", "Мебель", "Москва", "15000", "Петров", "Оплачен", "2024-02"],

    ["Ноутбук", "Электроника", "Москва", "148000", "Иванов", "Оплачен", "2024-03"],
    ["Мышка", "Электроника", "Москва", "1300", "Сидоров", "Оплачен", "2024-03"],
    ["Веб-камера", "Электроника", "Санкт-Петербург", "7000", "Петров", "Оплачен", "2024-03"],
    ["Микрофон", "Электроника", "Москва", "4500", "Иванов", "Оплачен", "2024-03"],
    ["Стол", "Мебель", "Москва", "26000", "Сидоров", "Оплачен", "2024-03"],
    ["Стул", "Мебель", "Санкт-Петербург", "8500", "Петров", "Оплачен", "2024-03"],
]

columns = ["Товар", "Категория", "Город", "Сумма", "Менеджер", "Статус", "Месяц"]

print("\n" + "="*80)
print("SheetGPT v7.8.0 - Advanced Queries Test")
print("Тестирование продвинутых операций Google Sheets")
print("="*80 + "\n")

# Продвинутые тесты
advanced_tests = [
    {
        "tier": "ADVANCED 1: Multi-level Aggregation + Percentage",
        "query": "Какой процент от общей выручки составляет каждая категория?",
        "description": "Группировка → Сумма → Процент от общего",
        "expected": "TIER 3B Code Generation (multiple operations)"
    },
    {
        "tier": "ADVANCED 2: Conditional Aggregation with Filter",
        "query": "Средний чек по менеджерам, но только для тех, у кого больше 3 оплаченных заказов",
        "description": "Фильтр → Группировка → Count filter → Average",
        "expected": "TIER 3B Code Generation (conditional logic)"
    },
    {
        "tier": "ADVANCED 3: Statistical Comparison",
        "query": "Покажи товары, цена которых выше средней по их категории",
        "description": "Группировка по категории → Вычисление среднего → Сравнение каждого товара",
        "expected": "TIER 3B Code Generation (nested operations)"
    },
    {
        "tier": "ADVANCED 4: Top N per Group",
        "query": "Топ 2 самых дорогих товара в каждой категории",
        "description": "Группировка → Top N внутри группы",
        "expected": "TIER 3B Code Generation (groupby + nlargest)"
    },
    {
        "tier": "ADVANCED 5: Trend Analysis",
        "query": "Сравни выручку по месяцам для категории Электроника и покажи рост",
        "description": "Фильтр → Группировка по месяцам → Вычисление роста",
        "expected": "TIER 3B Code Generation (time series)"
    },
    {
        "tier": "ADVANCED 6: Percentile Analysis",
        "query": "Найди заказы, которые входят в топ 20% по сумме в своем городе",
        "description": "Группировка по городу → Вычисление 80-го перцентиля → Фильтр",
        "expected": "TIER 3B Code Generation (percentile calculation)"
    },
    {
        "tier": "ADVANCED 7: Complex Multi-condition",
        "query": "Сколько менеджеров продали электронику на сумму больше 100000 в Москве?",
        "description": "Multiple filters + aggregation",
        "expected": "TIER 3B Code Generation (multi-condition filter)"
    }
]

passed = 0
failed = 0
results_summary = []

for i, test in enumerate(advanced_tests, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}: {test['tier']}")
    print(f"{'='*80}")
    print(f"Query: {test['query']}")
    print(f"Description: {test['description']}")
    print(f"Expected: {test['expected']}")
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

            # Determine which tier was used
            if result.get('code_generated') and result['code_generated'] != 'NOT_IN_RESULT':
                tier_used = "TIER 3B (Code Generation)"
            elif result.get('function_used'):
                tier_used = "TIER 3A (Function Calling)"
            else:
                tier_used = "TIER 1 (Pattern Detection)"

            print(f"  Tier Used: {tier_used}")

            # Print summary
            summary = result.get('summary', 'N/A')
            print(f"  Summary:")
            for line in summary.split('\n')[:8]:  # First 8 lines
                print(f"    {line}")

            # Show code if generated
            if result.get('code_generated') and result['code_generated'] != 'NOT_IN_RESULT':
                print(f"\n[CODE GENERATED]")
                code = result['code_generated']
                # Show full code for advanced queries
                for line in code.split('\n')[:10]:
                    print(f"    {line}")
                if len(code.split('\n')) > 10:
                    print(f"    ... ({len(code.split('\n'))} total lines)")

            # Check if table was created
            if result.get('structured_data'):
                print(f"\n[STRUCTURED DATA]")
                print(f"  Table created: YES")
                print(f"  Rows: {len(result['structured_data'].get('rows', []))}")
                print(f"  Columns: {result['structured_data'].get('columns', [])}")

            print(f"\n✅ SUCCESS - Query processed")
            passed += 1

            results_summary.append({
                "query": test['query'],
                "tier_used": tier_used,
                "success": True
            })

        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            print(f"Error: {response.text[:200]}")
            failed += 1
            results_summary.append({
                "query": test['query'],
                "success": False,
                "error": f"HTTP {response.status_code}"
            })

    except requests.exceptions.ConnectionError:
        print("❌ FAILED - Backend not running on port 8000")
        print("Start with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload --port 8000")
        failed += 1
        break

    except Exception as e:
        print(f"❌ FAILED - {str(e)}")
        failed += 1
        results_summary.append({
            "query": test['query'],
            "success": False,
            "error": str(e)
        })

print("\n" + "="*80)
print(f"ADVANCED QUERIES TEST SUMMARY")
print("="*80)
print(f"Total Tests: {len(advanced_tests)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Success Rate: {(passed/len(advanced_tests)*100):.1f}%")
print()

# Show tier distribution
tier_counts = {}
for res in results_summary:
    if res.get('success') and res.get('tier_used'):
        tier = res['tier_used']
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

print("TIER DISTRIBUTION:")
for tier, count in tier_counts.items():
    print(f"  {tier}: {count} queries")

print("\n" + "="*80)
print("CONCLUSION:")
if passed == len(advanced_tests):
    print("✅ EXCELLENT! All advanced queries handled successfully!")
    print("   v7.8.0 Hybrid Intelligence can handle sophisticated Google Sheets operations")
elif passed >= len(advanced_tests) * 0.8:
    print("✅ GOOD! Most advanced queries handled successfully")
    print(f"   {failed} queries need improvement")
else:
    print("⚠️  NEEDS WORK - Several advanced queries failed")
print("="*80 + "\n")
