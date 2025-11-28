/**
 * Google Sheets API Integration
 * Handles OAuth and all Sheets API operations
 */

const SHEETS_API_BASE = 'https://sheets.googleapis.com/v4/spreadsheets';

/**
 * Get OAuth token for Google Sheets API
 * v7.9.4: Added token refresh and better error handling
 */
async function getAuthToken(forceRefresh = false) {
  return new Promise((resolve, reject) => {
    // If force refresh, first remove cached token
    if (forceRefresh) {
      console.log('[SheetsAPI] Force refreshing token...');
      chrome.identity.getAuthToken({ interactive: false }, (cachedToken) => {
        if (cachedToken) {
          chrome.identity.removeCachedAuthToken({ token: cachedToken }, () => {
            console.log('[SheetsAPI] Cached token removed, getting new one...');
            getNewToken(resolve, reject);
          });
        } else {
          getNewToken(resolve, reject);
        }
      });
    } else {
      getNewToken(resolve, reject);
    }
  });
}

function getNewToken(resolve, reject) {
  chrome.identity.getAuthToken({ interactive: true }, (token) => {
    if (chrome.runtime.lastError) {
      const errorMsg = chrome.runtime.lastError.message;
      console.error('[SheetsAPI] Auth error:', errorMsg);

      // v7.9.4: Provide clearer error messages
      if (errorMsg.includes('OAuth2 not granted') || errorMsg.includes('user denied')) {
        reject(new Error('Пользователь отклонил доступ к Google Sheets. Нажмите на иконку расширения и разрешите доступ.'));
      } else if (errorMsg.includes('invalid_client') || errorMsg.includes('client_id')) {
        reject(new Error('Ошибка конфигурации OAuth. Обратитесь к разработчику.'));
      } else if (errorMsg.includes('network') || errorMsg.includes('fetch')) {
        reject(new Error('Ошибка сети при авторизации. Проверьте интернет-соединение.'));
      } else {
        reject(new Error(`Ошибка авторизации Google: ${errorMsg}`));
      }
    } else if (!token) {
      reject(new Error('Не удалось получить токен авторизации. Попробуйте перезагрузить страницу.'));
    } else {
      console.log('[SheetsAPI] ✅ Got auth token');
      resolve(token);
    }
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
 * Get all sheet names from spreadsheet
 */
async function getAllSheetNames(spreadsheetId) {
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
    const sheetNames = data.sheets.map(sheet => sheet.properties.title);
    console.log('[SheetsAPI] All sheet names:', sheetNames);
    return sheetNames;
  } catch (error) {
    console.error('[SheetsAPI] Error getting sheet names:', error);
    throw error;
  }
}

/**
 * Read data from active sheet
 * Default limit: 500 rows for performance optimization
 * v7.9.4: Added automatic token refresh on 401 errors
 */
async function readSheetData(spreadsheetId, sheetName, range = 'A1:Z500', _retryCount = 0) {
  try {
    const token = await getAuthToken(_retryCount > 0); // Force refresh on retry
    const fullRange = `${sheetName}!${range}`;

    console.log(`[SheetsAPI] Reading range: ${fullRange}${_retryCount > 0 ? ' (retry #' + _retryCount + ')' : ''}`);

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}/values/${encodeURIComponent(fullRange)}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    // v7.9.4: Auto-retry with token refresh on 401/403
    if ((response.status === 401 || response.status === 403) && _retryCount < 1) {
      console.log('[SheetsAPI] Got 401/403, refreshing token and retrying...');
      return readSheetData(spreadsheetId, sheetName, range, _retryCount + 1);
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const data = await response.json();
    console.log('[SheetsAPI] API Response:', data);
    console.log('[SheetsAPI] Has values?', !!data.values, 'Length:', data.values?.length || 0);

    if (!data.values || data.values.length === 0) {
      console.warn('[SheetsAPI] ⚠️ No data found in range:', fullRange);
      return { headers: [], data: [] };
    }

    // First row as headers, rest as data
    const headers = data.values[0] || [];
    const rows = data.values.slice(1);

    console.log('[SheetsAPI] ✅ Parsed data:', { headers, rowCount: rows.length });

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
 * Sort data in a range by column
 * @param {string} spreadsheetId - The spreadsheet ID
 * @param {number} sheetId - The sheet ID (not name!)
 * @param {number} columnIndex - 0-based column index to sort by
 * @param {string} sortOrder - "ASCENDING" or "DESCENDING"
 * @param {number} startRowIndex - Start row (0-based, typically 1 to skip header)
 * @param {number} endRowIndex - End row (exclusive), or -1 for all rows
 */
async function sortRange(spreadsheetId, sheetId, columnIndex, sortOrder = "ASCENDING", startRowIndex = 1, endRowIndex = -1) {
  try {
    const token = await getAuthToken();

    // If endRowIndex is -1, we need to get the sheet dimensions first
    let actualEndRowIndex = endRowIndex;
    if (endRowIndex === -1) {
      // Get sheet properties to find row count
      const propsResponse = await fetch(
        `${SHEETS_API_BASE}/${spreadsheetId}?fields=sheets.properties`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      const propsData = await propsResponse.json();
      const sheet = propsData.sheets?.find(s => s.properties.sheetId === sheetId);
      actualEndRowIndex = sheet?.properties?.gridProperties?.rowCount || 1000;
    }

    console.log(`[SheetsAPI] Sorting sheet ${sheetId}, column ${columnIndex}, order ${sortOrder}, rows ${startRowIndex}-${actualEndRowIndex}`);

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
            sortRange: {
              range: {
                sheetId: sheetId,
                startRowIndex: startRowIndex,  // Skip header row
                endRowIndex: actualEndRowIndex
              },
              sortSpecs: [{
                dimensionIndex: columnIndex,
                sortOrder: sortOrder  // "ASCENDING" or "DESCENDING"
              }]
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
    console.log('[SheetsAPI] ✅ Range sorted:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error sorting range:', error);
    throw error;
  }
}

/**
 * Freeze rows and/or columns
 * @param {string} spreadsheetId - The spreadsheet ID
 * @param {number} sheetId - The sheet ID
 * @param {number} frozenRowCount - Number of rows to freeze (0 to unfreeze)
 * @param {number} frozenColumnCount - Number of columns to freeze (0 to unfreeze)
 */
async function freezeRowsColumns(spreadsheetId, sheetId, frozenRowCount = 1, frozenColumnCount = 0) {
  try {
    const token = await getAuthToken();

    console.log(`[SheetsAPI] Freezing ${frozenRowCount} rows and ${frozenColumnCount} columns on sheet ${sheetId}`);

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
            updateSheetProperties: {
              properties: {
                sheetId: sheetId,
                gridProperties: {
                  frozenRowCount: frozenRowCount,
                  frozenColumnCount: frozenColumnCount
                }
              },
              fields: 'gridProperties.frozenRowCount,gridProperties.frozenColumnCount'
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
    console.log('[SheetsAPI] ✅ Rows/columns frozen:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error freezing rows/columns:', error);
    throw error;
  }
}

/**
 * Format cells (bold, background color)
 * @param {string} spreadsheetId - The spreadsheet ID
 * @param {number} sheetId - The sheet ID
 * @param {number} rowIndex - 0-based row index to format
 * @param {boolean} bold - Make text bold
 * @param {string} backgroundColor - Hex color (e.g., "#FFFF00")
 */
async function formatRow(spreadsheetId, sheetId, rowIndex = 0, bold = true, backgroundColor = null) {
  try {
    const token = await getAuthToken();

    console.log(`[SheetsAPI] Formatting row ${rowIndex} on sheet ${sheetId}, bold=${bold}, bg=${backgroundColor}`);

    // Build cell format
    const cellFormat = {};
    const fields = [];

    if (bold) {
      cellFormat.textFormat = { bold: true };
      fields.push('userEnteredFormat.textFormat.bold');
    }

    if (backgroundColor) {
      // Convert hex to RGB (0-1 scale)
      const hex = backgroundColor.replace('#', '');
      const r = parseInt(hex.substring(0, 2), 16) / 255;
      const g = parseInt(hex.substring(2, 4), 16) / 255;
      const b = parseInt(hex.substring(4, 6), 16) / 255;

      cellFormat.backgroundColor = { red: r, green: g, blue: b };
      fields.push('userEnteredFormat.backgroundColor');
    }

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
            repeatCell: {
              range: {
                sheetId: sheetId,
                startRowIndex: rowIndex,
                endRowIndex: rowIndex + 1
              },
              cell: {
                userEnteredFormat: cellFormat
              },
              fields: fields.join(',')
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
    console.log('[SheetsAPI] ✅ Row formatted:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error formatting row:', error);
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
    sortRange,
    freezeRowsColumns,
    formatRow,
    getSheetIdByName
  };
}
