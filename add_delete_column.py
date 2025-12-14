# Add DELETE_COLUMN handler in content.js
content_path = 'C:/Projects/SheetGPT/chrome-extension/src/content.js'
with open(content_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add case in switch
old1 = """      case 'CLEAR_ROW_COLORS':
        console.log('[SheetGPT] ↩️ CLEAR_ROW_COLORS - clearing highlight from rows:', data.rows);
        result = await clearRowColors(data.rows, data.sheetName);
        break;

      default:"""

new1 = """      case 'CLEAR_ROW_COLORS':
        console.log('[SheetGPT] ↩️ CLEAR_ROW_COLORS - clearing highlight from rows:', data.rows);
        result = await clearRowColors(data.rows, data.sheetName);
        break;

      case 'DELETE_COLUMN':
        console.log('[SheetGPT] ↩️ DELETE_COLUMN - deleting column:', data.column);
        result = await deleteColumn(data.column, data.sheetName);
        break;

      default:"""

if old1 in content:
    content = content.replace(old1, new1)
    print('SUCCESS 1: Added DELETE_COLUMN case')
else:
    print('ERROR 1: Case pattern not found')

# Add function after clearRowColors
old2 = """/**
 * Write a single value to a specific cell
 * @param {string} targetCell - Cell address like "B12", "C5"
 * @param {any} value - Value to write
 */
async function writeCellValue(targetCell, value) {"""

new2 = """/**
 * Delete a column from the sheet
 * @param {string} column - Column letter (e.g., "M")
 * @param {string} sheetName - Name of the sheet
 */
async function deleteColumn(column, sheetName) {
  console.log('[SheetGPT] ↩️ Deleting column:', column);

  try {
    if (!column) {
      return { success: false, message: 'No column specified' };
    }

    const response = await safeSendMessage({
      action: 'DELETE_COLUMN',
      data: {
        sheetName: sheetName || 'Sheet1',
        column: column
      }
    });

    if (!response.success) {
      throw new Error(response.error || 'Failed to delete column');
    }

    console.log('[SheetGPT] ✅ Column deleted');
    return {
      success: true,
      message: `Колонка ${column} удалена`
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ Error deleting column:', error);
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

if old2 in content:
    content = content.replace(old2, new2)
    print('SUCCESS 2: Added deleteColumn function')
else:
    print('ERROR 2: Function pattern not found')

with open(content_path, 'w', encoding='utf-8') as f:
    f.write(content)
