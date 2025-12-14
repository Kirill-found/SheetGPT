# Fix highlightRowsInSheet to pass rows to snapshot
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/sidebar.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """// Highlight rows in the sheet
async function highlightRowsInSheet(rows, color) {
  if (!rows || rows.length === 0) return;

  try {
    await saveSheetSnapshot('Выделение строк');
    await sendToContentScript('HIGHLIGHT_ROWS', { rows: rows, color: color });
    console.log('[Sidebar] Rows highlighted:', rows, 'with color:', color);
  } catch (error) {
    console.error('[Sidebar] Error highlighting rows:', error);
  }
}"""

new = """// Highlight rows in the sheet
async function highlightRowsInSheet(rows, color) {
  if (!rows || rows.length === 0) return;

  try {
    // Pass highlighted rows to snapshot for proper undo (clear colors, not restore data)
    await saveSheetSnapshot('Выделение строк', { highlightedRows: rows });
    await sendToContentScript('HIGHLIGHT_ROWS', { rows: rows, color: color });
    console.log('[Sidebar] Rows highlighted:', rows, 'with color:', color);
  } catch (error) {
    console.error('[Sidebar] Error highlighting rows:', error);
  }
}"""

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Updated highlightRowsInSheet')
else:
    print('ERROR: Pattern not found')
