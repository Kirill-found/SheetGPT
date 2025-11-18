/**
 * Google Sheets API Integration
 * Handles OAuth and all Sheets API operations
 */

const SHEETS_API_BASE = 'https://sheets.googleapis.com/v4/spreadsheets';

/**
 * Get OAuth token for Google Sheets API
 */
async function getAuthToken() {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive: true }, (token) => {
      if (chrome.runtime.lastError) {
        console.error('[SheetsAPI] Auth error:', chrome.runtime.lastError);
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        console.log('[SheetsAPI] ✅ Got auth token');
        resolve(token);
      }
    });
  });
}

/**
 * Extract spreadsheet ID from URL
 */
function getSpreadsheetIdFromUrl(url) {
  const match = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
  return match ? match[1] : null;
}

/**
 * Get active sheet name from Google Sheets page
 */
async function getActiveSheetName(tabId) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => {
        // Try multiple methods to find active sheet name

        // Method 1: aria-selected="true"
        let activeTab = document.querySelector('.docs-sheet-tab-name[aria-selected="true"]');
        if (activeTab) {
          console.log('[GetSheetName] Found via aria-selected:', activeTab.textContent.trim());
          return activeTab.textContent.trim();
        }

        // Method 2: .docs-sheet-active-tab
        activeTab = document.querySelector('.docs-sheet-active-tab .docs-sheet-tab-name');
        if (activeTab) {
          console.log('[GetSheetName] Found via active-tab class:', activeTab.textContent.trim());
          return activeTab.textContent.trim();
        }

        // Method 3: Look for selected sheet in tab bar
        const tabs = document.querySelectorAll('.docs-sheet-tab');
        for (const tab of tabs) {
          if (tab.classList.contains('docs-sheet-active-tab') || tab.getAttribute('aria-selected') === 'true') {
            const nameEl = tab.querySelector('.docs-sheet-tab-name');
            if (nameEl) {
              console.log('[GetSheetName] Found via tab iteration:', nameEl.textContent.trim());
              return nameEl.textContent.trim();
            }
          }
        }

        // Method 4: Get first sheet name as fallback
        const firstSheet = document.querySelector('.docs-sheet-tab-name');
        if (firstSheet) {
          console.log('[GetSheetName] Using first sheet as fallback:', firstSheet.textContent.trim());
          return firstSheet.textContent.trim();
        }

        console.warn('[GetSheetName] Could not find any sheet name, using default');
        return 'Sheet1';
      }
    });

    const sheetName = results[0]?.result || 'Sheet1';
    console.log('[SheetsAPI] Active sheet name:', sheetName);
    return sheetName;
  } catch (error) {
    console.error('[SheetsAPI] Error getting active sheet name:', error);
    return 'Sheet1';
  }
}

/**
 * Read data from active sheet
 */
async function readSheetData(spreadsheetId, sheetName, range = 'A1:Z1000') {
  try {
    const token = await getAuthToken();
    const fullRange = `${sheetName}!${range}`;

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}/values/${encodeURIComponent(fullRange)}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const data = await response.json();
    console.log('[SheetsAPI] Read data:', data);

    if (!data.values || data.values.length === 0) {
      return { headers: [], data: [] };
    }

    // First row as headers, rest as data
    const headers = data.values[0] || [];
    const rows = data.values.slice(1);

    return { headers, data: rows };
  } catch (error) {
    console.error('[SheetsAPI] Error reading sheet data:', error);
    throw error;
  }
}

/**
 * Write data to sheet (creates new sheet or overwrites existing)
 */
async function writeSheetData(spreadsheetId, sheetName, data, startCell = 'A1') {
  try {
    const token = await getAuthToken();
    const range = `${sheetName}!${startCell}`;

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}/values/${encodeURIComponent(range)}?valueInputOption=RAW`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          range: range,
          values: data
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const result = await response.json();
    console.log('[SheetsAPI] ✅ Data written:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error writing sheet data:', error);
    throw error;
  }
}

/**
 * Append data to sheet
 */
async function appendSheetData(spreadsheetId, sheetName, data) {
  try {
    const token = await getAuthToken();
    const range = `${sheetName}!A1`;

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}/values/${encodeURIComponent(range)}:append?valueInputOption=RAW`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          range: range,
          values: data
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const result = await response.json();
    console.log('[SheetsAPI] ✅ Data appended:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error appending sheet data:', error);
    throw error;
  }
}

/**
 * Create a new sheet in the spreadsheet
 */
async function createNewSheet(spreadsheetId, sheetTitle) {
  try {
    const token = await getAuthToken();

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}:batchUpdate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          requests: [{
            addSheet: {
              properties: {
                title: sheetTitle
              }
            }
          }]
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const result = await response.json();
    console.log('[SheetsAPI] ✅ Sheet created:', result);
    return result.replies[0].addSheet.properties;
  } catch (error) {
    console.error('[SheetsAPI] Error creating sheet:', error);
    throw error;
  }
}

/**
 * Highlight rows with color
 */
async function highlightRows(spreadsheetId, sheetId, rowIndices, color = { red: 1, green: 1, blue: 0.8 }) {
  try {
    const token = await getAuthToken();

    // Convert 1-based Google Sheets row numbers to 0-based API indices
    // Backend sends: [2, 3] (Google Sheets rows, 1=headers, 2=first data row)
    // API needs: [1, 2] (0-based indices, 0=headers, 1=first data row)
    const requests = rowIndices.map(rowIndex => ({
      repeatCell: {
        range: {
          sheetId: sheetId,
          startRowIndex: rowIndex - 1,  // Convert to 0-based
          endRowIndex: rowIndex         // End is exclusive, so no -1 needed
        },
        cell: {
          userEnteredFormat: {
            backgroundColor: color
          }
        },
        fields: 'userEnteredFormat.backgroundColor'
      }
    }));

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}:batchUpdate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ requests })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const result = await response.json();
    console.log('[SheetsAPI] ✅ Rows highlighted:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error highlighting rows:', error);
    throw error;
  }
}

/**
 * Get sheet ID by name
 */
async function getSheetIdByName(spreadsheetId, sheetName) {
  try {
    const token = await getAuthToken();

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}?fields=sheets.properties`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const data = await response.json();
    const sheet = data.sheets?.find(s => s.properties.title === sheetName);

    if (!sheet) {
      throw new Error(`Sheet "${sheetName}" not found`);
    }

    return sheet.properties.sheetId;
  } catch (error) {
    console.error('[SheetsAPI] Error getting sheet ID:', error);
    throw error;
  }
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getAuthToken,
    getSpreadsheetIdFromUrl,
    getActiveSheetName,
    readSheetData,
    writeSheetData,
    appendSheetData,
    createNewSheet,
    highlightRows,
    getSheetIdByName
  };
}
