/**
 * SheetGPT Chrome Extension - Background Service Worker
 * Handles OAuth and Sheets API operations
 */

// Import Sheets API module (path relative to extension root)
importScripts('src/sheets-api.js');

console.log('[Background] Service worker started');

// Handle extension installation
chrome.runtime.onInstalled.addListener((details) => {
  console.log('[Background] Extension installed:', details.reason);

  if (details.reason === 'install') {
    // First installation - show welcome message
    console.log('[Background] Welcome to SheetGPT! Please configure OAuth in manifest.json');
  }
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[Background] Message received:', message);

  const { action, data } = message;

  // Handle async operations
  (async () => {
    try {
      let result;

      switch (action) {
        case 'GET_SHEET_DATA':
          result = await handleGetSheetData(sender.tab.id, sender.tab.url);
          break;

        case 'WRITE_SHEET_DATA':
          result = await handleWriteSheetData(sender.tab.id, sender.tab.url, data);
          break;

        case 'CREATE_NEW_SHEET':
          result = await handleCreateNewSheet(sender.tab.id, sender.tab.url, data);
          break;

        case 'HIGHLIGHT_ROWS':
          result = await handleHighlightRows(sender.tab.id, sender.tab.url, data);
          break;

        case 'CHECK_AUTH':
          result = await checkAuth();
          break;

        default:
          throw new Error(`Unknown action: ${action}`);
      }

      sendResponse({ success: true, result });
    } catch (error) {
      console.error('[Background] Error handling message:', error);
      sendResponse({ success: false, error: error.message });
    }
  })();

  return true; // Keep message channel open for async response
});

/**
 * Timeout wrapper for async operations
 */
function withTimeout(promise, timeoutMs, operationName) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`${operationName} timeout after ${timeoutMs/1000}s. OAuth authorization may be required. Please check chrome://extensions and reload the extension.`)), timeoutMs)
    )
  ]);
}

/**
 * Get data from active Google Sheet
 */
async function handleGetSheetData(tabId, tabUrl) {
  console.log('[Background] Getting sheet data from tab:', tabId);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  // Try to get sheet name with short timeout, use fallback if fails
  let sheetName = 'Лист1'; // Russian Google Sheets default
  try {
    sheetName = await withTimeout(
      getActiveSheetName(tabId),
      2000, // Very short timeout to avoid hanging
      'Get sheet name'
    );
    console.log('[Background] Got sheet name:', sheetName);
  } catch (error) {
    console.warn('[Background] Could not get sheet name, using fallback:', sheetName, error.message);
  }

  // Try to read data, fallback to 'Sheet1' if Russian name fails
  let data;
  try {
    data = await withTimeout(
      readSheetData(spreadsheetId, sheetName),
      10000,
      'Read sheet data'
    );
  } catch (error) {
    console.warn(`[Background] Failed with "${sheetName}", trying "Sheet1"...`, error.message);
    data = await withTimeout(
      readSheetData(spreadsheetId, 'Sheet1'),
      10000,
      'Read sheet data (Sheet1 fallback)'
    );
  }

  console.log('[Background] ✅ Got sheet data:', data);
  return data;
}

/**
 * Write data to Google Sheet
 */
async function handleWriteSheetData(tabId, tabUrl, data) {
  console.log('[Background] Writing sheet data:', data);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { sheetName, values, startCell, mode } = data;

  let result;
  if (mode === 'append') {
    result = await appendSheetData(spreadsheetId, sheetName, values);
  } else if (mode === 'overwrite') {
    result = await writeSheetData(spreadsheetId, sheetName, values, startCell);
  } else {
    throw new Error(`Unknown write mode: ${mode}`);
  }

  console.log('[Background] ✅ Data written:', result);
  return result;
}

/**
 * Create a new sheet and write data
 */
async function handleCreateNewSheet(tabId, tabUrl, data) {
  console.log('[Background] Creating new sheet:', data);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { sheetTitle, values } = data;

  // Create new sheet
  const sheetProperties = await createNewSheet(spreadsheetId, sheetTitle);
  console.log('[Background] ✅ Sheet created:', sheetProperties);

  // Write data to new sheet
  await writeSheetData(spreadsheetId, sheetTitle, values, 'A1');
  console.log('[Background] ✅ Data written to new sheet');

  return { sheetProperties, rowsWritten: values.length };
}

/**
 * Highlight rows in Google Sheet
 */
async function handleHighlightRows(tabId, tabUrl, data) {
  console.log('[Background] Highlighting rows:', data);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { sheetName, rowIndices, color } = data;

  // Get sheet ID
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);

  // Highlight rows
  const result = await highlightRows(spreadsheetId, sheetId, rowIndices, color);

  console.log('[Background] ✅ Rows highlighted:', result);
  return result;
}

/**
 * Check if user is authenticated
 */
async function checkAuth() {
  try {
    await getAuthToken();
    return { authenticated: true };
  } catch (error) {
    return { authenticated: false, error: error.message };
  }
}
