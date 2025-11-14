#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v6.6.0: Исправление выделения через анализ результатов AI

Вместо примитивного regex поиска используем результаты выполнения Python кода от AI.
"""

filepath = 'C:/SheetGPT/backend/app/services/ai_code_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найти строку с 'if is_search_query:'
is_search_line = None
for i, line in enumerate(lines):
    if 'if is_search_query:' in line and 'ПОИСК КОНКРЕТНОГО ЗНАЧЕНИЯ' in lines[i+1] if i+1 < len(lines) else False:
        is_search_line = i
        break

if is_search_line is None:
    print('[ERROR] Could not find is_search_query block')
    exit(1)

# Найти конец блока is_search_query (следующий else:)
end_line = None
for i in range(is_search_line + 1, len(lines)):
    if lines[i].strip() == 'else:':
        # Проверяем, что это на том же уровне отступа
        if lines[i].startswith('            else:'):
            end_line = i
            break

if end_line is None:
    print('[ERROR] Could not find end of is_search_query block')
    exit(1)

print(f'[INFO] Found is_search_query block: lines {is_search_line+1} to {end_line}')

# Новый код для замены
new_code = '''            if is_search_query:
                # AI УЖЕ ВЫПОЛНИЛ ПОИСК - используем результаты!
                print(f"[SEARCH] AI executed search, analyzing results")
                rows_to_highlight = []
                
                # Проверяем, что AI нашёл данные
                result = exec_result.get('result')
                if result is not None:
                    # Если result - это DataFrame, берём его индексы
                    if hasattr(result, 'index'):
                        rows_to_highlight = [idx + 2 for idx in result.index.tolist()]
                        print(f"[AI_RESULT] Found DataFrame with indices: {result.index.tolist()}")
                    # Если result - это list of dicts (после to_dict('records')), 
                    # ищем исходные индексы в DataFrame
                    elif isinstance(result, list) and len(result) > 0:
                        # AI вернул отфильтрованные данные
                        # Ищем эти данные в исходном DataFrame
                        if df is not None:
                            for row_data in result:
                                # Ищем совпадение по первой колонке
                                first_col = df.columns[0]
                                if first_col in row_data:
                                    search_value = row_data[first_col]
                                    matches = df[df[first_col] == search_value]
                                    if not matches.empty:
                                        rows_to_highlight.extend([idx + 2 for idx in matches.index.tolist()])
                        print(f"[AI_RESULT] Extracted {len(rows_to_highlight)} rows from list result")
                
                if rows_to_highlight:
                    highlight_color = requested_color or '#ADD8E6'
                    highlight_message = f'Выделено строк: {len(rows_to_highlight)}'
                    highlighting_data = {
                        "action_type": "highlight_rows",
                        "highlight_rows": rows_to_highlight,
                        "highlight_color": highlight_color,
                        "highlight_message": highlight_message
                    }
                    print(f"[SUCCESS] Generated highlighting: {highlighting_data}")
                else:
                    highlighting_data = None
                    print(f"[WARNING] Could not extract rows from AI results")
            else:
'''

# Заменяем блок
new_lines = lines[:is_search_line] + [new_code] + lines[end_line:]

# Записываем
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('[OK] v6.6.0: Simple highlighting fix applied!')
print('[INFO] Now uses AI execution results instead of regex search')
