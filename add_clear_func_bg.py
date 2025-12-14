# Add handleClearRowColors function in background.js
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/background.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """}

/**
 * Sort data in Google Sheet by column
 */
async function handleSortRange(tabId, tabUrl, data) {"""

new = """}

/**
 * Clear row background colors (for undo highlight)
 */
async function handleClearRowColors(tabId, tabUrl, data) {
  console.log('[Background] Clearing row colors:', data);

  const match = tabUrl.match(/\\/spreadsheets\\/d\\/([a-zA-Z0-9-_]+)/);
  if (!match) {
    throw new Error('Could not get spreadsheet ID from URL');
  }
  const spreadsheetId = match[1];

  const { sheetName, rowIndices } = data;

  // Get stored sheet name or use provided
  const storageKey = `sheetName_${spreadsheetId}`;
  const storage = await chrome.storage.local.get([storageKey]);
  const actualSheetName = storage[storageKey] || sheetName || 'Sheet1';
  console.log('[Background] Using sheet name "' + actualSheetName + '" for clearing colors');

  // Clear colors using Sheets API
  const result = await SheetsAPI.clearRowBackgrounds(spreadsheetId, actualSheetName, rowIndices);
  console.log('[Background] ✅ Row colors cleared:', result);
  return result;
}

/**
 * Sort data in Google Sheet by column
 */
async function handleSortRange(tabId, tabUrl, data) {"""

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added handleClearRowColors function')
else:
    print('ERROR: Pattern not found')
