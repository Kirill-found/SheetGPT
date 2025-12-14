# Add CLEAR_ROW_COLORS handler in background.js
file_path = 'C:/Projects/SheetGPT/chrome-extension/src/background.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add case after HIGHLIGHT_ROWS
old = """        case 'HIGHLIGHT_ROWS':
          result = await handleHighlightRows(sender.tab.id, sender.tab.url, data);
          break;

        case 'SORT_RANGE':"""

new = """        case 'HIGHLIGHT_ROWS':
          result = await handleHighlightRows(sender.tab.id, sender.tab.url, data);
          break;

        case 'CLEAR_ROW_COLORS':
          result = await handleClearRowColors(sender.tab.id, sender.tab.url, data);
          break;

        case 'SORT_RANGE':"""

if old in content:
    content = content.replace(old, new)
    print('SUCCESS 1: Added CLEAR_ROW_COLORS case')
else:
    print('ERROR 1: Case pattern not found')

# Now add the handler function after handleHighlightRows
# Find handleHighlightRows function end
if 'async function handleHighlightRows' in content:
    print('Found handleHighlightRows function')

    # Add the handler function - find a good place
    # Let's add after the closing of handleHighlightRows
    old_func = """background.js:376 [Background] ✅ Rows highlighted"""

    # Actually, let's just add it before a known function
    old_func2 = """// Sort a range in the sheet
async function handleSortRange"""

    new_func2 = """// Clear row background colors (for undo highlight)
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

// Sort a range in the sheet
async function handleSortRange"""

    if old_func2 in content:
        content = content.replace(old_func2, new_func2)
        print('SUCCESS 2: Added handleClearRowColors function')
    else:
        print('ERROR 2: Function pattern not found')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
