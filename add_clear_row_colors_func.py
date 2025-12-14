# Add clearRowColors function in content.js after restoreSheetData
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/content.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add function after restoreSheetData function
old = """/**
 * Write a single value to a specific cell
 * @param {string} targetCell - Cell address like "B12", "C5"
 * @param {any} value - Value to write
 */
async function writeCellValue(targetCell, value) {"""

new = """/**
 * Clear background color from specified rows (for highlight undo)
 * @param {Array} rows - Row numbers to clear (1-indexed)
 * @param {string} sheetName - Name of the sheet
 */
async function clearRowColors(rows, sheetName) {
  console.log('[SheetGPT] ↩️ Clearing colors from rows:', rows);

  try {
    if (!rows || rows.length === 0) {
      return { success: true, message: 'No rows to clear' };
    }

    const response = await safeSendMessage({
      action: 'CLEAR_ROW_COLORS',
      data: {
        sheetName: sheetName || 'Sheet1',
        rowIndices: rows
      }
    });

    if (!response.success) {
      throw new Error(response.error || 'Failed to clear row colors');
    }

    console.log('[SheetGPT] ✅ Row colors cleared');
    return {
      success: true,
      message: `Цвет убран с ${rows.length} строк`
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ Error clearing row colors:', error);
    return {
      success: false,
      message: error.message
    };
  }
}

/**
 * Write a single value to a specific cell
 * @param {string} targetCell - Cell address like "B12", "C5"
 * @param {any} value - Value to write
 */
async function writeCellValue(targetCell, value) {"""

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added clearRowColors function')
else:
    print('ERROR: Pattern not found')
