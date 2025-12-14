# Add support for aggregated_data in chart creation (sheets-api.js)
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/sheets-api.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the createChart function and add aggregated_data handling at the beginning
old_start = '''async function createChart(spreadsheetId, sheetId, chartSpec) {
  try {
    const token = await getAuthToken();

    const { chart_type, title, x_column_index, y_column_indices, row_count, col_count } = chartSpec;

    console.log(`[SheetsAPI] Creating ${chart_type} chart: "${title}"`);
    console.log(`[SheetsAPI] X column: ${x_column_index}, Y columns: ${y_column_indices}, rows: ${row_count}`);

    // Build series for each Y column
    const series = y_column_indices.map((yColIndex, idx) => ({'''

new_start = '''async function createChart(spreadsheetId, sheetId, chartSpec) {
  try {
    const token = await getAuthToken();

    let { chart_type, title, x_column_index, y_column_indices, row_count, col_count, aggregated_data } = chartSpec;

    console.log(`[SheetsAPI] Creating ${chart_type} chart: "${title}"`);
    console.log(`[SheetsAPI] X column: ${x_column_index}, Y columns: ${y_column_indices}, rows: ${row_count}`);

    // Handle aggregated/transposed data (e.g., for single-row filtered charts)
    let tempDataRange = null;
    if (aggregated_data && aggregated_data.rows && aggregated_data.rows.length > 0) {
      console.log(`[SheetsAPI] Using aggregated data: ${aggregated_data.rows.length} rows`);

      // Write aggregated data to a temporary range (far right columns)
      const tempStartCol = (col_count || 10) + 5; // Start 5 columns after the data
      const tempColLetter = String.fromCharCode(65 + tempStartCol); // Convert to letter
      const tempColLetter2 = String.fromCharCode(65 + tempStartCol + 1);

      // Prepare data with headers
      const writeData = [aggregated_data.headers, ...aggregated_data.rows];

      // Get sheet name for writing
      const sheetsResponse = await fetch(
        `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}?fields=sheets(properties(sheetId,title))`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const sheetsData = await sheetsResponse.json();
      const sheet = sheetsData.sheets?.find(s => s.properties.sheetId === sheetId);
      const sheetName = sheet?.properties?.title || 'Sheet1';

      // Write temp data
      const writeRange = `'${sheetName}'!${tempColLetter}1:${tempColLetter2}${writeData.length}`;
      console.log(`[SheetsAPI] Writing aggregated data to ${writeRange}`);

      const writeResponse = await fetch(
        `https://sheets.googleapis.com/v4/spreadsheets/${spreadsheetId}/values/${encodeURIComponent(writeRange)}?valueInputOption=RAW`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ values: writeData })
        }
      );

      if (writeResponse.ok) {
        console.log(`[SheetsAPI] Aggregated data written successfully`);
        // Update chart parameters to use temp range
        x_column_index = tempStartCol;
        y_column_indices = [tempStartCol + 1];
        row_count = aggregated_data.rows.length;
        tempDataRange = { startCol: tempStartCol, endCol: tempStartCol + 2, rowCount: writeData.length };
      } else {
        console.error(`[SheetsAPI] Failed to write aggregated data: ${await writeResponse.text()}`);
      }
    }

    // Build series for each Y column
    const series = y_column_indices.map((yColIndex, idx) => ({'''

if old_start in content:
    content = content.replace(old_start, new_start)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added aggregated_data support to createChart')
else:
    print('ERROR: createChart pattern not found')
