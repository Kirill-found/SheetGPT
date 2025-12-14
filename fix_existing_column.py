# Add logic to use existing column if it has the same name
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/content.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''    // Determine target column
    let targetColLetter;
    if (targetColumn) {
      // Use specified column
      targetColLetter = targetColumn.toUpperCase();
      console.log('[SheetGPT] Using specified target column:', targetColLetter);
    } else {
      // Find next empty column index (after last column with data)
      const numCols = sheetData.result.headers.length;
      const nextColIndex = numCols; // 0-indexed, so this is the first empty column
      targetColLetter = String.fromCharCode(65 + nextColIndex); // A=0, B=1, etc.
      console.log('[SheetGPT] Using next empty column:', targetColLetter, 'index:', nextColIndex);
    }'''

new_code = '''    // Determine target column
    let targetColLetter;
    let skipHeader = false; // If using existing column, don't overwrite header

    if (targetColumn) {
      // Use specified column
      targetColLetter = targetColumn.toUpperCase();
      console.log('[SheetGPT] Using specified target column:', targetColLetter);
    } else {
      // Check if column with same name already exists
      const headers = sheetData.result.headers;
      const existingColIndex = headers.findIndex(h =>
        h && h.toString().toLowerCase().trim() === columnName.toLowerCase().trim()
      );

      if (existingColIndex >= 0) {
        // Use existing column
        targetColLetter = String.fromCharCode(65 + existingColIndex);
        skipHeader = true; // Don't overwrite existing header
        console.log('[SheetGPT] Found existing column "' + columnName + '" at:', targetColLetter);
      } else {
        // Find next empty column index (after last column with data)
        const numCols = headers.length;
        const nextColIndex = numCols; // 0-indexed, so this is the first empty column
        targetColLetter = String.fromCharCode(65 + nextColIndex); // A=0, B=1, etc.
        console.log('[SheetGPT] Using next empty column:', targetColLetter, 'index:', nextColIndex);
      }
    }'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print('SUCCESS: Added existing column check')
else:
    print('ERROR: Pattern not found')

# Also update the formulas array creation to handle skipHeader
old_formulas = '''    // Build formula values array:
    // Row 1 = header (columnName)
    // Row 2+ = formulas with row numbers replaced
    const formulas = [[columnName]]; // Header
    const actualRowCount = rowCount || sheetData.result?.data?.length || 100;

    for (let i = 2; i <= actualRowCount + 1; i++) {
      // Replace {row} placeholder with actual row number
      const formula = formulaTemplate.replace(/\\{row\\}/g, i.toString());
      formulas.push([formula]);
    }'''

new_formulas = '''    // Build formula values array:
    // Row 1 = header (columnName) - skip if using existing column
    // Row 2+ = formulas with row numbers replaced
    const formulas = skipHeader ? [] : [[columnName]]; // Header only if new column
    const actualRowCount = rowCount || sheetData.result?.data?.length || 100;
    const startRow = skipHeader ? 2 : 2; // Always start formulas from row 2

    for (let i = startRow; i <= actualRowCount + 1; i++) {
      // Replace {row} placeholder with actual row number
      const formula = formulaTemplate.replace(/\\{row\\}/g, i.toString());
      formulas.push([formula]);
    }'''

if old_formulas in content:
    content = content.replace(old_formulas, new_formulas)
    print('SUCCESS: Updated formulas array')
else:
    print('ERROR: Formulas pattern not found')

# Update the startCell to handle skipHeader
old_start = "startCell: `${targetColLetter}1`,"
new_start = "startCell: skipHeader ? `${targetColLetter}2` : `${targetColLetter}1`,"

if old_start in content:
    content = content.replace(old_start, new_start)
    print('SUCCESS: Updated startCell')
else:
    print('ERROR: startCell not found')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
