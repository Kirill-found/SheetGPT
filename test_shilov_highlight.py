#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Локальный тест выделения строки с фамилией Шилов
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

def test_shilov_highlighting():
    """Тестируем поиск и выделение строки с фамилией Шилов"""

    # Инициализация
    executor = AICodeExecutor()

    # Тестовые данные из test_shilov_request.json
    request_data = {
        "query": "выдели строку с фамилией Шилов",
        "column_names": ["Фамилия", "Имя", "Отчество"],
        "sheet_data": [
            ["Петрова", "Татьяна", "Васильевна"],
            ["Смирнов", "Антон", "Иванович"],
            ["Шабаров", "Александр", "Владимирович"],
            ["Кононова", "Светлана", "Евгеньевна"],
            ["Колпаков", "Евгений", "Олегович"],
            ["Шапочникова", "Людмила", "Петровна"],
            ["Белоусова", "Ольга", "Николаевна"],
            ["Усова", "Светлана", "Владимировна"],
            ["Шилов", "Петр", "Семенович"],  # Строка 10 (индекс 8)
            ["Шалов", "Алексей", "Викторович"],
            ["Морозов", "Максим", "Максимович"],
            ["Дорохов", "Дмитрий", "Сергеевич"],
            ["Капустин", "Константин", "Евгеньевич"],
            ["Самойлова", "Александра", "Валентиновна"]
        ],
        "custom_context": ""
    }

    print("=" * 60)
    print("TESTING SHILOV NAME SEARCH HIGHLIGHTING")
    print("=" * 60)
    print(f"\nQuery: {request_data['query']}")
    print(f"Looking for: Шилов (should be at row 10)")
    print(f"Data rows: {len(request_data['sheet_data'])}")

    try:
        # Вызываем основной метод
        print("\n[CALLING] executor.process_with_code()...")
        response = executor.process_with_code(
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

            # Проверяем наличие выделения
            if response.get('highlight_rows'):
                print("\n[SUCCESS] Highlighting data found!")
                print(f"Rows to highlight: {response.get('highlight_rows')}")
                print(f"Color: {response.get('highlight_color')}")
                print(f"Message: {response.get('highlight_message')}")

                # Проверяем, что выделена правильная строка (10)
                if 10 in response.get('highlight_rows', []):
                    print("\n[PERFECT] Row 10 (Шилов) is correctly highlighted!")
                    return True
                else:
                    print(f"\n[ERROR] Wrong row highlighted. Expected 10, got {response.get('highlight_rows')}")
                    return False
            else:
                print("\n[FAILED] No highlighting data in response")
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
    success = test_shilov_highlighting()

    print("\n" + "=" * 60)
    if success:
        print("TEST RESULT: [OK] PASSED - Шилов found and highlighted!")
    else:
        print("TEST RESULT: [X] FAILED - Highlighting not working for name search")
    print("=" * 60)