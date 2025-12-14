# Fix highlight undo - save highlighted rows and clear colors on undo

# 1. Fix sidebar.js - save highlighted rows in snapshot
sidebar_path = 'C:/Projects/SheetGPT/chrome-extension/src/sidebar.js'
with open(sidebar_path, 'r', encoding='utf-8') as f:
    sidebar = f.read()

# Update saveSheetSnapshot to accept extra data
old_sidebar1 = '''async function saveSheetSnapshot(actionName) {
  try {
    console.log('[Sidebar] 📸 Saving snapshot before:', actionName);
    const response = await sendToContentScript('GET_SHEET_DATA_FOR_UNDO', {});
    if (response && response.success && response.data) {
      undoSnapshot = response.data;
      undoActionName = actionName;'''

new_sidebar1 = '''async function saveSheetSnapshot(actionName, extraData = null) {
  try {
    console.log('[Sidebar] 📸 Saving snapshot before:', actionName);
    const response = await sendToContentScript('GET_SHEET_DATA_FOR_UNDO', {});
    if (response && response.success && response.data) {
      undoSnapshot = response.data;
      // Save extra data (e.g., highlighted rows for undo)
      if (extraData) {
        undoSnapshot.extraData = extraData;
      }
      undoActionName = actionName;'''

if old_sidebar1 in sidebar:
    sidebar = sidebar.replace(old_sidebar1, new_sidebar1)
    print('SUCCESS 1: Updated saveSheetSnapshot')
else:
    print('ERROR 1: saveSheetSnapshot pattern not found')

# Update undoLastAction to handle highlight undo
old_sidebar2 = '''async function undoLastAction() {
  if (!undoSnapshot) {
    console.log('[Sidebar] ⚠️ Nothing to undo');
    return;
  }

  try {
    console.log('[Sidebar] ↩️ Restoring snapshot...');
    const response = await sendToContentScript('RESTORE_SHEET_DATA', {
      data: undoSnapshot
    });'''

new_sidebar2 = '''async function undoLastAction() {
  if (!undoSnapshot) {
    console.log('[Sidebar] ⚠️ Nothing to undo');
    return;
  }

  try {
    console.log('[Sidebar] ↩️ Restoring snapshot...');

    let response;

    // For highlight actions, just clear the colors instead of restoring all data
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
    }'''

if old_sidebar2 in sidebar:
    sidebar = sidebar.replace(old_sidebar2, new_sidebar2)
    print('SUCCESS 2: Updated undoLastAction')
else:
    print('ERROR 2: undoLastAction pattern not found')

with open(sidebar_path, 'w', encoding='utf-8') as f:
    f.write(sidebar)

# 2. Update highlight call to pass rows to snapshot
# Find where highlight saves snapshot and passes rows
old_sidebar3 = '''    await saveSheetSnapshot('Выделение строк');'''
# Need to find the context where this is called with rows available

# Actually, let's search for the actual highlight handling code
print('Searching for highlight handling...')
if 'HIGHLIGHT_ROWS' in sidebar:
    print('Found HIGHLIGHT_ROWS usage')
