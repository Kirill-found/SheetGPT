# Fix: Only write aggregated_data for single_row transposition, not regular aggregation
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/sheets-api.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''    // Handle aggregated/transposed data (e.g., for single-row filtered charts)
    let tempDataRange = null;
    if (aggregated_data && aggregated_data.rows && aggregated_data.rows.length > 0) {
      console.log(`[SheetsAPI] Using aggregated data: ${aggregated_data.rows.length} rows`);'''

new_code = '''    // Handle aggregated/transposed data (e.g., for single-row filtered charts)
    // Only write temp data for TRANSPOSED single-row data, not regular aggregation
    let tempDataRange = null;
    const needsTempWrite = aggregated_data &&
                           aggregated_data.rows &&
                           aggregated_data.rows.length > 0 &&
                           aggregated_data.aggregation_type === 'single_row';

    if (needsTempWrite) {
      console.log(`[SheetsAPI] Writing transposed data: ${aggregated_data.rows.length} rows (single_row mode)`);'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Only write temp data for single_row transposition')
else:
    print('ERROR: Pattern not found')
