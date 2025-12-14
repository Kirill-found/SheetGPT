# Add search query example to prompt
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''explanation += f"\\nИтого проблем: {total_issues}"

ФОРМАТ (КРИТИЧНО):
- НЕ используй ** или * (markdown)'''

new = '''explanation += f"\\nИтого проблем: {total_issues}"

6. Для ПОИСКА СТРОК по условию (найди товары где X=0, найди строки с нулевыми значениями):
# Фильтруем по условию и выводим СПИСОК найденных записей
stock_cols = [col for col in df.columns if 'остат' in col.lower() and 'шт' in col.lower()]
id_col = df.columns[0]  # Первая колонка обычно ID/артикул

if stock_cols:
    # Конвертируем в числа, пустые = 0
    for col in stock_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Фильтруем: все указанные колонки = 0
    mask = (df[stock_cols] == 0).all(axis=1)
    found = df[mask]

    explanation = f"Товары с нулевыми остатками ({len(found)} шт.):\\n\\n"
    if len(found) > 0:
        for i, (idx, row) in enumerate(found.head(20).iterrows(), 1):
            explanation += f"{i}. {row[id_col]}\\n"
        if len(found) > 20:
            explanation += f"\\n...и ещё {len(found) - 20} товаров"
    else:
        explanation = "Товаров с нулевыми остатками на всех складах не найдено."
    result = found[id_col].tolist() if len(found) > 0 else []
else:
    explanation = "Колонки с остатками не найдены"
    result = explanation

ФОРМАТ (КРИТИЧНО):
- НЕ используй ** или * (markdown)'''

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added search query example')
else:
    print('ERROR: Pattern not found')
    # Debug: show what we're looking for
    import re
    pattern = r'explanation \+= f"\\nИтого проблем: \{total_issues\}"'
    matches = re.findall(pattern, content)
    print(f"Regex matches: {matches}")
