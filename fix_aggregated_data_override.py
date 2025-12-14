# Fix: Don't overwrite aggregated_data if already set by transposition
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''        # Handle aggregation if needed
        aggregated_data = None
        if needs_aggregation and x_idx < len(df.columns):'''

new_code = '''        # Handle aggregation if needed (skip if already set by single-row transposition)
        if 'aggregated_data' not in locals():
            aggregated_data = None
        if needs_aggregation and x_idx < len(df.columns) and aggregated_data is None:'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Fixed aggregated_data override')
else:
    print('ERROR: Pattern not found')
