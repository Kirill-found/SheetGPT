#!/usr/bin/env python3
"""
Тест для проверки задеплоенной v5.0.0 с AI Code Executor
"""

import requests
import json
import time

API_URL = "https://sheetgpt-production.up.railway.app"

def check_version():
    """Проверка версии API"""
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        data = response.json()

        print("=" * 60)
        print("API STATUS CHECK")
        print("=" * 60)
        print(f"Version: {data.get('version', 'N/A')}")
        print(f"Engine: {data.get('engine', 'N/A')}")
        print(f"Status: {data.get('status', 'N/A')}")

        features = data.get('features', {})
        if features:
            print("\nFeatures:")
            for feature, enabled in features.items():
                print(f"  - {feature}: {enabled}")

        return data.get('version') == '5.0.0'
    except Exception as e:
        print(f"Error checking version: {e}")
        return False

def test_code_executor():
    """Тест AI Code Executor с реальным запросом"""

    test_data = {
        "column_names": ["Колонка A", "Колонка B", "Колонка C", "Колонка D", "Колонка E"],
        "sheet_data": [
            ["Товар 1", "ООО Время", 10730.32, 1010, 107303.2],
            ["Товар 2", "ООО Сатурн", 8568.37, 1030, 257051.1],
            ["Товар 14", "ООО Время", 6328.28, 1007, 44297.96],  # 1
            ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44], # 2
            ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44], # 3
            ["Товар 14", "ООО Время", 6328.28, 1015, 63282.8],  # 4
            ["Товар 14", "ООО Время", 6328.28, 1025, 129076.72], # 5
            ["Товар 14", "ООО Время", 6328.28, 1022, 60771.44], # 6
            ["Товар 8", "ООО Радость", 25212.79, 1015, 378191.85]
        ],
        "history": []
    }

    queries = [
        {
            "query": "Топ 3 товара по продажам",
            "expected": ["Товар 14", "588", "Товар 8", "378", "Товар 2", "257"]
        },
        {
            "query": "У какого поставщика больше всего продаж",
            "expected": ["ООО Время", "695"]
        },
        {
            "query": "Посчитай общую сумму продаж",
            "expected": ["1480776"]
        }
    ]

    print("\n" + "=" * 60)
    print("TESTING AI CODE EXECUTOR")
    print("=" * 60)

    for test in queries:
        print(f"\nQuery: {test['query']}")
        print("-" * 50)

        payload = test_data.copy()
        payload["query"] = test["query"]

        try:
            start = time.time()
            response = requests.post(f"{API_URL}/api/v1/formula", json=payload, timeout=30)
            duration = time.time() - start

            if response.status_code == 200:
                result = response.json()

                print(f"✓ Response received in {duration:.2f}s")
                print(f"  Summary: {result.get('summary', 'N/A')[:100]}")
                print(f"  Methodology: {result.get('methodology', 'N/A')[:100]}")
                print(f"  Confidence: {result.get('confidence', 0):.2f}")
                print(f"  Response type: {result.get('response_type', 'N/A')}")

                # Проверяем ожидаемые значения
                summary = result.get('summary', '').lower()
                all_found = True
                for exp in test['expected']:
                    if exp.lower() in summary:
                        print(f"  ✓ Found: {exp}")
                    else:
                        print(f"  ✗ Missing: {exp}")
                        all_found = False

                if all_found:
                    print(f"  [SUCCESS] All expected values found")
                else:
                    print(f"  [PARTIAL] Some values missing")

            else:
                print(f"✗ Error: HTTP {response.status_code}")
                print(f"  Response: {response.text[:200]}")

        except Exception as e:
            print(f"✗ Exception: {str(e)}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

def main():
    print("SheetGPT v5.0.0 AI Code Executor Test")
    print("=" * 60)

    # Проверяем версию
    if check_version():
        print("\n✓ Version 5.0.0 is deployed!")

        # Ждем немного чтобы сервис прогрелся
        print("\nWaiting 5 seconds for service warmup...")
        time.sleep(5)

        # Тестируем функциональность
        test_code_executor()
    else:
        print("\n✗ Version 5.0.0 not deployed yet")
        print("  The deployment may still be in progress")
        print("  Try again in 1-2 minutes")

if __name__ == "__main__":
    main()