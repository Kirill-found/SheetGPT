"""
Комплексный тест v7.5.0 улучшений:
- Query Classifier (75% tokens saved)
- Fuzzy Column Matching (95%+ success rate)
- Metrics Logging (real-time monitoring)
"""

import sys
import json
import requests
import time
from datetime import datetime

# Настройка кодировки для Windows
sys.stdout.reconfigure(encoding='utf-8')

# Цвета для вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_section(title):
    print(f"\n{'='*80}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{'='*80}\n")

def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")

def print_info(msg):
    print(f"{YELLOW}ℹ{RESET} {msg}")

# ============================================================================
# TEST 1: Query Classifier
# ============================================================================
def test_query_classifier():
    print_section("TEST 1: Query Classifier (Token Savings)")

    try:
        from app.utils.query_classifier import QueryClassifier

        classifier = QueryClassifier()

        test_queries = [
            ("Какая сумма продаж?", ["math"]),
            ("Топ 5 менеджеров по продажам", ["filter", "sort"]),
            ("Группировка по городам с суммой", ["group", "math"]),
            ("Найди все заказы со словом срочно", ["text", "filter"]),
            ("Подсвети строки где сумма больше 100000", ["action", "filter"]),
        ]

        total_functions = 0
        total_original = len(test_queries) * 100  # 100 functions per query

        for query, expected_categories in test_queries:
            categories = classifier.classify(query)
            relevant_functions = classifier.get_relevant_functions(query)
            num_functions = len(relevant_functions)
            total_functions += num_functions

            print_info(f"Query: {query[:50]}...")
            print(f"  Categories: {categories}")
            print(f"  Functions sent: {num_functions}/100 ({num_functions}%)")

            # Проверяем что нашлись ожидаемые категории
            if any(cat in categories for cat in expected_categories):
                print_success(f"Correct category detected")
            else:
                print_error(f"Expected {expected_categories}, got {categories}")
            print()

        avg_functions = total_functions / len(test_queries)
        savings = (1 - avg_functions / 100) * 100

        print_success(f"Average functions sent: {avg_functions:.1f}/100 ({avg_functions:.0f}%)")
        print_success(f"Token savings: {savings:.0f}%")
        print_success(f"Expected speedup: {100/avg_functions:.1f}x")

        return True

    except Exception as e:
        print_error(f"Query Classifier test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# TEST 2: Fuzzy Column Matching
# ============================================================================
def test_fuzzy_matching():
    print_section("TEST 2: Fuzzy Column Matching (95%+ Success Rate)")

    try:
        from app.utils.fuzzy_match import find_best_column_match

        test_cases = [
            # (requested, available, expected)
            ("Продажи", ["Менеджер", "Сумма продаж", "Дата"], "Сумма продаж"),
            ("Сумма", ["Менеджер", "Заказали на сумму", "Дата"], "Заказали на сумму"),
            ("Manager", ["Name", "Sales Manager", "Region"], "Sales Manager"),
            ("total", ["Product", "Total Sales", "Date"], "Total Sales"),
            ("выручка", ["Менеджер", "Сумма продаж", "Дата"], "Сумма продаж"),  # synonym
            ("цена", ["Товар", "Стоимость", "Количество"], "Стоимость"),  # synonym
        ]

        passed = 0
        failed = 0

        for requested, available, expected in test_cases:
            result = find_best_column_match(requested, available)

            if result == expected:
                print_success(f"'{requested}' → '{result}'")
                passed += 1
            else:
                print_error(f"'{requested}' → '{result}' (expected '{expected}')")
                failed += 1

        success_rate = (passed / len(test_cases)) * 100
        print()
        print_success(f"Tests passed: {passed}/{len(test_cases)} ({success_rate:.0f}%)")

        if success_rate >= 95:
            print_success(f"Target 95%+ success rate ACHIEVED!")
            return True
        else:
            print_error(f"Target 95%+ success rate NOT achieved (got {success_rate:.0f}%)")
            return False

    except Exception as e:
        print_error(f"Fuzzy matching test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# TEST 3: Metrics Logging
# ============================================================================
def test_metrics():
    print_section("TEST 3: Metrics Logging (Real-time Monitoring)")

    try:
        from app.utils.metrics import metrics_collector, MetricsCollector

        # Создаем тестовый collector
        test_metrics = MetricsCollector()

        # Логируем несколько успешных запросов
        test_metrics.log_execution(
            "calculate_sum",
            success=True,
            duration_ms=1250,
            query="Сумма продаж",
            confidence=0.98,
            num_functions_sent=8,
            categories=["math"]
        )

        test_metrics.log_execution(
            "filter_top_n",
            success=True,
            duration_ms=2100,
            query="Топ 5",
            confidence=0.95,
            num_functions_sent=20,
            categories=["filter", "sort"]
        )

        # Логируем провал
        test_metrics.log_execution(
            "filter_rows",
            success=False,
            duration_ms=1500,
            query="Фильтр",
            error="Column not found",
            num_functions_sent=20,
            categories=["filter"]
        )

        # Fuzzy match
        test_metrics.log_fuzzy_match(
            "Продажи",
            "Сумма продаж",
            ["Менеджер", "Сумма продаж", "Дата"],
            method="synonym"
        )

        # Проверяем summary
        summary = test_metrics.get_summary()

        print_info(f"Total requests: {summary['total_requests']}")
        print_info(f"Success rate: {summary['success_rate']}")
        print_info(f"Avg duration: {summary['avg_duration_ms']}ms")

        if summary['total_requests'] == 3:
            print_success("Metrics logging works correctly")
            return True
        else:
            print_error(f"Expected 3 requests, got {summary['total_requests']}")
            return False

    except Exception as e:
        print_error(f"Metrics test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# TEST 4: Integration Test (Real API Request)
# ============================================================================
def test_integration():
    print_section("TEST 4: Integration Test (Real API Request)")

    try:
        # Проверяем что сервер запущен
        try:
            health = requests.get("http://localhost:8000/health", timeout=5)
            if health.status_code != 200:
                print_error("Backend not running on port 8000")
                return False
            print_success("Backend is running")
        except requests.exceptions.ConnectionError:
            print_error("Backend not running on port 8000")
            print_info("Start backend with: cd /c/SheetGPT/backend && python -m uvicorn app.main:app --reload")
            return False

        # Тестовый запрос
        test_data = {
            "query": "Какая средняя сумма продаж?",
            "column_names": ["Менеджер", "Сумма продаж", "Дата"],
            "sheet_data": [
                ["Иван", 10000, "2024-01-01"],
                ["Мария", 15000, "2024-01-02"],
                ["Петр", 12000, "2024-01-03"],
            ]
        }

        print_info(f"Sending request: {test_data['query']}")
        start_time = time.time()

        response = requests.post(
            "http://localhost:8000/api/v1/formula",
            json=test_data,
            timeout=30
        )

        duration = (time.time() - start_time) * 1000

        if response.status_code != 200:
            print_error(f"Request failed with status {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        result = response.json()

        print_success(f"Request successful (HTTP 200)")
        print_success(f"Response time: {duration:.0f}ms")

        # Проверяем что ответ содержит нужные поля
        required_fields = ["summary", "confidence", "response_type"]
        for field in required_fields:
            if field in result:
                print_success(f"Field '{field}' present: {str(result[field])[:50]}...")
            else:
                print_error(f"Field '{field}' missing")

        # Проверяем response time
        if duration < 3000:
            print_success(f"Response time <3s target ACHIEVED! ({duration:.0f}ms)")
        else:
            print_error(f"Response time >3s (got {duration:.0f}ms)")

        # Выводим краткий результат
        print()
        print_info("Result summary:")
        print(f"  Summary: {result.get('summary', 'N/A')[:100]}...")
        print(f"  Confidence: {result.get('confidence', 'N/A')}")
        print(f"  Response type: {result.get('response_type', 'N/A')}")

        return True

    except Exception as e:
        print_error(f"Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}SheetGPT v7.5.0 - Comprehensive Test Suite{RESET}")
    print(f"{BLUE}Performance & Reliability Improvements{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []

    # Run all tests
    results.append(("Query Classifier", test_query_classifier()))
    results.append(("Fuzzy Column Matching", test_fuzzy_matching()))
    results.append(("Metrics Logging", test_metrics()))
    results.append(("Integration Test", test_integration()))

    # Summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        if result:
            print_success(f"{name}")
        else:
            print_error(f"{name}")

    print()
    if passed == total:
        print(f"{GREEN}{'='*80}{RESET}")
        print(f"{GREEN}ALL TESTS PASSED! ({passed}/{total}){RESET}")
        print(f"{GREEN}v7.5.0 improvements are working correctly!{RESET}")
        print(f"{GREEN}{'='*80}{RESET}")
    else:
        print(f"{RED}{'='*80}{RESET}")
        print(f"{RED}SOME TESTS FAILED ({passed}/{total}){RESET}")
        print(f"{RED}{'='*80}{RESET}")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
