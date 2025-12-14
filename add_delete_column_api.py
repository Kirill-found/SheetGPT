# Add deleteColumn function in sheets-api.js
api_path = 'C:/Projects/SheetGPT/chrome-extension/src/sheets-api.js'
with open(api_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add function after clearRowBackgrounds
old1 = """/**
 * Sort data in a range by column
 * @param {string} spreadsheetId - The spreadsheet ID
 * @param {number} sheetId - The sheet ID (not name!)
 * @param {number} columnIndex - 0-based column index to sort by
 * @param {string} sortOrder - "ASCENDING" or "DESCENDING"
 * @param {number} startRowIndex - Start row (0-based, typically 1 to skip header)
 * @param {number} endRowIndex - End row (exclusive), or -1 for all rows"""

new1 = """/**
 * Delete a column from the sheet
 * @param {string} spreadsheetId - The spreadsheet ID
 * @param {string} sheetName - The sheet name
 * @param {string} column - Column letter (e.g., "M")
 */
async function deleteColumn(spreadsheetId, sheetName, column) {
  try {
    const token = await getAuthToken();

    // Get sheet ID from name
    const sheetId = await getSheetIdByName(spreadsheetId, sheetName);
    if (sheetId === null) {
      throw new Error(`Sheet "${sheetName}" not found`);
    }

    // Convert column letter to index (A=0, B=1, ..., M=12)
    const columnIndex = column.toUpperCase().charCodeAt(0) - 65;

    const requests = [{
      deleteDimension: {
        range: {
          sheetId: sheetId,
          dimension: 'COLUMNS',
          startIndex: columnIndex,
          endIndex: columnIndex + 1
        }
      }
    }];

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}:batchUpdate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ requests })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const result = await response.json();
    console.log('[SheetsAPI] ✅ Column deleted:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error deleting column:', error);
    throw error;
  }
}

/**
 * Sort data in a range by column
 * @param {string} spreadsheetId - The spreadsheet ID
 * @param {number} sheetId - The sheet ID (not name!)
 * @param {number} columnIndex - 0-based column index to sort by
 * @param {string} sortOrder - "ASCENDING" or "DESCENDING"
 * @param {number} startRowIndex - Start row (0-based, typically 1 to skip header)
 * @param {number} endRowIndex - End row (exclusive), or -1 for all rows"""

if old1 in content:
    content = content.replace(old1, new1)
    print('SUCCESS 1: Added deleteColumn function')
else:
    print('ERROR 1: Function pattern not found')

# Add to exports
old2 = """    clearRowBackgrounds,"""
new2 = """    clearRowBackgrounds,
    deleteColumn,"""

if old2 in content:
    content = content.replace(old2, new2)
    print('SUCCESS 2: Added to exports')
else:
    print('ERROR 2: Export pattern not found')

with open(api_path, 'w', encoding='utf-8') as f:
    f.write(content)
