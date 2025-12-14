# Fix column letter calculation for aggregated data charts
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/sheets-api.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''    if (aggregated_data && aggregated_data.rows && aggregated_data.rows.length > 0) {
      console.log(`[SheetsAPI] Using aggregated data: ${aggregated_data.rows.length} rows`);

      // Write aggregated data to a temporary range (far right columns)
      const tempStartCol = (col_count || 10) + 5; // Start 5 columns after the data
      const tempColLetter = String.fromCharCode(65 + tempStartCol); // Convert to letter
      const tempColLetter2 = String.fromCharCode(65 + tempStartCol + 1);

      // Prepare data with headers
      const writeData = [aggregated_data.headers, ...aggregated_data.rows];'''

new_code = '''    if (aggregated_data && aggregated_data.rows && aggregated_data.rows.length > 0) {
      console.log(`[SheetsAPI] Using aggregated data: ${aggregated_data.rows.length} rows`);

      // Helper function to convert column index to letter (handles AA, AB, etc.)
      const colIndexToLetter = (index) => {
        let letter = '';
        while (index >= 0) {
          letter = String.fromCharCode(65 + (index % 26)) + letter;
          index = Math.floor(index / 26) - 1;
        }
        return letter;
      };

      // Write aggregated data to a temporary range
      // Use column index 0-1 for simplicity (overwrite first 2 cols with temp data, then create chart)
      // Actually, let's write to a new sheet or far right. For now, use small offset
      const numDataCols = aggregated_data.headers.length;
      const tempStartCol = Math.max(0, (col_count || 5) + 2); // Start 2 columns after data
      const tempEndCol = tempStartCol + numDataCols - 1;
      const tempColLetter = colIndexToLetter(tempStartCol);
      const tempColLetterEnd = colIndexToLetter(tempEndCol);

      console.log(`[SheetsAPI] Temp range: col ${tempStartCol} (${tempColLetter}) to col ${tempEndCol} (${tempColLetterEnd})`);

      // Prepare data with headers
      const writeData = [aggregated_data.headers, ...aggregated_data.rows];'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print('SUCCESS: Fixed column letter calculation')
else:
    print('ERROR: Pattern not found')

# Also fix the write range
old_range = '''      // Write temp data
      const writeRange = `'${sheetName}'!${tempColLetter}1:${tempColLetter2}${writeData.length}`;'''

new_range = '''      // Write temp data
      const writeRange = `'${sheetName}'!${tempColLetter}1:${tempColLetterEnd}${writeData.length}`;'''

if old_range in content:
    content = content.replace(old_range, new_range)
    print('SUCCESS: Fixed write range')
else:
    print('ERROR: Write range pattern not found')

# Fix the chart indices update
old_indices = '''      if (writeResponse.ok) {
        console.log(`[SheetsAPI] Aggregated data written successfully`);
        // Update chart parameters to use temp range
        x_column_index = tempStartCol;
        y_column_indices = [tempStartCol + 1];
        row_count = aggregated_data.rows.length;
        tempDataRange = { startCol: tempStartCol, endCol: tempStartCol + 2, rowCount: writeData.length };
      }'''

new_indices = '''      if (writeResponse.ok) {
        console.log(`[SheetsAPI] Aggregated data written successfully`);
        // Update chart parameters to use temp range
        x_column_index = tempStartCol;
        // Y columns are all columns after X (index 1 to numDataCols-1 in temp range)
        y_column_indices = [];
        for (let i = 1; i < numDataCols; i++) {
          y_column_indices.push(tempStartCol + i);
        }
        row_count = aggregated_data.rows.length;
        tempDataRange = { startCol: tempStartCol, endCol: tempEndCol + 1, rowCount: writeData.length };
        console.log(`[SheetsAPI] Chart will use: X=${x_column_index}, Y=${y_column_indices.join(',')}, rows=${row_count}`);
      }'''

if old_indices in content:
    content = content.replace(old_indices, new_indices)
    print('SUCCESS: Fixed chart indices')
else:
    print('ERROR: Chart indices pattern not found')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
