#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест API эндпоинта для CustomFunctions
Имитирует запросы от Google Apps Script
"""

import sys
import io
import requests
import json
import time

# Фикс для Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = "https://sheetgpt-production.up.railway.app/api/v1/formula"

# Тестовые данные - имитация таблицы продаж
test_data = {
    "column_names": ["Менеджер", "Продукт", "Сумма", "Дата"],
    "sheet_data": [
        ["Иванов", "Ноутбук", 150000, "2024-01-15"],
        ["Петров", "Телефон", 80000, "2024-01-16"],
        ["Иванов", "Мышка", 2000, "2024-01-17"],
        ["Сидоров", "Клавиатура", 5000, "2024-01-18"],
        ["Петров", "Монитор", 25000, "2024-01-19"]
    ]
}

# Тестовые кейсы для каждой функции
test_cases = [
    {
        "name": "GPT - простой вопрос",
        "query": "Кто лучший менеджер по продажам?",
        "expected_format": "text"
    },
    {
        "name": "GPT_VALUE - числовое значение",
        "query": "Какая общая сумма продаж?",
        "expected_format": "number"
    },
    {
        "name": "GPT_LIST - список",
        "query": "Список всех менеджеров",
        "expected_format": "array"
    },
    {
        "name": "GPT_TABLE - таблица",
        "query": "Группировка по менеджерам с суммой продаж",
        "expected_format": "table"
    }
]

def test_api(test_case):
    """Тестирует один запрос к API"""
    print(f"\n{'='*80}")
    print(f"🧪 Тест: {test_case['name']}")
    print(f"📝 Запрос: {test_case['query']}")
    print(f"{'='*80}")

    payload = {
        "query": test_case["query"],
        "column_names": test_data["column_names"],
        "sheet_data": test_data["sheet_data"]
    }

    try:
        start_time = time.time()
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        elapsed = time.time() - start_time

        print(f"⏱️  Время ответа: {elapsed:.2f}s")
        print(f"📊 HTTP статус: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Успешный ответ:")
            print(f"   response_type: {result.get('response_type')}")
            print(f"   function_used: {result.get('function_used')}")
            print(f"   confidence: {result.get('confidence')}")

            # Показываем релевантную часть ответа
            if test_case["expected_format"] == "text":
                print(f"   explanation: {result.get('explanation', 'N/A')[:200]}...")
            elif test_case["expected_format"] == "number":
                print(f"   summary: {result.get('summary', 'N/A')}")
            elif test_case["expected_format"] == "array":
                insights = result.get('insights', [])
                print(f"   insights (первые 3): {insights[:3]}")
            elif test_case["expected_format"] == "table":
                structured = result.get('structured_data', {})
                if structured:
                    print(f"   structured_data keys: {list(structured.keys())}")
                    if 'data' in structured:
                        print(f"   rows: {len(structured['data'])}")

            return True
        else:
            print(f"\n❌ Ошибка HTTP {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False

    except requests.Timeout:
        print(f"\n⏰ TIMEOUT после 30 секунд")
        return False
    except Exception as e:
        print(f"\n❌ Исключение: {type(e).__name__}: {e}")
        return False

def main():
    print("🚀 Тестирование API для CustomFunctions")
    print(f"🌐 Endpoint: {API_URL}")
    print(f"📋 Тестовых кейсов: {len(test_cases)}")

    results = []
    for i, test_case in enumerate(test_cases, 1):
        success = test_api(test_case)
        results.append(success)

        # Пауза между запросами
        if i < len(test_cases):
            print("\n⏳ Пауза 2 секунды...")
            time.sleep(2)

    # Итоги
    print(f"\n{'='*80}")
    print(f"📊 РЕЗУЛЬТАТЫ")
    print(f"{'='*80}")
    passed = sum(results)
    total = len(results)
    print(f"✅ Успешно: {passed}/{total} ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ! CustomFunctions готовы к использованию.")
    else:
        print(f"\n⚠️  {total - passed} тестов провалились. Проверьте логи выше.")

if __name__ == "__main__":
    main()
