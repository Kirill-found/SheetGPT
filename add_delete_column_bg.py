# Add DELETE_COLUMN handler in background.js
bg_path = 'C:/Projects/SheetGPT/chrome-extension/src/background.js'
with open(bg_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add case
old1 = """        case 'CLEAR_ROW_COLORS':
          result = await handleClearRowColors(sender.tab.id, sender.tab.url, data);
          break;

        case 'SORT_RANGE':"""

new1 = """        case 'CLEAR_ROW_COLORS':
          result = await handleClearRowColors(sender.tab.id, sender.tab.url, data);
          break;

        case 'DELETE_COLUMN':
          result = await handleDeleteColumn(sender.tab.id, sender.tab.url, data);
          break;

        case 'SORT_RANGE':"""

if old1 in content:
    content = content.replace(old1, new1)
    print('SUCCESS 1: Added DELETE_COLUMN case')
else:
    print('ERROR 1: Case pattern not found')

# Add handler function
old2 = """/**
 * Sort data in Google Sheet by column
 */
async function handleSortRange(tabId, tabUrl, data) {"""

new2 = """/**
 * Delete a column from the sheet
 */
async function handleDeleteColumn(tabId, tabUrl, data) {
  console.log('[Background] Deleting column:', data);

  const match = tabUrl.match(/\\/spreadsheets\\/d\\/([a-zA-Z0-9-_]+)/);
  if (!match) {
    throw new Error('Could not get spreadsheet ID from URL');
  }
  const spreadsheetId = match[1];

  const { sheetName, column } = data;

  // Get stored sheet name or use provided
  const storageKey = `sheetName_${spreadsheetId}`;
  const storage = await chrome.storage.local.get([storageKey]);
  const actualSheetName = storage[storageKey] || sheetName || 'Sheet1';
  console.log('[Background] Using sheet name "' + actualSheetName + '" for deleting column');

  // Delete column using Sheets API
  const result = await deleteColumn(spreadsheetId, actualSheetName, column);
  console.log('[Background] ✅ Column deleted:', result);
  return result;
}

/**
 * Sort data in Google Sheet by column
 */
async function handleSortRange(tabId, tabUrl, data) {"""

if old2 in content:
    content = content.replace(old2, new2)
    print('SUCCESS 2: Added handleDeleteColumn function')
else:
    print('ERROR 2: Function pattern not found')

with open(bg_path, 'w', encoding='utf-8') as f:
    f.write(content)
