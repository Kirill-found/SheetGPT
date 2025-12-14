# Add clearRowBackgrounds function in sheets-api.js
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/sheets-api.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add function after highlightRows
old = """/**
 * Sort data in a range by column
 * @param {string} spreadsheetId - The spreadsheet ID
 * @param {number} sheetId - The sheet ID (not name!)
 * @param {number} columnIndex - 0-based column index to sort by
 * @param {string} sortOrder - "ASCENDING" or "DESCENDING"
 * @param {number} startRowIndex - Start row (0-based, typically 1 to skip header)
 * @param {number} endRowIndex - End row (exclusive), or -1 for all rows"""

new = """/**
 * Clear row background colors (set to white/default)
 */
async function clearRowBackgrounds(spreadsheetId, sheetName, rowIndices) {
  try {
    const token = await getAuthToken();

    // Get sheet ID from name
    const sheetId = await getSheetIdByName(spreadsheetId, sheetName);
    if (sheetId === null) {
      throw new Error(`Sheet "${sheetName}" not found`);
    }

    // Set background to white (removing any highlight)
    const whiteColor = { red: 1, green: 1, blue: 1 };

    const requests = rowIndices.map(rowIndex => ({
      repeatCell: {
        range: {
          sheetId: sheetId,
          startRowIndex: rowIndex - 1,  // Convert to 0-based
          endRowIndex: rowIndex         // End is exclusive
        },
        cell: {
          userEnteredFormat: {
            backgroundColor: whiteColor
          }
        },
        fields: 'userEnteredFormat.backgroundColor'
      }
    }));

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
    console.log('[SheetsAPI] ✅ Row backgrounds cleared:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error clearing row backgrounds:', error);
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

if old in content:
    content = content.replace(old, new)
    print('SUCCESS 1: Added clearRowBackgrounds function')
else:
    print('ERROR 1: Function pattern not found')

# Also add to exports
old_export = """    highlightRows,"""
new_export = """    highlightRows,
    clearRowBackgrounds,"""

if old_export in content:
    content = content.replace(old_export, new_export)
    print('SUCCESS 2: Added to exports')
else:
    print('ERROR 2: Export pattern not found')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
