# Update chart selection GPT prompt to include row_filter
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_prompt = '''Ответь ТОЛЬКО в формате JSON:
{{
  "x_column": <индекс колонки для оси X>,
  "y_columns": [<индексы колонок для оси Y>],
  "title": "<заголовок>",
  "needs_aggregation": <true/false>,
  "aggregation": "<sum/mean/count/null>"
}}

ВАЖНО - АГРЕГАЦИЯ:'''

new_prompt = '''Ответь ТОЛЬКО в формате JSON:
{{
  "x_column": <индекс колонки для оси X>,
  "y_columns": [<индексы колонок для оси Y>],
  "title": "<заголовок>",
  "needs_aggregation": <true/false>,
  "aggregation": "<sum/mean/count/null>",
  "row_filter": {{"column": <индекс>, "value": "<значение>"}} или null
}}

ВАЖНО - ФИЛЬТРАЦИЯ ПО СТРОКЕ:
- Если пользователь просит "за декабрь", "за январь", "за 2024" и т.п.:
  row_filter = {{"column": 0, "value": "Декабрь"}} (ищи значение в первом столбце)
- Если НЕ указан конкретный период: row_filter = null

ВАЖНО - АГРЕГАЦИЯ:'''

if old_prompt in content:
    content = content.replace(old_prompt, new_prompt)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Updated GPT prompt for row_filter')
else:
    print('ERROR: GPT prompt pattern not found')
    # Debug: show what's actually there
    idx = content.find('Ответь ТОЛЬКО в формате JSON:')
    if idx >= 0:
        print(f'Found at index {idx}')
        print(repr(content[idx:idx+300]))
