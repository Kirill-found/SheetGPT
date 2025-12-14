# Fix: Add transpose_columns support for "по категориям" pie charts
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update prompt to include transpose_columns
old_prompt = '''Ответь ТОЛЬКО в формате JSON:
{{
  "x_column": <индекс колонки для оси X>,
  "y_columns": [<индексы колонок для оси Y>],
  "title": "<заголовок>",
  "needs_aggregation": <true/false>,
  "aggregation": "<sum/mean/count/null>",
  "row_filter": {{"column": <индекс>, "value": "<значение>"}} или null
}}

ВАЖНО - ФИЛЬТРАЦИЯ ПО СТРОКЕ:'''

new_prompt = '''Ответь ТОЛЬКО в формате JSON:
{{
  "x_column": <индекс колонки для оси X>,
  "y_columns": [<индексы колонок для оси Y>],
  "title": "<заголовок>",
  "needs_aggregation": <true/false>,
  "aggregation": "<sum/mean/count/null>",
  "row_filter": {{"column": <индекс>, "value": "<значение>"}} или null,
  "transpose_columns": <true/false>
}}

ВАЖНО - ТРАНСПОНИРОВАНИЕ КОЛОНОК (transpose_columns):
- Если пользователь просит "по категориям", "долю категорий", "распределение по категориям"
  и категории это КОЛОНКИ (Электроника, Одежда, Продукты и т.п.):
  transpose_columns = true
  Это создаст диаграмму где НАЗВАНИЯ КОЛОНОК станут X-осью, а СУММЫ по колонкам - значениями
- Если категории это СТРОКИ (уже в одной колонке): transpose_columns = false

ВАЖНО - ФИЛЬТРАЦИЯ ПО СТРОКЕ:'''

if old_prompt in content:
    content = content.replace(old_prompt, new_prompt)
    print('SUCCESS: Updated prompt with transpose_columns')
else:
    print('ERROR: Prompt pattern not found')

# 2. Add logic to handle transpose_columns in _finalize_chart_action
old_finalize = '''            row_filter = gpt_result.get("row_filter")

            # Apply row filter if specified (e.g., "за декабрь")
            if row_filter and isinstance(row_filter, dict):'''

new_finalize = '''            row_filter = gpt_result.get("row_filter")
            transpose_columns = gpt_result.get("transpose_columns", False)

            # Handle transpose_columns: sum each numeric column and create transposed data
            # This is for "по категориям" where column names become X-axis labels
            if transpose_columns and len(y_indices) > 1:
                logger.info(f"[SimpleGPT] Transpose columns mode: summing columns and transposing")
                rows = []
                for y_idx in y_indices:
                    if y_idx < len(df.columns):
                        col_name = column_names[y_idx]
                        try:
                            col_sum = pd.to_numeric(df.iloc[:, y_idx], errors='coerce').sum()
                            rows.append([col_name, round(float(col_sum), 2)])
                        except Exception as e:
                            logger.error(f"[SimpleGPT] Error summing column {col_name}: {e}")

                if rows:
                    aggregated_data = {
                        "headers": ["Категория", "Сумма"],
                        "rows": rows,
                        "aggregation_type": "single_row"  # Use single_row to trigger temp write
                    }
                    needs_aggregation = True
                    logger.info(f"[SimpleGPT] Transposed column data: {rows}")

            # Apply row filter if specified (e.g., "за декабрь")
            if row_filter and isinstance(row_filter, dict):'''

if old_finalize in content:
    content = content.replace(old_finalize, new_finalize)
    print('SUCCESS: Added transpose_columns handling')
else:
    print('ERROR: Finalize pattern not found')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
