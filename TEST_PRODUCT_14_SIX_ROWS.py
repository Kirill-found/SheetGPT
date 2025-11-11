#!/usr/bin/env python3
"""
Test for Product 14 with 6 rows totaling 588,530
Проверка что API правильно суммирует все 6 строк Товара 14
"""

import requests
import json
import time

# Test data with 6 instances of Товар 14
# Total should be 588,530
test_data = {
    "column_names": ["Колонка A", "Колонка B", "Колонка C", "Колонка D", "Колонка E"],
    "sheet_data": [
        # 6 строк с Товаром 14 - должно быть 588,530 в сумме
        ["Товар 14", "ООО Время", 6328.28, 1007, 44297.96],
        ["Товар 1", "ООО Время", 10730.32, 1010, 107303.2],
        ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44],
        ["Товар 2", "ООО Сатурн", 8568.37, 1030, 257051.1],
        ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44],
        ["Товар 3", "ООО Луна", 7318.09, 1020, 146361.8],
        ["Товар 14", "ООО Время", 6328.28, 1015, 63282.8],  # Новая строка
        ["Товар 5", "ООО Персектив", 1196.9, 1017, 20347.3],
        ["Товар 14", "ООО Время", 6328.28, 1025, 129076.72],  # Новая строка
        ["Товар 7", "ООО Космос", 2499.28, 1012, 29991.36],
        ["Товар 14", "ООО Время", 6328.28, 1022, 60771.44],  # Новая строка
        ["Товар 8", "ООО Радость", 25212.79, 1015, 378191.85],
        ["Товар 10", "ИП Разум", 17789.22, 1010, 177892.2],
        ["Товар 2", "ООО Сатурн", 8568.37, 1018, 154230.66]  # Еще один Товар 2
    ],
    "history": []
}

def calculate_expected():
    """Рассчитать ожидаемые суммы"""
    products = {}
    suppliers = {}

    for row in test_data["sheet_data"]:
        product = row[0]
        supplier = row[1]
        sales = row[4]

        if product not in products:
            products[product] = 0
        products[product] += sales

        if supplier not in suppliers:
            suppliers[supplier] = 0
        suppliers[supplier] += sales

    print("\n=== ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ ===")
    print("\nТовары:")
    sorted_products = sorted(products.items(), key=lambda x: x[1], reverse=True)
    for i, (name, total) in enumerate(sorted_products[:5], 1):
        print(f"{i}. {name}: {total:,.2f} руб.")

    print("\nПоставщики:")
    sorted_suppliers = sorted(suppliers.items(), key=lambda x: x[1], reverse=True)
    for i, (name, total) in enumerate(sorted_suppliers[:5], 1):
        print(f"{i}. {name}: {total:,.2f} руб.")

    return products, suppliers

def test_api(query, expected_values):
    """Test API with a query"""
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print(f"EXPECTED: {expected_values}")
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
            key_findings = result.get('key_findings', [])

            print(f"SUMMARY:\n{summary}")
            print(f"\nMETHODOLOGY:\n{methodology}")
            print(f"\nKEY FINDINGS:")
            for finding in key_findings:
                print(f"  - {finding}")

            # Check if expected values are in response
            success = False
            for expected in expected_values:
                if str(expected).lower() in summary.lower() or \
                   any(str(expected).lower() in str(finding).lower() for finding in key_findings):
                    success = True
                    print(f"\n[OK] Найдено ожидаемое значение: {expected}")
                else:
                    print(f"\n[WARNING] Не найдено: {expected}")

            return success
        else:
            print(f"[ERROR] HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return False

def main():
    print("="*60)
    print("ТЕСТ: Товар 14 должен иметь 6 строк с суммой 588,530")
    print("="*60)

    # Рассчитать ожидаемые значения
    products, suppliers = calculate_expected()

    # Проверить Товар 14
    product_14_total = products.get("Товар 14", 0)
    print(f"\n[INFO] Товар 14 сумма: {product_14_total:,.2f} руб.")

    if abs(product_14_total - 588530) < 1:
        print("[OK] Товар 14 правильно суммируется до 588,530!")
    else:
        print(f"[ERROR] Товар 14 должен быть 588,530, но получилось {product_14_total:,.2f}")

    # Ждем деплоя
    print("\nЖдем 15 секунд для деплоя...")
    time.sleep(15)

    # Тесты
    tests = [
        {
            "query": "Топ 3 товара по продажам",
            "expected": ["Товар 14", "588", "Товар 2", "411", "Товар 8", "378"]
        },
        {
            "query": "какой товар продается лучше всего",
            "expected": ["Товар 14", "588"]
        },
        {
            "query": "у какого поставщика больше всего продаж",
            "expected": ["ООО Время", "850"]
        }
    ]

    results = []
    for test in tests:
        success = test_api(test["query"], test["expected"])
        results.append(success)
        time.sleep(2)

    # Итоги
    print("\n" + "="*60)
    print("ИТОГИ ТЕСТИРОВАНИЯ:")
    print("="*60)

    for i, (test, success) in enumerate(zip(tests, results), 1):
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} Test {i}: {test['query'][:40]}...")

    total = len(results)
    passed = sum(results)
    print(f"\nВСЕГО: {passed}/{total} тестов прошло")

    if passed == total:
        print("\n[SUCCESS] Все тесты прошли! Товар 14 правильно агрегируется!")
    else:
        print("\n[FAILURE] Некоторые тесты не прошли!")

if __name__ == "__main__":
    main()