# -*- coding: utf-8 -*-
# Add CSV split handler to sidebar.js

with open('C:/Projects/SheetGPT/chrome-extension/src/sidebar.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace - using partial match to avoid encoding issues
old = '''  // If response has structured_data (table)
  if (apiResponse.structured_data) {
    return {
      type: 'table','''

new = '''  // If response is a csv_split action
  if (apiResponse.action_type === 'csv_split' && apiResponse.structured_data) {
    console.log('[Sidebar] CSV split condition met!');
    // Store split data for later use with "Заменить данные" button
    window.lastSplitData = apiResponse.structured_data;
    return {
      type: 'csv_split',
      text: apiResponse.summary || 'Данные разбиты по ячейкам',
      newRows: apiResponse.new_rows || apiResponse.structured_data.rows?.length || 0,
      newCols: apiResponse.new_cols || apiResponse.structured_data.headers?.length || 0
    };
  }

  // If response has structured_data (table)
  if (apiResponse.structured_data) {
    return {
      type: 'table','''

if old in content:
    content = content.replace(old, new)
    with open('C:/Projects/SheetGPT/chrome-extension/src/sidebar.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: Added CSV split handler to sidebar.js')
else:
    print('NOT FOUND - searching for partial match...')
    # Try simpler search
    search = 'If response has structured_data (table)'
    idx = content.find(search)
    if idx > 0:
        print(f'Found at index {idx}')
        # Try with escaped quotes
        print(repr(content[idx-30:idx+200]))
