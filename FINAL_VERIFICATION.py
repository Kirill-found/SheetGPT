#!/usr/bin/env python3
"""
ФИНАЛЬНАЯ ПРОВЕРКА SheetGPT
Проверяем что Товар 14 правильно агрегируется (6 строк = 588,530)
"""

import requests
import json
import time
from datetime import datetime

def test_complete_data():
    """Тест с полными данными пользователя"""

    # Реальные данные пользователя с 6 строками Товара 14
    test_data = {
        "column_names": ["Колонка A", "Колонка B", "Колонка C", "Колонка D", "Колонка E"],
        "sheet_data": [
            # Все строки из таблицы пользователя
            ["Товар 1", "ООО Время", 10730.32, 1010, 107303.2],
            ["Товар 2", "ООО Сатурн", 8568.37, 1030, 257051.1],
            ["Товар 3", "ООО Луна", 7318.09, 1020, 146361.8],
            ["Товар 14", "ООО Время", 6328.28, 1007, 44297.96],  # 1
            ["Товар 5", "ООО Персектив", 1196.9, 1017, 20347.3],
            ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44], # 2
            ["Товар 7", "ООО Космос", 2499.28, 1012, 29991.36],
            ["Товар 8", "ООО Радость", 25212.79, 1015, 378191.85],
            ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44], # 3
            ["Товар 10", "ИП Разум", 17789.22, 1010, 177892.2],
            # Строки после 10-й (которые раньше не отправлялись!)
            ["Товар 11", "ООО Солнце", 5432.10, 1005, 54321.0],
            ["Товар 14", "ООО Время", 6328.28, 1015, 63282.8],  # 4 - ПОСЛЕ 10 СТРОКИ!
            ["Товар 12", "ИП Мечта", 3210.50, 1008, 32105.0],
            ["Товар 14", "ООО Время", 6328.28, 1025, 129076.72], # 5 - ПОСЛЕ 10 СТРОКИ!
            ["Товар 13", "ООО Звезда", 4567.89, 1003, 45678.9],
            ["Товар 14", "ООО Время", 6328.28, 1022, 60771.44], # 6 - ПОСЛЕ 10 СТРОКИ!
            ["Товар 2", "ООО Сатурн", 8568.37, 1018, 154230.66], # Еще один Товар 2
            ["Товар 6", "ИП Надежда", 2345.67, 1011, 23456.7],
        ],
        "history": []
    }

    print("="*70)
    print("ФИНАЛЬНАЯ ПРОВЕРКА SheetGPT v3.0.6")
    print("="*70)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: https://sheetgpt-production.up.railway.app")
    print("="*70)

    # Считаем ожидаемые результаты
    print("\nАНАЛИЗ ДАННЫХ:")
    print("-"*40)

    products = {}
    suppliers = {}
    product_14_rows = []

    for i, row in enumerate(test_data["sheet_data"]):
        product = row[0]
        supplier = row[1]
        sales = row[4]

        # Собираем статистику по товарам
        if product not in products:
            products[product] = {"total": 0, "rows": []}
        products[product]["total"] += sales
        products[product]["rows"].append(i+1)

        # Собираем статистику по поставщикам
        if supplier not in suppliers:
            suppliers[supplier] = 0
        suppliers[supplier] += sales

        # Отслеживаем Товар 14
        if product == "Товар 14":
            product_14_rows.append({
                "row": i+1,
                "supplier": supplier,
                "sales": sales
            })

    # Выводим информацию о Товаре 14
    print(f"\nТОВАР 14 - ДЕТАЛЬНЫЙ АНАЛИЗ:")
    print(f"Найдено строк: {len(product_14_rows)}")
    total_14 = 0
    for item in product_14_rows:
        print(f"  Строка {item['row']:2}: {item['supplier']:15} = {item['sales']:10,.2f} руб.")
        total_14 += item['sales']
    print(f"  {'='*40}")
    print(f"  ИТОГО: {total_14:,.2f} руб.")

    expected_total = 588530.00
    if abs(total_14 - expected_total) < 1:
        print(f"  [OK] ПРАВИЛЬНО! Ожидалось: {expected_total:,.2f}")
    else:
        print(f"  [ERROR] ОШИБКА! Ожидалось: {expected_total:,.2f}, получено: {total_14:,.2f}")

    # Топ товаров
    print(f"\nТОП 5 ТОВАРОВ:")
    sorted_products = sorted(products.items(), key=lambda x: x[1]["total"], reverse=True)
    for i, (name, data) in enumerate(sorted_products[:5], 1):
        rows_info = f"({len(data['rows'])} строк)"
        print(f"  {i}. {name:10} = {data['total']:10,.2f} руб. {rows_info}")

    # Топ поставщиков
    print(f"\nТОП 5 ПОСТАВЩИКОВ:")
    sorted_suppliers = sorted(suppliers.items(), key=lambda x: x[1], reverse=True)
    for i, (name, total) in enumerate(sorted_suppliers[:5], 1):
        print(f"  {i}. {name:15} = {total:10,.2f} руб.")

    print("\n" + "="*70)
    print("ТЕСТИРОВАНИЕ API")
    print("="*70)

    # Тесты
    tests = [
        {
            "name": "Топ товаров",
            "query": "Топ 3 товара по продажам",
            "expected": ["Товар 14", "588", "Товар 2", "411", "Товар 8", "378"]
        },
        {
            "name": "Лучший товар",
            "query": "какой товар продается лучше всего",
            "expected": ["Товар 14", "588"]
        },
        {
            "name": "Топ поставщиков",
            "query": "у какого поставщика больше всего продаж",
            "expected": ["ООО Время", "850"]  # 850333 = все продажи ООО Время
        },
    ]

    url = "https://sheetgpt-production.up.railway.app/api/v1/formula"

    all_passed = True
    for test in tests:
        print(f"\nТЕСТ: {test['name']}")
        print(f"Запрос: {test['query']}")
        print("-"*40)

        payload = test_data.copy()
        payload["query"] = test["query"]

        try:
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                summary = result.get('summary', '')
                methodology = result.get('methodology', '')

                print(f"Ответ: {summary[:100]}...")
                print(f"Методология: {methodology[:100]}...")

                # Проверяем ожидаемые значения
                test_passed = True
                for expected in test["expected"]:
                    if expected.lower() not in summary.lower():
                        print(f"  [X] Не найдено: {expected}")
                        test_passed = False
                        all_passed = False
                    else:
                        print(f"  [OK] Найдено: {expected}")

                if test_passed:
                    print(f"  РЕЗУЛЬТАТ: [PASS] ПРОЙДЕН")
                else:
                    print(f"  РЕЗУЛЬТАТ: [FAIL] НЕ ПРОЙДЕН")
            else:
                print(f"[ERROR] HTTP {response.status_code}: {response.text}")
                all_passed = False

        except Exception as e:
            print(f"[ERROR] Ошибка: {str(e)}")
            all_passed = False

        time.sleep(1)

    print("\n" + "="*70)
    print("ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("="*70)

    if all_passed:
        print("[SUCCESS] ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("\nСИСТЕМА РАБОТАЕТ КОРРЕКТНО:")
        print("- Товар 14 правильно агрегируется (6 строк = 588,530 руб.)")
        print("- Поставщики правильно группируются")
        print("- API возвращает правильные результаты")
        print("\nМОЖНО ИСПОЛЬЗОВАТЬ В PRODUCTION!")
    else:
        print("[FAILURE] ЕСТЬ ПРОБЛЕМЫ!")
        print("\nПРОВЕРЬТЕ:")
        print("1. Используется ли Code_PRODUCTION_FINAL.gs?")
        print("2. Отправляются ли ВСЕ строки данных?")
        print("3. Правильно ли работает агрегация на сервере?")

    print("="*70)

if __name__ == "__main__":
    test_complete_data()