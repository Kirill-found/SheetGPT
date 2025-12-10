# -*- coding: utf-8 -*-
# Add aggregation support for charts

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update the GPT prompt to include aggregation detection
old_prompt = '''        prompt = f"""Пользователь хочет создать диаграмму.
Запрос: "{query}"

Доступные колонки:
{columns_desc}

Выбери ТОЧНО те колонки, которые пользователь упомянул или имел в виду.

Ответь ТОЛЬКО в формате JSON:
{{"x_column": <индекс колонки для оси X (категории/даты)>, "y_columns": [<индексы колонок для оси Y (числовые значения)>], "title": "<заголовок диаграммы>"}}

Правила:
- X ось: категориальная или дата колонка (то, ПО ЧЕМУ группируем)
- Y ось: числовые колонки (то, ЧТО измеряем)
- Если пользователь написал "по категории и выручке" - X=категория, Y=выручка
- Если колонка не упомянута явно - НЕ добавляй её
- title должен отражать запрос пользователя"""'''

new_prompt = '''        # Check for duplicates in potential X columns
        unique_counts = {}
        for idx, col in enumerate(column_names):
            if idx < len(df.columns):
                unique_count = df.iloc[:, idx].nunique()
                total_count = len(df)
                unique_counts[col] = f"{unique_count} уникальных из {total_count}"

        unique_info = "\\n".join([f"  {col}: {info}" for col, info in unique_counts.items()])

        prompt = f"""Пользователь хочет создать диаграмму.
Запрос: "{query}"

Доступные колонки:
{columns_desc}

Количество уникальных значений:
{unique_info}

Ответь ТОЛЬКО в формате JSON:
{{
  "x_column": <индекс колонки для оси X>,
  "y_columns": [<индексы колонок для оси Y>],
  "title": "<заголовок>",
  "needs_aggregation": <true/false>,
  "aggregation": "<sum/mean/count/null>"
}}

ВАЖНО - АГРЕГАЦИЯ:
- Если X колонка имеет ПОВТОРЯЮЩИЕСЯ значения (уникальных < всего) - needs_aggregation=true
- Например: 5 категорий на 200 строк = НУЖНА агрегация (sum/mean)
- "по категории и выручке" = сумма выручки по каждой категории
- aggregation: "sum" для суммы, "mean" для среднего, "count" для количества
- Если уникальных значений = количеству строк - needs_aggregation=false

Правила выбора колонок:
- X ось: категория или дата (ПО ЧЕМУ группируем)
- Y ось: числовые колонки (ЧТО измеряем)
- title должен отражать запрос"""'''

content = content.replace(old_prompt, new_prompt)

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated GPT prompt with aggregation detection')
