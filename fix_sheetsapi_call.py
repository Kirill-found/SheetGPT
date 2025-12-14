# Fix SheetsAPI call in background.js
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/background.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = "const result = await SheetsAPI.clearRowBackgrounds(spreadsheetId, actualSheetName, rowIndices);"
new = "const result = await clearRowBackgrounds(spreadsheetId, actualSheetName, rowIndices);"

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Fixed SheetsAPI call')
else:
    print('ERROR: Pattern not found')
