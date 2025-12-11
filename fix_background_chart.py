# -*- coding: utf-8 -*-
# Update background.js to handle chart aggregation

with open('C:/Projects/SheetGPT/chrome-extension/src/background.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_function = '''/**
 * Create a chart in Google Sheet
 */
async function handleCreateChart(tabId, tabUrl, data) {
  console.log('[Background] 📊 Creating chart, data:', JSON.stringify(data));

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  console.log('[Background] 📊 Spreadsheet ID:', spreadsheetId);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { chartSpec } = data;

  if (!chartSpec) {
    throw new Error('Chart specification is required');
  }

  // Get saved sheet name from storage
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1';

  console.log(`[Background] 📊 Using sheet name "${sheetName}" for chart (storageKey: ${storageKey})`);

  // Get sheet ID
  console.log('[Background] 📊 Getting sheet ID...');
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);
  console.log('[Background] 📊 Sheet ID:', sheetId);

  // Create chart
  console.log('[Background] 📊 Calling createChart API...');
  const result = await createChart(spreadsheetId, sheetId, chartSpec);

  console.log('[Background] ✅ Chart created successfully:', result);
  return result;
}'''

new_function = '''/**
 * Convert column index to letter (0 = A, 1 = B, 26 = AA, etc.)
 */
function columnIndexToLetter(index) {
  let letter = '';
  while (index >= 0) {
    letter = String.fromCharCode((index % 26) + 65) + letter;
    index = Math.floor(index / 26) - 1;
  }
  return letter;
}

/**
 * Create a chart in Google Sheet
 * Supports aggregated data - writes summary data before creating chart
 */
async function handleCreateChart(tabId, tabUrl, data) {
  console.log('[Background] 📊 Creating chart, data:', JSON.stringify(data));

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  console.log('[Background] 📊 Spreadsheet ID:', spreadsheetId);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  let { chartSpec } = data;

  if (!chartSpec) {
    throw new Error('Chart specification is required');
  }

  // Get saved sheet name from storage
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1';

  console.log(`[Background] 📊 Using sheet name "${sheetName}" for chart (storageKey: ${storageKey})`);

  // Get sheet ID
  console.log('[Background] 📊 Getting sheet ID...');
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);
  console.log('[Background] 📊 Sheet ID:', sheetId);

  // Check if we need to write aggregated data first
  if (chartSpec.aggregated_data && chartSpec.needs_aggregation) {
    console.log('[Background] 📊 Chart needs aggregation, writing summary data...');

    const { headers, rows, aggregation_type } = chartSpec.aggregated_data;

    // Write aggregated data to a new location (after main data + 3 columns)
    const startCol = chartSpec.col_count + 3;
    const startColLetter = columnIndexToLetter(startCol);
    const endColLetter = columnIndexToLetter(startCol + headers.length - 1);

    // Prepare data with headers
    const allData = [headers, ...rows];
    const range = `${sheetName}!${startColLetter}1:${endColLetter}${allData.length}`;

    console.log(`[Background] 📊 Writing aggregated data to ${range}`);
    console.log(`[Background] 📊 Aggregated data: ${rows.length} rows, headers: ${headers.join(', ')}`);

    // Write the aggregated data
    await writeDataToRange(spreadsheetId, range, allData);

    // Update chartSpec to use aggregated data location
    chartSpec = {
      ...chartSpec,
      x_column_index: startCol,
      y_column_indices: headers.slice(1).map((_, i) => startCol + 1 + i),
      row_count: rows.length,
      col_count: startCol + headers.length
    };

    // Update title to indicate aggregation
    if (aggregation_type) {
      const aggNames = { sum: 'Сумма', mean: 'Среднее', count: 'Количество' };
      chartSpec.title = chartSpec.title + ` (${aggNames[aggregation_type] || aggregation_type})`;
    }

    console.log('[Background] 📊 Updated chart spec for aggregated data');
  }

  // Create chart
  console.log('[Background] 📊 Calling createChart API...');
  const result = await createChart(spreadsheetId, sheetId, chartSpec);

  console.log('[Background] ✅ Chart created successfully:', result);
  return result;
}'''

if old_function in content:
    content = content.replace(old_function, new_function)
    with open('C:/Projects/SheetGPT/chrome-extension/src/background.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated background.js with chart aggregation support')
else:
    print('Could not find the target function in background.js')
