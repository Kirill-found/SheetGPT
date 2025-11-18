"""
SheetGPT v7.4.0 - 10 Functions Test Runner
Тестирование 4 базовых + 6 новых функций
"""

import requests
import json
import time
from datetime import datetime

# API endpoint
API_URL = "http://localhost:8000/api/v1/formula"

def load_test_data():
    """Загрузка тестовых данных"""
    with open("test_10_functions.json", "r", encoding="utf-8") as f:
        return json.load(f)

def run_test(test_case, test_data):
    """Запуск одного теста"""
    print(f"\n{'='*80}")
    print(f"TEST #{test_case['id']}: {test_case['category']}")
    print(f"Function: {test_case['function']}")
    print(f"Query: '{test_case['query']}'")
    print(f"{'='*80}")

    # Подготовка запроса
    payload = {
        "query": test_case["query"],
        "column_names": test_data["column_names"],
        "sheet_data": test_data["sheet_data"],
        "history": []
    }

    try:
        # Отправка запроса
        start_time = time.time()
        response = requests.post(API_URL, json=payload, timeout=30)
        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            # Проверка результата
            function_used = result.get("function_used")
            response_type = result.get("response_type")
            summary = result.get("summary", "")

            print(f"\n✅ SUCCESS ({elapsed:.2f}s)")
            print(f"Function used: {function_used}")
            print(f"Response type: {response_type}")
            print(f"Summary: {summary[:200]}...")

            # Детальная проверка
            success = True
            if function_used != test_case["expected_function"]:
                print(f"⚠️  WARNING: Expected {test_case['expected_function']}, got {function_used}")
                success = False

            if response_type == "error":
                print(f"❌ ERROR: {result.get('warnings', [])}")
                success = False

            return {
                "test_id": test_case["id"],
                "category": test_case["category"],
                "success": success,
                "function_used": function_used,
                "response_type": response_type,
                "elapsed": elapsed,
                "summary": summary
            }
        else:
            print(f"❌ HTTP ERROR: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return {
                "test_id": test_case["id"],
                "category": test_case["category"],
                "success": False,
                "error": f"HTTP {response.status_code}",
                "elapsed": elapsed
            }

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return {
            "test_id": test_case["id"],
            "category": test_case["category"],
            "success": False,
            "error": str(e),
            "elapsed": 0
        }

def main():
    """Запуск всех тестов"""
    print("\n" + "="*80)
    print("SheetGPT v7.4.0 - 10 Functions Test Suite")
    print(f"Started at: {datetime.now()}")
    print("="*80)

    # Загрузка тестов
    data = load_test_data()
    test_data = data["test_data"]
    tests = data["tests"]

    print(f"\nTotal tests: {len(tests)}")
    print(f"Test data: {len(test_data['sheet_data'])} rows × {len(test_data['column_names'])} columns")

    # Запуск тестов
    results = []
    for test_case in tests:
        result = run_test(test_case, test_data)
        results.append(result)
        time.sleep(0.5)  # Пауза между запросами

    # Итоги
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)

    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    accuracy = (successful / len(results)) * 100

    print(f"\n✅ Successful: {successful}/{len(results)} ({accuracy:.1f}%)")
    print(f"❌ Failed: {failed}/{len(results)}")

    # Детали по категориям
    print("\nBy category:")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"success": 0, "total": 0}
        categories[cat]["total"] += 1
        if r["success"]:
            categories[cat]["success"] += 1

    for cat, stats in categories.items():
        acc = (stats["success"] / stats["total"]) * 100
        status = "✅" if stats["success"] == stats["total"] else "⚠️"
        print(f"  {status} {cat}: {stats['success']}/{stats['total']} ({acc:.0f}%)")

    # Средняя скорость
    avg_time = sum(r.get("elapsed", 0) for r in results) / len(results)
    print(f"\nAverage response time: {avg_time:.2f}s")

    # Сохранение результатов
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results),
            "successful": successful,
            "failed": failed,
            "accuracy": accuracy,
            "avg_response_time": avg_time,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("\n" + "="*80)
    print(f"TARGET: 95%+ accuracy")
    print(f"ACTUAL: {accuracy:.1f}%")
    if accuracy >= 95:
        print("🎉 SUCCESS! Target achieved!")
    else:
        print(f"⚠️  Need improvement: {95 - accuracy:.1f}% to go")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
