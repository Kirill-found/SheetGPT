#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладочный тест для поиска проблемы с выделением
"""

import json
import sys
import os

# Добавляем путь к backend
sys.path.insert(0, 'C:/SheetGPT/backend')

# Устанавливаем переменные окружения
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['OPENAI_API_KEY'] = 'sk-test-key'  # Фиктивный ключ для теста

def test_highlight_logic():
    """Тестируем логику выделения напрямую"""

    import pandas as pd
    import re

    # Тестовые данные
    sheet_data = [
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
    ]

    column_names = ["Фамилия", "Имя", "Отчество"]
    query = "выдели строку с фамилией Шилов"

    # Создаем DataFrame
    df = pd.DataFrame(sheet_data, columns=column_names)

    print("=" * 60)
    print("DEBUG: Testing highlight logic directly")
    print("=" * 60)
    print(f"\nQuery: {query}")
    print(f"\nDataFrame shape: {df.shape}")
    print("\nFirst few rows:")
    print(df.head())

    # Логика выделения
    query_lower = query.lower()
    highlight_keywords = ['выдели', 'подсвет', 'отметь', 'покаж', 'highlight', 'mark', 'топ', 'лучш', 'худш', 'строк', 'фамили']

    if any(kw in query_lower for kw in highlight_keywords):
        print("\n[STEP 1] Highlight keyword found!")

        # Проверяем тип запроса
        is_search_query = any(word in query_lower for word in ['фамили', 'имен', 'строк', 'найди', 'где'])

        if is_search_query:
            print("[STEP 2] This is a search query")

            rows_to_highlight = []

            # Извлекаем искомое значение
            names_pattern = r'\b[А-ЯA-Z][а-яa-z]+\b'
            names_found = re.findall(names_pattern, query)
            print(f"[STEP 3] Names found in query: {names_found}")

            if names_found and df is not None:
                for name in names_found:
                    print(f"\n[SEARCH] Looking for: {name}")

                    # Поиск по всем колонкам
                    for idx in range(len(df)):
                        row_values = [str(val) for val in df.iloc[idx]]
                        print(f"  Row {idx+2}: {row_values}")

                        if any(name in val for val in row_values):
                            row_number = idx + 2  # +2 т.к. строка 1 - заголовки
                            rows_to_highlight.append(row_number)
                            print(f"  [FOUND] {name} at row {row_number}")
                            break

            if rows_to_highlight:
                highlight_color = '#ADD8E6'  # Голубой для поиска
                found_items = ", ".join(names_found) if names_found else "запрошенные данные"
                highlight_message = f'Найдена строка: {found_items}'

                highlighting_data = {
                    "action_type": "highlight_rows",
                    "highlight_rows": rows_to_highlight,
                    "highlight_color": highlight_color,
                    "highlight_message": highlight_message
                }

                print(f"\n[SUCCESS] Generated highlighting: {highlighting_data}")

                # Проверка результата
                if 10 in rows_to_highlight:
                    print("\n[PERFECT] Row 10 (Шилов) is correctly highlighted!")
                    return True
                else:
                    print(f"\n[ERROR] Wrong row. Expected 10, got {rows_to_highlight}")
                    return False
            else:
                print("\n[ERROR] No rows found to highlight")
                return False

    return False

if __name__ == "__main__":
    success = test_highlight_logic()

    print("\n" + "=" * 60)
    if success:
        print("TEST RESULT: [OK] Logic works correctly!")
    else:
        print("TEST RESULT: [X] Logic needs fixing")
    print("=" * 60)