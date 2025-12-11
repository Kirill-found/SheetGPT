# -*- coding: utf-8 -*-
# Add writeDataToRange function to sheets-api.js

with open('C:/Projects/SheetGPT/chrome-extension/src/sheets-api.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Add the new function after writeSheetData
new_function = '''

/**
 * Write data to a specific range (for aggregated chart data)
 * @param {string} spreadsheetId - The spreadsheet ID
 * @param {string} range - Full range like "Sheet1!N1:O10"
 * @param {Array} data - 2D array of data
 */
async function writeDataToRange(spreadsheetId, range, data) {
  try {
    const token = await getAuthToken();

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}/values/${encodeURIComponent(range)}?valueInputOption=USER_ENTERED`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          range: range,
          values: data
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const result = await response.json();
    console.log('[SheetsAPI] ✅ Data written to range:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error writing to range:', error);
    throw error;
  }
}
'''

# Insert after writeSheetData function
insert_after = '''  } catch (error) {
    console.error('[SheetsAPI] Error writing sheet data:', error);
    throw error;
  }
}

/**
 * Append data to sheet
 */'''

content = content.replace(insert_after, '''  } catch (error) {
    console.error('[SheetsAPI] Error writing sheet data:', error);
    throw error;
  }
}
''' + new_function + '''
/**
 * Append data to sheet
 */''')

# Also add to exports
old_exports = '''  module.exports = {
    getAuthToken,
    getSpreadsheetIdFromUrl,
    getActiveSheetName,
    readSheetData,
    writeSheetData,
    appendSheetData,'''

new_exports = '''  module.exports = {
    getAuthToken,
    getSpreadsheetIdFromUrl,
    getActiveSheetName,
    readSheetData,
    writeSheetData,
    writeDataToRange,
    appendSheetData,'''

content = content.replace(old_exports, new_exports)

with open('C:/Projects/SheetGPT/chrome-extension/src/sheets-api.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Added writeDataToRange function to sheets-api.js')
