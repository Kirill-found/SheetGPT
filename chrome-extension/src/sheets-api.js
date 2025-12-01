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
    // v9.2.0: Wrap sheet name in quotes for special characters (Cyrillic, spaces, etc.)
    const quotedSheetName = `'${sheetName.replace(/'/g, "''")}'`;
    const fullRange = `${quotedSheetName}!${range}`;

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
      `${SHEETS_API_BASE}/${spreadsheetId}/values/${encodeURIComponent(range)}?valueInputOption=USER_ENTERED`,
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
      `${SHEETS_API_BASE}/${spreadsheetId}/values/${encodeURIComponent(range)}:append?valueInputOption=USER_ENTERED`,
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
 * Create a chart in Google Sheets
 * @param {string} spreadsheetId - The spreadsheet ID
 * @param {number} sheetId - The sheet ID
 * @param {object} chartSpec - Chart specification from backend
 */
async function createChart(spreadsheetId, sheetId, chartSpec) {
  try {
    const token = await getAuthToken();

    const { chart_type, title, x_column_index, y_column_indices, row_count, col_count } = chartSpec;

    console.log(`[SheetsAPI] Creating ${chart_type} chart: "${title}"`);
    console.log(`[SheetsAPI] X column: ${x_column_index}, Y columns: ${y_column_indices}, rows: ${row_count}`);

    // Build series for each Y column
    const series = y_column_indices.map((yColIndex, idx) => ({
      series: {
        sourceRange: {
          sources: [{
            sheetId: sheetId,
            startRowIndex: 0,
            endRowIndex: row_count + 1, // Include header
            startColumnIndex: yColIndex,
            endColumnIndex: yColIndex + 1
          }]
        }
      },
      targetAxis: 'LEFT_AXIS'
    }));

    // Build domain (X axis)
    const domain = {
      domain: {
        sourceRange: {
          sources: [{
            sheetId: sheetId,
            startRowIndex: 0,
            endRowIndex: row_count + 1, // Include header
            startColumnIndex: x_column_index,
            endColumnIndex: x_column_index + 1
          }]
        }
      }
    };

    // Map chart type to Google Sheets API type
    const chartTypeMap = {
      'LINE': 'LINE',
      'BAR': 'BAR',
      'COLUMN': 'COLUMN',
      'PIE': 'PIE',
      'AREA': 'AREA',
      'SCATTER': 'SCATTER',
      'COMBO': 'COMBO'
    };

    const googleChartType = chartTypeMap[chart_type] || 'COLUMN';

    // Build chart spec based on type
    let spec;

    if (googleChartType === 'PIE') {
      // Pie charts have different structure
      spec = {
        pieChart: {
          legendPosition: 'RIGHT_LEGEND',
          domain: domain.domain,
          series: series[0]?.series || series[0],
          threeDimensional: false
        }
      };
    } else {
      // Line, Bar, Column, Area, Scatter, Combo
      spec = {
        basicChart: {
          chartType: googleChartType,
          legendPosition: 'BOTTOM_LEGEND',
          axis: [
            {
              position: 'BOTTOM_AXIS',
              title: chartSpec.x_column_name || ''
            },
            {
              position: 'LEFT_AXIS',
              title: chartSpec.y_column_names?.join(', ') || ''
            }
          ],
          domains: [domain],
          series: series,
          headerCount: 1,
          stackedType: 'NOT_STACKED'
        }
      };

      // interpolateNulls only supported for LINE, AREA, SCATTER
      if (['LINE', 'AREA', 'SCATTER'].includes(googleChartType)) {
        spec.basicChart.interpolateNulls = true;
      }

      // For scatter, add specific settings
      if (googleChartType === 'SCATTER') {
        spec.basicChart.lineSmoothing = false;
      }

      // For area chart, stack if multiple series
      if (googleChartType === 'AREA' && series.length > 1) {
        spec.basicChart.stackedType = 'STACKED';
      }
    }

    // Build the full chart request
    const chartRequest = {
      addChart: {
        chart: {
          spec: {
            title: title,
            ...spec
          },
          position: {
            overlayPosition: {
              anchorCell: {
                sheetId: sheetId,
                rowIndex: 1,
                columnIndex: col_count + 1 // Place chart next to data
              },
              offsetXPixels: 20,
              offsetYPixels: 20,
              widthPixels: 600,
              heightPixels: 400
            }
          }
        }
      }
    };

    console.log('[SheetsAPI] Chart request:', JSON.stringify(chartRequest, null, 2));

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}:batchUpdate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          requests: [chartRequest]
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      console.error('[SheetsAPI] Chart error:', error);
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const result = await response.json();
    console.log('[SheetsAPI] ✅ Chart created:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error creating chart:', error);
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
    console.log('[SheetsAPI] 📋 All sheets:', data.sheets?.map(s => ({ title: s.properties.title, sheetId: s.properties.sheetId })));

    const sheet = data.sheets?.find(s => s.properties.title === sheetName);

    if (!sheet) {
      console.error(`[SheetsAPI] ❌ Sheet "${sheetName}" not found in sheets list`);
      throw new Error(`Sheet "${sheetName}" not found`);
    }

    console.log(`[SheetsAPI] ✅ Found sheet "${sheetName}" with ID: ${sheet.properties.sheetId}`);
    return sheet.properties.sheetId;
  } catch (error) {
    console.error('[SheetsAPI] Error getting sheet ID:', error);
    throw error;
  }
}

/**
 * Apply conditional formatting to a column
 * @param {string} spreadsheetId - The spreadsheet ID
 * @param {number} sheetId - The sheet ID
 * @param {object} rule - The conditional format rule with:
 *   - column_index: Column to apply rule to
 *   - condition_type: NUMBER_GREATER, NUMBER_LESS, NUMBER_EQ, BLANK, NOT_BLANK
 *   - condition_value: Value to compare against (null for BLANK/NOT_BLANK)
 *   - format_color: RGB color object {red, green, blue}
 */
async function applyConditionalFormat(spreadsheetId, sheetId, rule) {
  try {
    const token = await getAuthToken();

    const { column_index, condition_type, condition_value, format_color } = rule;

    console.log(`[SheetsAPI] Applying conditional format to column ${column_index}, type: ${condition_type}, value: ${condition_value}`);

    // Build the condition based on type
    let booleanCondition;

    switch (condition_type) {
      case 'NUMBER_GREATER':
        booleanCondition = {
          type: 'NUMBER_GREATER',
          values: [{ userEnteredValue: String(condition_value) }]
        };
        break;
      case 'NUMBER_LESS':
        booleanCondition = {
          type: 'NUMBER_LESS',
          values: [{ userEnteredValue: String(condition_value) }]
        };
        break;
      case 'NUMBER_EQ':
        booleanCondition = {
          type: 'NUMBER_EQ',
          values: [{ userEnteredValue: String(condition_value) }]
        };
        break;
      case 'BLANK':
        booleanCondition = {
          type: 'BLANK'
        };
        break;
      case 'NOT_BLANK':
        booleanCondition = {
          type: 'NOT_BLANK'
        };
        break;
      default:
        booleanCondition = {
          type: 'NUMBER_GREATER',
          values: [{ userEnteredValue: '0' }]
        };
    }

    // Build the conditional format request
    const request = {
      addConditionalFormatRule: {
        rule: {
          ranges: [{
            sheetId: sheetId,
            startRowIndex: 1, // Skip header row
            startColumnIndex: column_index,
            endColumnIndex: column_index + 1
          }],
          booleanRule: {
            condition: booleanCondition,
            format: {
              backgroundColor: format_color || { red: 1, green: 1, blue: 0.7 }
            }
          }
        },
        index: 0 // Insert at the beginning of the conditional format rules
      }
    };

    console.log('[SheetsAPI] Conditional format request:', JSON.stringify(request, null, 2));

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}:batchUpdate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          requests: [request]
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      console.error('[SheetsAPI] Conditional format error:', error);
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const result = await response.json();
    console.log('[SheetsAPI] ✅ Conditional format applied:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error applying conditional format:', error);
    throw error;
  }
}

/**
 * Apply color scale (gradient) formatting to a column
 * This creates a gradient from min to max values in the column
 * Rule object:
 *   - column_index: Column to apply gradient to (0-based)
 *   - min_color: RGB color object for minimum value
 *   - mid_color: RGB color object for midpoint value
 *   - max_color: RGB color object for maximum value
 *   - row_count: Number of data rows (excluding header)
 */
async function applyColorScale(spreadsheetId, sheetId, rule) {
  try {
    const token = await getAuthToken();

    console.log('[SheetsAPI] 🎨 applyColorScale called with rule:', JSON.stringify(rule, null, 2));

    const { column_index, min_color, mid_color, max_color, row_count } = rule;

    console.log(`[SheetsAPI] 🎨 Applying color scale to column ${column_index} (type: ${typeof column_index})`);
    console.log(`[SheetsAPI] Colors: min=${JSON.stringify(min_color)}, mid=${JSON.stringify(mid_color)}, max=${JSON.stringify(max_color)}`);

    // Build gradient rule with proper color format (alpha required!)
    const gradientRule = {
      minpoint: {
        color: {
          red: min_color?.red || 0.0,
          green: min_color?.green || 1.0,
          blue: min_color?.blue || 0.0,
          alpha: 1.0
        },
        type: 'MIN'
      },
      maxpoint: {
        color: {
          red: max_color?.red || 1.0,
          green: max_color?.green || 0.0,
          blue: max_color?.blue || 0.0,
          alpha: 1.0
        },
        type: 'MAX'
      }
    };

    // Add midpoint if provided
    if (mid_color) {
      gradientRule.midpoint = {
        color: {
          red: mid_color.red,
          green: mid_color.green,
          blue: mid_color.blue,
          alpha: 1.0
        },
        type: 'PERCENTILE',
        value: '50'
      };
    }

    const request = {
      addConditionalFormatRule: {
        rule: {
          ranges: [{
            sheetId: sheetId,
            startRowIndex: 1,
            endRowIndex: (row_count || 1000) + 1,
            startColumnIndex: column_index,
            endColumnIndex: column_index + 1
          }],
          gradientRule: gradientRule
        },
        index: 0
      }
    };

    console.log('[SheetsAPI] Color scale request:', JSON.stringify(request, null, 2));

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}:batchUpdate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          requests: [request]
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      console.error('[SheetsAPI] Color scale error:', error);
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const result = await response.json();
    console.log('[SheetsAPI] ✅ Color scale applied:', JSON.stringify(result, null, 2));
    console.log('[SheetsAPI] 📋 Replies:', result.replies);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error applying color scale:', error);
    throw error;
  }
}

/**
 * Set data validation (dropdown list) for a column
 */
async function setDataValidation(spreadsheetId, sheetId, rule) {
  try {
    const token = await getAuthToken();

    const { column_index, allowed_values, show_dropdown, strict } = rule;

    console.log(`[SheetsAPI] Setting data validation for column ${column_index}, values: ${allowed_values.join(', ')}`);

    // Build the data validation request
    const request = {
      setDataValidation: {
        range: {
          sheetId: sheetId,
          startRowIndex: 1, // Skip header row
          startColumnIndex: column_index,
          endColumnIndex: column_index + 1
        },
        rule: {
          condition: {
            type: 'ONE_OF_LIST',
            values: allowed_values.map(value => ({ userEnteredValue: value }))
          },
          showCustomUi: show_dropdown !== false, // Show dropdown by default
          strict: strict !== false // Reject invalid input by default
        }
      }
    };

    console.log('[SheetsAPI] Data validation request:', JSON.stringify(request, null, 2));

    const response = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}:batchUpdate`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          requests: [request]
        })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      console.error('[SheetsAPI] Data validation error:', error);
      throw new Error(`Sheets API error: ${error.error?.message || response.statusText}`);
    }

    const result = await response.json();
    console.log('[SheetsAPI] ✅ Data validation set:', result);
    return result;
  } catch (error) {
    console.error('[SheetsAPI] Error setting data validation:', error);
    throw error;
  }
}

/**
 * Convert text column to numbers
 * Reads values, converts to numbers, writes back
 */
async function convertColumnToNumbers(spreadsheetId, sheetName, columnIndex, rowCount) {
  try {
    const token = await getAuthToken();

    // Get column letter (A, B, C, ...)
    const columnLetter = String.fromCharCode(65 + columnIndex);
    const range = `${sheetName}!${columnLetter}2:${columnLetter}${rowCount + 1}`;

    console.log(`[SheetsAPI] 🔢 Converting column ${columnLetter} to numbers, range: ${range}`);

    // Read current values
    const readResponse = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}/values/${encodeURIComponent(range)}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!readResponse.ok) {
      const error = await readResponse.json();
      throw new Error(`Read error: ${error.error?.message || readResponse.statusText}`);
    }

    const data = await readResponse.json();
    const values = data.values || [];

    console.log(`[SheetsAPI] 📖 Read ${values.length} values from column ${columnLetter}`);

    // Convert to numbers
    const convertedValues = values.map(row => {
      if (!row || !row[0]) return [null];
      const val = row[0];
      // Remove spaces, replace comma with dot, parse as number
      const cleanVal = String(val).replace(/\s/g, '').replace(',', '.');
      const num = parseFloat(cleanVal);
      return [isNaN(num) ? val : num];
    });

    console.log(`[SheetsAPI] 🔄 Converted values sample:`, convertedValues.slice(0, 3));

    // Write back as numbers
    const writeResponse = await fetch(
      `${SHEETS_API_BASE}/${spreadsheetId}/values/${encodeURIComponent(range)}?valueInputOption=USER_ENTERED`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          range: range,
          values: convertedValues
        })
      }
    );

    if (!writeResponse.ok) {
      const error = await writeResponse.json();
      throw new Error(`Write error: ${error.error?.message || writeResponse.statusText}`);
    }

    const result = await writeResponse.json();
    console.log(`[SheetsAPI] ✅ Column ${columnLetter} converted to numbers:`, result);

    return {
      success: true,
      updatedCells: result.updatedCells,
      column: columnLetter
    };
  } catch (error) {
    console.error('[SheetsAPI] Error converting column to numbers:', error);
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
    createChart,
    getSheetIdByName,
    applyConditionalFormat,
    applyColorScale,
    setDataValidation,
    convertColumnToNumbers
  };
}
