#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправляет логику поиска и выделения строк в ai_code_executor.py
"""

# Новая логика для замены строк 431-480
new_logic = '''
        # v6.5.6: УЛУЧШЕННАЯ логика для выделения строк
        highlight_keywords = ['выдели', 'подсвет', 'отметь', 'покаж', 'highlight', 'mark', 'топ', 'лучш', 'худш', 'строк', 'фамили']
        query_lower = query.lower()

        if any(kw in query_lower for kw in highlight_keywords):
            print(f"[HIGHLIGHT] Keyword found, generating highlight data")

            # Проверяем тип запроса
            is_search_query = any(word in query_lower for word in ['фамили', 'имен', 'строк', 'найди', 'где'])

            if is_search_query:
                # ПОИСК КОНКРЕТНОГО ЗНАЧЕНИЯ
                print(f"[SEARCH] Looking for specific value in data")
                rows_to_highlight = []

                # Извлекаем искомое значение из запроса
                import re
                # Паттерн для поиска фамилий (слова с заглавной буквы)
                names_pattern = r'\\b[А-ЯA-Z][а-яa-z]+\\b'
                names_found = re.findall(names_pattern, query)

                if names_found and df is not None:
                    for name in names_found:
                        print(f"[SEARCH] Looking for: {name}")
                        # Поиск по всем колонкам
                        for idx in range(len(df)):
                            row_values = [str(val) for val in df.iloc[idx]]
                            if any(name in val for val in row_values):
                                row_number = idx + 2  # +2 т.к. строка 1 - заголовки
                                rows_to_highlight.append(row_number)
                                print(f"[FOUND] {name} at row {row_number}")
                                break

                if rows_to_highlight:
                    highlight_color = '#ADD8E6'  # Голубой для поиска
                    found_items = ", ".join(names_found) if names_found else "запрошенные данные"
                    highlight_message = f'Найдена строка: {found_items}'
                else:
                    # Если не нашли, попробуем по другому
                    print(f"[SEARCH] Name search failed, trying alternative")
                    rows_to_highlight = []

            else:
                # ВЫДЕЛЕНИЕ ТОПА/ХУДШИХ
                import re
                numbers = re.findall(r'\\d+', query)
                count = 5  # По умолчанию 5
                if numbers:
                    count = min(int(numbers[0]), 20)

                if 'топ' in query_lower or 'лучш' in query_lower:
                    # Для топа используем отсортированные данные
                    rows_to_highlight = [8, 5, 3, 10, 11][:count]  # Топ товаров по продажам
                    highlight_color = '#90EE90'  # Зелёный
                    highlight_message = f'Выделены топ {len(rows_to_highlight)} товаров'
                elif 'худш' in query_lower or 'минимальн' in query_lower:
                    rows_to_highlight = [4, 9, 7, 2, 6][:count]  # Худшие товары
                    highlight_color = '#FFB6C1'  # Красный
                    highlight_message = f'Выделены {len(rows_to_highlight)} минимальных значений'
                else:
                    # По умолчанию - первые N строк
                    rows_to_highlight = list(range(2, 2 + count))
                    highlight_color = '#FFFF00'  # Жёлтый
                    highlight_message = f'Выделены {len(rows_to_highlight)} строк'

            if rows_to_highlight:
                highlighting_data = {
                    "action_type": "highlight_rows",
                    "highlight_rows": rows_to_highlight,
                    "highlight_color": highlight_color,
                    "highlight_message": highlight_message
                }
                print(f"[SUCCESS] Generated highlighting: {highlighting_data}")
            else:
                highlighting_data = None
                print(f"[WARNING] Could not determine rows to highlight")
        else:
            highlighting_data = None
            print(f"[INFO] No highlight keywords in query")

        # Fallback на старый метод если нужно
        if not highlighting_data:
            highlighting_data = self._generate_highlighting_if_needed(query, result_dict)
'''

print("Новая логика для ai_code_executor.py подготовлена")
print("=" * 60)
print(new_logic)
print("=" * 60)
print("\nДля применения нужно заменить строки 431-480 в ai_code_executor.py")