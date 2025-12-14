# Add CLEAR_ROW_COLORS handler in content.js
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/content.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """      case 'ADD_FORMULA_COLUMN':
        console.log('[SheetGPT] ➕ ADD_FORMULA_COLUMN - adding column:', data.columnName, 'formula:', data.formulaTemplate);
        result = await addFormulaColumn(data.columnName, data.formulaTemplate, data.rowCount);
        break;

      default:
        throw new Error(`Unknown action: ${action}`);"""

new = """      case 'ADD_FORMULA_COLUMN':
        console.log('[SheetGPT] ➕ ADD_FORMULA_COLUMN - adding column:', data.columnName, 'formula:', data.formulaTemplate);
        result = await addFormulaColumn(data.columnName, data.formulaTemplate, data.rowCount);
        break;

      case 'CLEAR_ROW_COLORS':
        console.log('[SheetGPT] ↩️ CLEAR_ROW_COLORS - clearing highlight from rows:', data.rows);
        result = await clearRowColors(data.rows, data.sheetName);
        break;

      default:
        throw new Error(`Unknown action: ${action}`);"""

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added CLEAR_ROW_COLORS case')
else:
    print('ERROR: Pattern not found')
