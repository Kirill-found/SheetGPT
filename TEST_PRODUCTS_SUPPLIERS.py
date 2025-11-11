#!/usr/bin/env python3
"""
Test for product/supplier detection in SheetGPT API
"""

import requests
import json
import time

# Test data
test_data = {
    "column_names": ["Колонка A", "Колонка B", "Колонка C", "Колонка D", "Колонка E"],
    "sheet_data": [
        ["Товар 1", "ООО Время", 10730.32, 1010, 107303.2],
        ["Товар 2", "ООО Сатурн", 8568.37, 1030, 257051.1],
        ["Товар 3", "ООО Луна", 7318.09, 1020, 146361.8],
        ["Товар 14", "ООО Время", 6328.28, 1007, 44297.96],
        ["Товар 5", "ООО Персектив", 1196.9, 1017, 20347.3],
        ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44],
        ["Товар 7", "ООО Космос", 2499.28, 1012, 29991.36],
        ["Товар 8", "ООО Радость", 25212.79, 1015, 378191.85],
        ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44],
        ["Товар 10", "ИП Разум", 17789.22, 1010, 177892.2]
    ],
    "history": []
}

def test_api(query, expected_in_response):
    """Test API with a query"""
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print(f"{'='*60}")

    payload = test_data.copy()
    payload["query"] = query

    url = "https://sheetgpt-production.up.railway.app/api/v1/formula"

    try:
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            summary = result.get('summary', 'NO SUMMARY')
            methodology = result.get('methodology', 'NO METHODOLOGY')

            print(f"SUMMARY:\n{summary}")
            print(f"\nMETHODOLOGY:\n{methodology}")

            # Check if expected content is in response
            success = any(exp.lower() in summary.lower() for exp in expected_in_response)

            if success:
                print(f"\n[OK] CORRECT! Found expected: {expected_in_response}")
            else:
                print(f"\n[ERROR] Expected: {expected_in_response}")
                print(f"        Got: {summary}")

            return success
        else:
            print(f"[ERROR] HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return False


def main():
    print("SheetGPT API Test - Products vs Suppliers Detection")
    print("="*60)

    # Wait for deployment
    print("Waiting 30 seconds for deployment...")
    time.sleep(30)

    tests = [
        # Test 1: Ask about suppliers
        {
            "query": "у какого поставщика больше всего продаж",
            "expected": ["ООО Время", "442"]
        },
        # Test 2: Ask about products
        {
            "query": "Топ 3 товара по продажам",
            "expected": ["Товар 8", "Товар 14", "Товар 2"]
        },
        # Test 3: Ask about top product
        {
            "query": "какой товар продается лучше всего",
            "expected": ["Товар 8", "378"]
        },
    ]

    results = []
    for test in tests:
        success = test_api(test["query"], test["expected"])
        results.append(success)
        time.sleep(2)  # Delay between tests

    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS:")
    print("="*60)

    for i, (test, success) in enumerate(zip(tests, results), 1):
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} Test {i}: {test['query'][:40]}...")

    total = len(results)
    passed = sum(results)
    print(f"\nTOTAL: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
    else:
        print("\n[FAILURE] Some tests failed!")


if __name__ == "__main__":
    main()