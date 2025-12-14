# Add row filter support for charts
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update GPT prompt to include row_filter
old_prompt = '''Ответь ТОЛЬКО в формате JSON:
{
  "x_column": <индекс колонки для оси X>,
  "y_columns": [<индексы колонок для оси Y>],
  "title": "<заголовок>",
  "needs_aggregation": <true/false>,
  "aggregation": "<sum/mean/count/null>"
}

ВАЖНО - АГРЕГАЦИЯ:'''

new_prompt = '''Ответь ТОЛЬКО в формате JSON:
{
  "x_column": <индекс колонки для оси X>,
  "y_columns": [<индексы колонок для оси Y>],
  "title": "<заголовок>",
  "needs_aggregation": <true/false>,
  "aggregation": "<sum/mean/count/null>",
  "row_filter": {"column": <индекс>, "value": "<значение>"} или null
}

ВАЖНО - ФИЛЬТРАЦИЯ ПО СТРОКЕ:
- Если пользователь просит "за декабрь", "за январь", "за 2024" и т.п.:
  row_filter = {"column": 0, "value": "Декабрь"} (ищи значение в первом столбце)
- Если НЕ указан конкретный период: row_filter = null

ВАЖНО - АГРЕГАЦИЯ:'''

if old_prompt in content:
    content = content.replace(old_prompt, new_prompt)
    print('SUCCESS: Updated GPT prompt for row_filter')
else:
    print('ERROR: GPT prompt pattern not found')

# 2. Update _finalize_chart_action to apply row_filter
old_finalize = '''        if gpt_result:
            x_idx = gpt_result.get("x_column", 0)
            y_indices = gpt_result.get("y_columns", [1])
            title = gpt_result.get("title", "Диаграмма")
            needs_aggregation = gpt_result.get("needs_aggregation", False)
            aggregation = gpt_result.get("aggregation", "sum")
        else:'''

new_finalize = '''        if gpt_result:
            x_idx = gpt_result.get("x_column", 0)
            y_indices = gpt_result.get("y_columns", [1])
            title = gpt_result.get("title", "Диаграмма")
            needs_aggregation = gpt_result.get("needs_aggregation", False)
            aggregation = gpt_result.get("aggregation", "sum")
            row_filter = gpt_result.get("row_filter")

            # Apply row filter if specified (e.g., "за декабрь")
            if row_filter and isinstance(row_filter, dict):
                filter_col = row_filter.get("column", 0)
                filter_val = row_filter.get("value", "")
                if filter_col < len(df.columns) and filter_val:
                    # Find matching row
                    col_data = df.iloc[:, filter_col].astype(str).str.lower()
                    mask = col_data.str.contains(filter_val.lower(), na=False)
                    filtered_df = df[mask]
                    if len(filtered_df) > 0:
                        df = filtered_df
                        logger.info(f"[SimpleGPT] Chart row filter applied: {filter_val}, {len(df)} rows")
        else:'''

if old_finalize in content:
    content = content.replace(old_finalize, new_finalize)
    print('SUCCESS: Updated _finalize_chart_action for row_filter')
else:
    print('ERROR: _finalize_chart_action pattern not found')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
