# Fix undo snapshot - use data instead of values
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/content.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """    console.log('[SheetGPT] ✅ Snapshot captured:', response.result?.values?.length, 'rows');
    return {
      success: true,
      data: {
        sheetName: sheetName,
        values: response.result.values,
        headers: response.result.headers
      }
    };"""

new = """    // GET_SHEET_DATA returns { headers, data }, not { headers, values }
    // For undo we need the raw data rows including headers
    const rawData = response.result.data || [];
    const headers = response.result.headers || [];

    // Combine headers + data for full restore
    const allValues = [headers, ...rawData];

    console.log('[SheetGPT] ✅ Snapshot captured:', allValues.length, 'rows (including header)');
    return {
      success: true,
      data: {
        sheetName: sheetName,
        values: allValues,
        headers: headers
      }
    };"""

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Fixed undo snapshot')
else:
    print('ERROR: Pattern not found')
