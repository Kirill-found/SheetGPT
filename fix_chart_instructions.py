# Add chart-specific instructions to SmartGPT prompt
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """🔹 БЫСТРЫЕ ДЕЙСТВИЯ (визуальное оформление):
   sort, color_scale, conditional_format, chart, freeze, write_value
   ⚠️ highlight — ТОЛЬКО в FULL режиме! В SAMPLE → analysis

🔹 ФОРМУЛЫ В СТОЛБЕЦ (add_formula):"""

new = """🔹 БЫСТРЫЕ ДЕЙСТВИЯ (визуальное оформление):
   sort, color_scale, conditional_format, chart, freeze, write_value
   ⚠️ highlight — ТОЛЬКО в FULL режиме! В SAMPLE → analysis

🔹 ДИАГРАММЫ (chart) - ВАЖНО!
   Когда просят "диаграмму", "график", "chart":
   → ВСЕГДА возвращай action_type: "chart"
   → НЕ используй analysis для диаграмм!
   → chart_type: "PIE" для круговой, "COLUMN" для столбчатой, "LINE" для линейной
   → x_column_index: индекс колонки с категориями (0, 1, 2...)
   → y_column_indices: [индексы колонок со значениями]

   Пример для "круговая диаграмма по складам":
   {{"action_type": "chart", "chart_spec": {{"chart_type": "PIE", "title": "Остатки по складам", "x_column_index": 0, "y_column_indices": [1], "row_count": 109}}, "summary": "Создаю круговую диаграмму"}}

🔹 ФОРМУЛЫ В СТОЛБЕЦ (add_formula):"""

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added chart instructions')
else:
    print('ERROR: Pattern not found')
