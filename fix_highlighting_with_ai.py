#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6.6.0: Исправление выделения строк через AI Code Executor

ПРОБЛЕМА:
- "выдели красным Усову" → выделяет строки 2-6 вместо строки 9 (Усова)
- AI генерирует код для поиска, но не возвращает rows_to_highlight

РЕШЕНИЕ:
1. Обнаруживаем ключевые слова выделения в запросе
2. Добавляем в промпт инструкцию для AI генерировать rows_to_highlight
3. Используем rows_to_highlight из exec_result вместо примитивного regex
"""

import re

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ===================================================================
# ШАГ 1: Модифицируем промпт для AI, чтобы генерировать rows_to_highlight
# ===================================================================

# Находим место, где формируется prompt для AI (перед "NOW GENERATE CODE FOR THIS QUESTION:")
old_prompt_end = '''NOW GENERATE CODE FOR THIS QUESTION:
{query}

Return ONLY the Python code, no explanations."""'''

new_prompt_end = '''🎯 SPECIAL INSTRUCTION FOR HIGHLIGHTING QUERIES:
If the query asks to "выдели" (highlight), "подсвети" (highlight), "отметь" (mark) specific rows,
you MUST generate an additional variable called 'rows_to_highlight' containing a list of DataFrame 
row indices (0-based) that match the search criteria.

Example for "выдели строку с фамилией Усова":
```python
# Find rows where Фамилия contains "Усова"
matching_rows = df[df[df.columns[0]].str.contains("Усова", case=False, na=False)]
rows_to_highlight = matching_rows.index.tolist()  # [7] if Усова is at index 7
result = matching_rows.to_dict('records')
summary = f"Найдено строк: {len(matching_rows)}"
methodology = f"Filtered {df.columns[0]} column for 'Усова'"
```

Example for "выдели красным строки с женскими именами":
```python
female_names = ["Татьяна", "Светлана", "Людмила", "Ольга", "Александра"]
matching_rows = df[df[df.columns[1]].isin(female_names)]
rows_to_highlight = matching_rows.index.tolist()  # [0, 3, 6, 7, 8, 14]
result = matching_rows.to_dict('records')
summary = f"Найдено строк с женскими именами: {len(matching_rows)}"
methodology = f"Filtered {df.columns[1]} column for female names"
```

⚠️ IMPORTANT: rows_to_highlight must contain DataFrame indices (0-based), NOT Google Sheets row numbers!

NOW GENERATE CODE FOR THIS QUESTION:
{query}

Return ONLY the Python code, no explanations."""'''

content = content.replace(old_prompt_end, new_prompt_end)

# ===================================================================
# ШАГ 2: Удаляем примитивную логику подсветки (строки 467-506)
# ===================================================================

# Находим и удаляем секцию is_search_query
old_search_logic = r'''            # Проверяем тип запроса
            is_search_query = any\(word in query_lower for word in \['фамили', 'имен', 'строк', 'найди', 'где'\]\)

            if is_search_query:
                # ПОИСК КОНКРЕТНОГО ЗНАЧЕНИЯ \(например, "выдели строку с фамилией Шилов"\)
                print\(f"\[SEARCH\] Looking for specific value in data"\)
                rows_to_highlight = \[\]

                # Извлекаем искомое значение из запроса
                import re
                # Паттерн для поиска фамилий \(слова с заглавной буквы\)
                names_pattern = r'\b\[А-ЯA-Z\]\[а-яa-z\]\+\b'
                names_found = re\.findall\(names_pattern, query\)

                if names_found:
                    for name in names_found:
                        print\(f"\[SEARCH\] Looking for: \{name\}"\)
                        # Используем key_findings для определения позиций
                        # Это временное решение - используем фиксированные позиции
                        if "Шилов" in name:
                            rows_to_highlight\.append\(10\)  # Шилов в строке 10
                            print\(f"\[FOUND\] \{name\} at row 10"\)
                        elif name in str\(exec_result\.get\("result", ""\)\):
                            # Для других имен пробуем найти в результате
                            rows_to_highlight\.append\(2\)  # По умолчанию строка 2
                            print\(f"\[FOUND\] \{name\} at row 2"\)

                if rows_to_highlight:
                    highlight_color = requested_color or '#ADD8E6'  # Используем запрошенный цвет
                    found_items = ", "\.join\(names_found\) if names_found else "запрошенные данные"
                    highlight_message = f'Найдена строка: \{found_items\}'
                    highlighting_data = \{
                        "action_type": "highlight_rows",
                        "highlight_rows": rows_to_highlight,
                        "highlight_color": highlight_color,
                        "highlight_message": highlight_message
                    \}
                else:
                    highlighting_data = None
                    print\(f"\[WARNING\] Could not find requested value"\)
            else:'''

new_search_logic = '''            # Проверяем, вернул ли AI rows_to_highlight
            rows_from_ai = exec_result.get('rows_to_highlight', None)
            
            if rows_from_ai is not None and len(rows_from_ai) > 0:
                # AI нашёл строки для подсветки!
                print(f"[AI_HIGHLIGHT] AI returned rows_to_highlight: {rows_from_ai}")
                
                # Преобразуем индексы DataFrame (0-based) в номера строк Google Sheets (1-based + header)
                # DataFrame index 0 = Google Sheets row 2 (row 1 is header)
                rows_to_highlight = [idx + 2 for idx in rows_from_ai]
                
                highlight_color = requested_color or '#ADD8E6'  # Используем запрошенный цвет
                highlight_message = f'Выделено строк: {len(rows_to_highlight)}'
                highlighting_data = {
                    "action_type": "highlight_rows",
                    "highlight_rows": rows_to_highlight,
                    "highlight_color": highlight_color,
                    "highlight_message": highlight_message
                }
                print(f"[SUCCESS] Highlighting data generated: {highlighting_data}")
            else:'''

content = re.sub(old_search_logic, new_search_logic, content, flags=re.DOTALL)

# Записываем изменённый файл
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] v6.6.0: AI-powered highlighting fix applied!")
print("[INFO] Changes:")
print("1. Modified AI prompt to generate rows_to_highlight")
print("2. Replaced primitive regex search with AI results")
print("3. AI now returns DataFrame indices for highlighting")
