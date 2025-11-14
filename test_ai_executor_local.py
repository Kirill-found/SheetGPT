#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Локальный тест AI Code Executor с выделением
"""

import json
import sys
import os

# Добавляем путь к backend
sys.path.insert(0, 'C:/SheetGPT/backend')

# Устанавливаем переменные окружения
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['OPENAI_API_KEY'] = 'test-key'

from backend.app.services.ai_code_executor import AICodeExecutor

def test_highlighting():
    """Тестируем функцию выделения в AI Code Executor"""

    # Инициализация
    executor = AICodeExecutor()

    # Тестовый запрос
    request_data = {
        "query": "выдели топ 5 товаров по продажам",
        "column_names": ["Товар", "Продажи", "Статус"],
        "sheet_data": [
            ["Товар A", 1500, "Активен"],
            ["Товар B", 2500, "Активен"],
            ["Товар C", 500, "Неактивен"],
            ["Товар D", 3000, "Активен"],
            ["Товар E", 1200, "Активен"],
            ["Товар F", 800, "Неактивен"],
            ["Товар G", 4000, "Активен"],
            ["Товар H", 600, "Неактивен"],
            ["Товар I", 2200, "Активен"],
            ["Товар J", 1800, "Активен"]
        ],
        "custom_context": ""
    }

    print("=" * 60)
    print("TESTING AI CODE EXECUTOR WITH HIGHLIGHTING")
    print("=" * 60)
    print(f"\nQuery: {request_data['query']}")
    print(f"Data rows: {len(request_data['sheet_data'])}")

    try:
        # Вызываем основной метод
        print("\n[CALLING] executor.generate_formula_code()...")
        response = executor.generate_formula_code(
            query=request_data['query'],
            sheet_data=request_data['sheet_data'],
            column_names=request_data['column_names'],
            custom_context=request_data.get('custom_context', '')
        )

        print("\n[RESPONSE]:")
        print(f"Response type: {type(response)}")

        if isinstance(response, dict):
            # Выводим ключевые поля
            print(f"\nКлючевые поля:")
            print(f"- action_type: {response.get('action_type')}")
            print(f"- highlight_rows: {response.get('highlight_rows')}")
            print(f"- highlight_color: {response.get('highlight_color')}")
            print(f"- highlight_message: {response.get('highlight_message')}")
            print(f"- key_findings: {response.get('key_findings', [])[:3]}")

            # Проверяем наличие выделения
            if response.get('highlight_rows'):
                print("\n[SUCCESS] ✅ Highlighting data found!")
                print(f"Rows to highlight: {response.get('highlight_rows')}")
                print(f"Color: {response.get('highlight_color')}")
                print(f"Message: {response.get('highlight_message')}")
                return True
            else:
                print("\n[FAILED] ❌ No highlighting data in response")
                print("Full response keys:", list(response.keys()))
                return False
        else:
            print(f"\n[ERROR] Unexpected response type: {type(response)}")
            return False

    except Exception as e:
        print(f"\n[ERROR] Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_highlighting()

    print("\n" + "=" * 60)
    if success:
        print("TEST RESULT: ✅ PASSED - Highlighting works!")
    else:
        print("TEST RESULT: ❌ FAILED - Highlighting not working")
    print("=" * 60)