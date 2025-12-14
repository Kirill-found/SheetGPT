# Add target_column support for add_formula action
import re

# 1. Update backend prompt
backend_file = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(backend_file, 'r', encoding='utf-8') as f:
    content = f.read()

old_prompt = 'add_formula: {{"action_type": "add_formula", "column_name": "Итого", "formula_template": "=H{{row}}+E{{row}}", "source_columns": ["H", "E"], "row_count": {len(df)}, "summary": "Добавляю столбец Итого с формулой =H+E"}}'

new_prompt = '''add_formula: {{"action_type": "add_formula", "column_name": "Итого", "formula_template": "=H{{row}}+E{{row}}", "source_columns": ["H", "E"], "row_count": {len(df)}, "target_column": "F" или null, "summary": "Добавляю столбец Итого с формулой =H+E"}}
   → target_column: если пользователь указал "в столбец F" или "в колонку F" - укажи букву. Если не указал - null (создать новый столбец)'''

if old_prompt in content:
    content = content.replace(old_prompt, new_prompt)
    with open(backend_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Updated backend prompt')
else:
    print('ERROR: Backend prompt not found')

# 2. Update sidebar.js
sidebar_file = 'C:/Projects/SheetGPT/chrome-extension/src/sidebar.js'
with open(sidebar_file, 'r', encoding='utf-8') as f:
    sidebar_content = f.read()

old_sidebar = "addFormulaColumn(apiResponse.column_name, apiResponse.formula_template, apiResponse.row_count);"

new_sidebar = "addFormulaColumn(apiResponse.column_name, apiResponse.formula_template, apiResponse.row_count, apiResponse.target_column);"

if old_sidebar in sidebar_content:
    sidebar_content = sidebar_content.replace(old_sidebar, new_sidebar)
    print('SUCCESS: Updated sidebar.js call')
else:
    print('ERROR: sidebar.js call not found')

# Also update the function definition in sidebar.js
old_sidebar_func = "async function addFormulaColumn(columnName, formulaTemplate, rowCount) {"

new_sidebar_func = "async function addFormulaColumn(columnName, formulaTemplate, rowCount, targetColumn = null) {"

if old_sidebar_func in sidebar_content:
    sidebar_content = sidebar_content.replace(old_sidebar_func, new_sidebar_func)
    print('SUCCESS: Updated sidebar.js function')
else:
    print('ERROR: sidebar.js function not found')

# Update sendToContentScript in sidebar.js
old_sidebar_send = '''    const response = await sendToContentScript('ADD_FORMULA_COLUMN', {
      columnName,
      formulaTemplate,
      rowCount
    });'''

new_sidebar_send = '''    const response = await sendToContentScript('ADD_FORMULA_COLUMN', {
      columnName,
      formulaTemplate,
      rowCount,
      targetColumn
    });'''

if old_sidebar_send in sidebar_content:
    sidebar_content = sidebar_content.replace(old_sidebar_send, new_sidebar_send)
    print('SUCCESS: Updated sidebar.js sendToContentScript')
else:
    print('ERROR: sidebar.js sendToContentScript not found')

with open(sidebar_file, 'w', encoding='utf-8') as f:
    f.write(sidebar_content)

# 3. Update content.js
content_file = 'C:/Projects/SheetGPT/chrome-extension/src/content.js'
with open(content_file, 'r', encoding='utf-8') as f:
    content_js = f.read()

old_content_call = "result = await addFormulaColumn(data.columnName, data.formulaTemplate, data.rowCount);"

new_content_call = "result = await addFormulaColumn(data.columnName, data.formulaTemplate, data.rowCount, data.targetColumn);"

if old_content_call in content_js:
    content_js = content_js.replace(old_content_call, new_content_call)
    print('SUCCESS: Updated content.js call')
else:
    print('ERROR: content.js call not found')

# Update function signature and logic in content.js
old_content_func = '''async function addFormulaColumn(columnName, formulaTemplate, rowCount) {
  console.log('[SheetGPT] ➕ Adding formula column:', columnName, formulaTemplate, rowCount);'''

new_content_func = '''async function addFormulaColumn(columnName, formulaTemplate, rowCount, targetColumn = null) {
  console.log('[SheetGPT] ➕ Adding formula column:', columnName, formulaTemplate, rowCount, 'target:', targetColumn);'''

if old_content_func in content_js:
    content_js = content_js.replace(old_content_func, new_content_func)
    print('SUCCESS: Updated content.js function signature')
else:
    print('ERROR: content.js function signature not found')

# Update the column selection logic
old_content_col = '''    // Find next empty column index (after last column with data)
    const numCols = sheetData.result.headers.length;
    const nextColIndex = numCols; // 0-indexed, so this is the first empty column
    const nextColLetter = String.fromCharCode(65 + nextColIndex); // A=0, B=1, etc.

    console.log('[SheetGPT] Next column:', nextColLetter, 'index:', nextColIndex);'''

new_content_col = '''    // Determine target column
    let targetColLetter;
    if (targetColumn) {
      // Use specified column
      targetColLetter = targetColumn.toUpperCase();
      console.log('[SheetGPT] Using specified target column:', targetColLetter);
    } else {
      // Find next empty column index (after last column with data)
      const numCols = sheetData.result.headers.length;
      const nextColIndex = numCols; // 0-indexed, so this is the first empty column
      targetColLetter = String.fromCharCode(65 + nextColIndex); // A=0, B=1, etc.
      console.log('[SheetGPT] Using next empty column:', targetColLetter, 'index:', nextColIndex);
    }'''

if old_content_col in content_js:
    content_js = content_js.replace(old_content_col, new_content_col)
    print('SUCCESS: Updated content.js column logic')
else:
    print('ERROR: content.js column logic not found')

# Update references from nextColLetter to targetColLetter
content_js = content_js.replace(
    "console.log('[SheetGPT] Writing formulas to column', nextColLetter,",
    "console.log('[SheetGPT] Writing formulas to column', targetColLetter,"
)
content_js = content_js.replace(
    "startCell: `${nextColLetter}1`,",
    "startCell: `${targetColLetter}1`,"
)
content_js = content_js.replace(
    'message: `Столбец "${columnName}" с формулой добавлен в колонку ${nextColLetter}`,',
    'message: `Столбец "${columnName}" с формулой добавлен в колонку ${targetColLetter}`,'
)
content_js = content_js.replace(
    "column: nextColLetter",
    "column: targetColLetter"
)

print('SUCCESS: Updated nextColLetter references')

with open(content_file, 'w', encoding='utf-8') as f:
    f.write(content_js)

print('\\nAll files updated!')
