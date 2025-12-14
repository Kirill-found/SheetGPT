# Fix undo for add_formula - delete column instead of restoring data

sidebar_path = 'C:/Projects/SheetGPT/chrome-extension/src/sidebar.js'
with open(sidebar_path, 'r', encoding='utf-8') as f:
    sidebar = f.read()

# 1. Update addFormulaColumn to save the added column in snapshot
old1 = """  try {
    await saveSheetSnapshot('Добавление столбца с формулой');
    console.log(`[Sidebar] Adding formula column "${columnName}" with template: ${formulaTemplate}`);
    const response = await sendToContentScript('ADD_FORMULA_COLUMN', {
      columnName: columnName || 'Итого',
      formulaTemplate: formulaTemplate,
      rowCount: rowCount || 100
    });
    console.log(`[Sidebar] Formula column added:`, response);
    return response;"""

new1 = """  try {
    console.log(`[Sidebar] Adding formula column "${columnName}" with template: ${formulaTemplate}`);
    const response = await sendToContentScript('ADD_FORMULA_COLUMN', {
      columnName: columnName || 'Итого',
      formulaTemplate: formulaTemplate,
      rowCount: rowCount || 100
    });
    console.log(`[Sidebar] Formula column added:`, response);

    // Save snapshot AFTER adding column, so we know which column was added
    if (response?.column) {
      await saveSheetSnapshot('Добавление столбца с формулой', { addedColumn: response.column });
    }

    return response;"""

if old1 in sidebar:
    sidebar = sidebar.replace(old1, new1)
    print('SUCCESS 1: Updated addFormulaColumn')
else:
    print('ERROR 1: addFormulaColumn pattern not found')

# 2. Update undoLastAction to handle addedColumn
old2 = """    // For highlight actions, just clear the colors instead of restoring all data
    if (undoSnapshot.extraData?.highlightedRows) {
      console.log('[Sidebar] ↩️ Clearing highlight colors from rows:', undoSnapshot.extraData.highlightedRows);
      response = await sendToContentScript('CLEAR_ROW_COLORS', {
        rows: undoSnapshot.extraData.highlightedRows,
        sheetName: undoSnapshot.sheetName
      });
    } else {
      // For other actions, restore the full data
      response = await sendToContentScript('RESTORE_SHEET_DATA', {
        data: undoSnapshot
      });
    }"""

new2 = """    // For highlight actions, just clear the colors instead of restoring all data
    if (undoSnapshot.extraData?.highlightedRows) {
      console.log('[Sidebar] ↩️ Clearing highlight colors from rows:', undoSnapshot.extraData.highlightedRows);
      response = await sendToContentScript('CLEAR_ROW_COLORS', {
        rows: undoSnapshot.extraData.highlightedRows,
        sheetName: undoSnapshot.sheetName
      });
    } else if (undoSnapshot.extraData?.addedColumn) {
      // For add_formula actions, delete the added column
      console.log('[Sidebar] ↩️ Deleting added column:', undoSnapshot.extraData.addedColumn);
      response = await sendToContentScript('DELETE_COLUMN', {
        column: undoSnapshot.extraData.addedColumn,
        sheetName: undoSnapshot.sheetName
      });
    } else {
      // For other actions, restore the full data
      response = await sendToContentScript('RESTORE_SHEET_DATA', {
        data: undoSnapshot
      });
    }"""

if old2 in sidebar:
    sidebar = sidebar.replace(old2, new2)
    print('SUCCESS 2: Updated undoLastAction')
else:
    print('ERROR 2: undoLastAction pattern not found')

with open(sidebar_path, 'w', encoding='utf-8') as f:
    f.write(sidebar)
