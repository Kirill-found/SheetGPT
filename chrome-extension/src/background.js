/**
 * SheetGPT Chrome Extension - Background Service Worker
 * Handles OAuth and Sheets API operations
 */

// Import Sheets API module (path relative to current directory)
importScripts('sheets-api.js');

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

        case 'SORT_RANGE':
          result = await handleSortRange(sender.tab.id, sender.tab.url, data);
          break;

        case 'FREEZE_ROWS':
          result = await handleFreezeRows(sender.tab.id, sender.tab.url, data);
          break;

        case 'FORMAT_ROW':
          result = await handleFormatRow(sender.tab.id, sender.tab.url, data);
          break;

        case 'CREATE_CHART':
          result = await handleCreateChart(sender.tab.id, sender.tab.url, data);
          break;

        case 'APPLY_CONDITIONAL_FORMAT':
          result = await handleConditionalFormat(sender.tab.id, sender.tab.url, data);
          break;

        case 'APPLY_COLOR_SCALE':
          console.log('[Background] 🎨 APPLY_COLOR_SCALE received:', data);
          result = await handleColorScale(sender.tab.id, sender.tab.url, data);
          break;

        case 'SET_DATA_VALIDATION':
          result = await handleSetDataValidation(sender.tab.id, sender.tab.url, data);
          break;

        case 'CONVERT_TO_NUMBERS':
          console.log('[Background] 🔢 CONVERT_TO_NUMBERS received:', data);
          result = await handleConvertToNumbers(sender.tab.id, sender.tab.url, data);
          break;

        case 'GET_REFERENCE_SHEET_DATA':
          console.log('[Background] 📋 GET_REFERENCE_SHEET_DATA received:', message.sheetNameHint);
          result = await handleGetReferenceSheetData(sender.tab?.id, sender.tab?.url, message.sheetNameHint);
          break;

        case 'CHECK_AUTH':
          result = await checkAuth();
          break;

        case 'FORCE_REAUTH':
          // v7.9.4: Force re-authentication by removing cached token
          result = await forceReauth();
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

  try {
    // v9.2.1: Get all sheet names from API first (more reliable than DOM scraping)
    console.log('[Background] 📋 Getting all sheet names from API...');
    const allSheetNames = await withTimeout(
      getAllSheetNames(spreadsheetId),
      5000,
      'Get all sheet names'
    );
    console.log('[Background] Available sheets:', allSheetNames);

    // Get active sheet name from DOM
    console.log('[Background] 🎯 Getting ACTIVE sheet name from DOM...');
    const domSheetName = await withTimeout(
      getActiveSheetName(tabId),
      5000,
      'Get active sheet name'
    );
    console.log(`[Background] DOM sheet name: "${domSheetName}"`);

    // Find matching sheet name from API (exact or partial match)
    let activeSheetName = allSheetNames.find(s => s === domSheetName);
    if (!activeSheetName) {
      // Try case-insensitive match
      activeSheetName = allSheetNames.find(s => s.toLowerCase() === domSheetName.toLowerCase());
    }
    if (!activeSheetName) {
      // Try partial match
      activeSheetName = allSheetNames.find(s => s.includes(domSheetName) || domSheetName.includes(s));
    }
    if (!activeSheetName && allSheetNames.length > 0) {
      // Fallback to first sheet
      activeSheetName = allSheetNames[0];
      console.log(`[Background] ⚠️ Using fallback sheet: "${activeSheetName}"`);
    }
    
    console.log(`[Background] ✅ Active sheet: "${activeSheetName}"`);

    // Читаем данные из активного листа
    console.log(`[Background] 📖 Reading data from sheet: "${activeSheetName}"...`);
    const data = await withTimeout(
      readSheetData(spreadsheetId, activeSheetName),
      8000,
      `Read sheet data "${activeSheetName}"`
    );

    // Проверяем что данные не пустые
    if (!data.headers || data.headers.length === 0 || !data.data || data.data.length === 0) {
      throw new Error(`Active sheet "${activeSheetName}" is empty or has no data`);
    }

    console.log(`[Background] ✅ Got data from "${activeSheetName}":`, {
      headers: data.headers,
      rows: data.data.length
    });

    // Save successful sheet name for later use (e.g., highlighting)
    await chrome.storage.local.set({
      [`sheetName_${spreadsheetId}`]: activeSheetName
    });
    console.log(`[Background] 💾 Saved sheet name "${activeSheetName}" for spreadsheet ${spreadsheetId}`);

    return data;

  } catch (error) {
    console.error('[Background] ❌ Error getting sheet data:', error);
    throw error;
  }
}

/**
 * Get reference sheet data for VLOOKUP (v9.2.0)
 * Finds sheet by name hint and returns its data
 */
async function handleGetReferenceSheetData(tabId, tabUrl, sheetNameHint) {
  console.log('[Background] Getting reference sheet data, hint:', sheetNameHint);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  try {
    // Get all sheet names from API
    console.log('[Background] 📋 Getting all sheet names...');
    const allSheetNames = await withTimeout(
      getAllSheetNames(spreadsheetId),
      5000,
      'Get all sheet names'
    );
    console.log('[Background] Available sheets:', allSheetNames);

    // Find matching sheet by hint
    let targetSheetName = null;
    const lowerHint = sheetNameHint.toLowerCase();

    // 1. Exact match (case-insensitive)
    targetSheetName = allSheetNames.find(s => s.toLowerCase() === lowerHint);

    // 2. Contains match (case-insensitive)
    if (!targetSheetName) {
      targetSheetName = allSheetNames.find(s =>
        s.toLowerCase().includes(lowerHint) || lowerHint.includes(s.toLowerCase())
      );
    }

    // 3. Keyword match (прайс, справочник, price, etc.)
    if (!targetSheetName) {
      const refKeywords = ['прайс', 'справочник', 'каталог', 'price', 'catalog', 'reference', 'lookup'];
      targetSheetName = allSheetNames.find(s => {
        const lowerName = s.toLowerCase();
        return refKeywords.some(keyword => lowerName.includes(keyword));
      });
    }

    if (!targetSheetName) {
      throw new Error(`Could not find reference sheet matching "${sheetNameHint}". Available: ${allSheetNames.join(', ')}`);
    }

    console.log(`[Background] ✅ Found reference sheet: "${targetSheetName}"`);

    // Read data from reference sheet
    console.log(`[Background] 📖 Reading reference data from "${targetSheetName}"...`);
    const data = await withTimeout(
      readSheetData(spreadsheetId, targetSheetName),
      8000,
      `Read reference sheet "${targetSheetName}"`
    );

    if (!data.headers || data.headers.length === 0 || !data.data || data.data.length === 0) {
      throw new Error(`Reference sheet "${targetSheetName}" is empty or has no data`);
    }

    console.log(`[Background] ✅ Got reference data from "${targetSheetName}":`, {
      headers: data.headers,
      rows: data.data.length
    });

    return {
      sheetName: targetSheetName,
      headers: data.headers,
      data: data.data
    };

  } catch (error) {
    console.error('[Background] ❌ Error getting reference sheet data:', error);
    throw error;
  }
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
  console.log('[Background] Creating new sheet, received data:', JSON.stringify(data, null, 2));
  console.log('[Background] data.sheetTitle:', data?.sheetTitle);
  console.log('[Background] data.values:', data?.values);
  console.log('[Background] data.values length:', data?.values?.length);
  console.log('[Background] data.values[0] (headers):', data?.values?.[0]);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { sheetTitle, values } = data;

  // v9.0.2: Validate values before creating sheet
  if (!values || !Array.isArray(values)) {
    console.error('[Background] ❌ ERROR: values is not an array!', values);
    throw new Error('Invalid data: values must be an array');
  }

  if (values.length === 0) {
    console.error('[Background] ❌ ERROR: values array is empty!');
    throw new Error('Invalid data: values array is empty');
  }

  console.log('[Background] ✅ Validated values:', values.length, 'rows');

  // Create new sheet
  const sheetProperties = await createNewSheet(spreadsheetId, sheetTitle);
  console.log('[Background] ✅ Sheet created:', sheetProperties);

  // Write data to new sheet
  await writeSheetData(spreadsheetId, sheetTitle, values, 'A1');
  console.log('[Background] ✅ Data written to new sheet:', values.length, 'rows');

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

  const { rowIndices, color } = data;

  // Get saved sheet name from storage (saved by handleGetSheetData)
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1'; // Fallback to Russian default

  console.log(`[Background] Using sheet name "${sheetName}" for highlighting`);

  // Get sheet ID
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);

  // Highlight rows
  const result = await highlightRows(spreadsheetId, sheetId, rowIndices, color);

  console.log('[Background] ✅ Rows highlighted:', result);
  return result;
}

/**
 * Sort data in Google Sheet by column
 */
async function handleSortRange(tabId, tabUrl, data) {
  console.log('[Background] Sorting range:', data);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { columnIndex, sortOrder } = data;

  // Get saved sheet name from storage (saved by handleGetSheetData)
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1'; // Fallback to Russian default

  console.log(`[Background] Using sheet name "${sheetName}" for sorting`);

  // Get sheet ID
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);

  // Sort range (start from row 1 to skip header)
  const result = await sortRange(spreadsheetId, sheetId, columnIndex, sortOrder, 1, -1);

  console.log('[Background] ✅ Range sorted:', result);
  return result;
}

/**
 * Freeze rows/columns in Google Sheet
 */
async function handleFreezeRows(tabId, tabUrl, data) {
  console.log('[Background] Freezing rows/columns:', data);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { freezeRows, freezeColumns } = data;

  // Get saved sheet name from storage
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1';

  console.log(`[Background] Using sheet name "${sheetName}" for freezing`);

  // Get sheet ID
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);

  // Freeze rows/columns
  const result = await freezeRowsColumns(spreadsheetId, sheetId, freezeRows || 0, freezeColumns || 0);

  console.log('[Background] ✅ Rows/columns frozen:', result);
  return result;
}

/**
 * Format row in Google Sheet (bold, color)
 */
async function handleFormatRow(tabId, tabUrl, data) {
  console.log('[Background] Formatting row:', data);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { rowIndex, bold, backgroundColor } = data;

  // Get saved sheet name from storage
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1';

  console.log(`[Background] Using sheet name "${sheetName}" for formatting`);

  // Get sheet ID
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);

  // Format row
  const result = await formatRow(spreadsheetId, sheetId, rowIndex || 0, bold, backgroundColor);

  console.log('[Background] ✅ Row formatted:', result);
  return result;
}

/**
 * Create a chart in Google Sheet
 */
async function handleCreateChart(tabId, tabUrl, data) {
  console.log('[Background] 📊 Creating chart, data:', JSON.stringify(data));

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  console.log('[Background] 📊 Spreadsheet ID:', spreadsheetId);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { chartSpec } = data;

  if (!chartSpec) {
    throw new Error('Chart specification is required');
  }

  // Get saved sheet name from storage
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1';

  console.log(`[Background] 📊 Using sheet name "${sheetName}" for chart (storageKey: ${storageKey})`);

  // Get sheet ID
  console.log('[Background] 📊 Getting sheet ID...');
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);
  console.log('[Background] 📊 Sheet ID:', sheetId);

  // Create chart
  console.log('[Background] 📊 Calling createChart API...');
  const result = await createChart(spreadsheetId, sheetId, chartSpec);

  console.log('[Background] ✅ Chart created successfully:', result);
  return result;
}

/**
 * Apply conditional formatting to Google Sheet
 */
async function handleConditionalFormat(tabId, tabUrl, data) {
  console.log('[Background] Applying conditional format:', data);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { rule } = data;

  if (!rule) {
    throw new Error('Conditional format rule is required');
  }

  // Get saved sheet name from storage
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1';

  console.log(`[Background] Using sheet name "${sheetName}" for conditional format`);

  // Get sheet ID
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);

  // Apply conditional format
  const result = await applyConditionalFormat(spreadsheetId, sheetId, rule);

  console.log('[Background] ✅ Conditional format applied:', result);
  return result;
}

/**
 * Apply color scale (gradient) formatting to Google Sheet
 */
async function handleColorScale(tabId, tabUrl, data) {
  console.log('[Background] 🎨 Applying color scale:', data);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { rule } = data;

  if (!rule) {
    throw new Error('Color scale rule is required');
  }

  // Get saved sheet name from storage
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1';

  console.log(`[Background] Using sheet name "${sheetName}" for color scale`);

  // Get sheet ID
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);

  // Apply color scale
  const result = await applyColorScale(spreadsheetId, sheetId, rule);

  console.log('[Background] ✅ Color scale applied:', result);
  return result;
}

/**
 * Set data validation (dropdown list) for a column
 */
async function handleSetDataValidation(tabId, tabUrl, data) {
  console.log('[Background] Setting data validation:', data);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { rule } = data;

  if (!rule) {
    throw new Error('Data validation rule is required');
  }

  // Get saved sheet name from storage
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1';

  console.log(`[Background] Using sheet name "${sheetName}" for data validation`);

  // Get sheet ID
  const sheetId = await getSheetIdByName(spreadsheetId, sheetName);

  // Set data validation
  const result = await setDataValidation(spreadsheetId, sheetId, rule);

  console.log('[Background] ✅ Data validation set:', result);
  return result;
}

/**
 * Convert column from text to numbers
 */
async function handleConvertToNumbers(tabId, tabUrl, data) {
  console.log('[Background] 🔢 Converting column to numbers:', data);

  const spreadsheetId = getSpreadsheetIdFromUrl(tabUrl);
  if (!spreadsheetId) {
    throw new Error('Not a valid Google Sheets URL');
  }

  const { columnIndex, rowCount } = data;

  if (columnIndex === undefined) {
    throw new Error('Column index is required');
  }

  // Get saved sheet name from storage
  const storageKey = `sheetName_${spreadsheetId}`;
  const storageData = await chrome.storage.local.get(storageKey);
  const sheetName = storageData[storageKey] || 'Лист1';

  console.log(`[Background] Using sheet name "${sheetName}" for number conversion`);

  // Convert column
  const result = await convertColumnToNumbers(spreadsheetId, sheetName, columnIndex, rowCount || 1000);

  console.log('[Background] ✅ Column converted to numbers:', result);
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

/**
 * v7.9.4: Force re-authentication by clearing cached tokens
 */
async function forceReauth() {
  console.log('[Background] Force re-authentication requested');

  return new Promise((resolve, reject) => {
    // First get the current token (non-interactive)
    chrome.identity.getAuthToken({ interactive: false }, (token) => {
      if (token) {
        console.log('[Background] Removing cached token...');
        // Remove the cached token
        chrome.identity.removeCachedAuthToken({ token }, () => {
          console.log('[Background] Token removed, requesting new auth...');
          // Now get a new token interactively
          chrome.identity.getAuthToken({ interactive: true }, (newToken) => {
            if (chrome.runtime.lastError) {
              console.error('[Background] Re-auth failed:', chrome.runtime.lastError);
              reject(new Error(chrome.runtime.lastError.message));
            } else if (newToken) {
              console.log('[Background] ✅ Re-authentication successful');
              resolve({ success: true, message: 'Авторизация обновлена' });
            } else {
              reject(new Error('Не удалось получить новый токен'));
            }
          });
        });
      } else {
        // No cached token, just get a new one
        console.log('[Background] No cached token, requesting new auth...');
        chrome.identity.getAuthToken({ interactive: true }, (newToken) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else if (newToken) {
            console.log('[Background] ✅ Authentication successful');
            resolve({ success: true, message: 'Авторизация выполнена' });
          } else {
            reject(new Error('Не удалось получить токен'));
          }
        });
      }
    });
  });
}
