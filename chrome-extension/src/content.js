/**
 * SheetGPT Chrome Extension - Content Script
 * Инжектит sidebar в Google Sheets
 */

console.log('[SheetGPT] Content script loaded');

// Слушаем сообщения от popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[SheetGPT] Message received:', message);

  if (message.action === 'OPEN_SIDEBAR') {
    openSidebar();
    sendResponse({ success: true });
  }
});

// Проверяем что мы на странице Google Sheets
if (window.location.href.includes('docs.google.com/spreadsheets')) {
  console.log('[SheetGPT] Google Sheets detected, injecting sidebar...');

  // Ждём когда DOM загрузится
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectSidebar);
  } else {
    injectSidebar();
  }
}

function injectSidebar() {
  // Проверяем что sidebar ещё не создан
  if (document.getElementById('sheetgpt-sidebar-container')) {
    console.log('[SheetGPT] Sidebar already exists');
    return;
  }

  // Создаём контейнер для iframe
  const container = document.createElement('div');
  container.id = 'sheetgpt-sidebar-container';
  container.style.cssText = `
    position: fixed;
    top: 0;
    right: 0;
    width: 400px;
    height: 100vh;
    z-index: 999999;
    transform: translateX(100%);
    transition: transform 0.3s ease;
  `;

  // Создаём iframe с sidebar
  const iframe = document.createElement('iframe');
  iframe.id = 'sheetgpt-sidebar-iframe';
  iframe.src = chrome.runtime.getURL('src/sidebar.html');
  iframe.style.cssText = `
    width: 100%;
    height: 100%;
    border: none;
    border-left: 1px solid #e5e7eb;
    box-shadow: -2px 0 10px rgba(0, 0, 0, 0.1);
  `;

  container.appendChild(iframe);

  // Добавляем toggle кнопку
  const toggleBtn = document.createElement('button');
  toggleBtn.id = 'sheetgpt-toggle-btn';
  toggleBtn.innerHTML = `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  `;
  toggleBtn.style.cssText = `
    position: fixed;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 48px;
    height: 48px;
    background: #4285f4;
    border: none;
    border-radius: 24px 0 0 24px;
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: -2px 2px 8px rgba(0, 0, 0, 0.2);
    z-index: 1000000;
    transition: background 0.2s;
  `;

  toggleBtn.addEventListener('click', () => {
    const isOpen = container.style.transform === 'translateX(0px)';
    container.style.transform = isOpen ? 'translateX(100%)' : 'translateX(0px)';
  });

  document.body.appendChild(container);
  document.body.appendChild(toggleBtn);

  console.log('[SheetGPT] Sidebar injected with Apps Script design');
}

function setupEventListeners() {
  const sidebar = document.getElementById('sheetgpt-sidebar');
  const toggleBtn = document.getElementById('sheetgpt-toggle');
  const closeBtn = document.getElementById('sheetgpt-close');
  const sendBtn = document.getElementById('sheetgpt-send');
  const input = document.getElementById('sheetgpt-input');

  // Toggle sidebar
  toggleBtn?.addEventListener('click', () => {
    sidebar?.classList.toggle('sheetgpt-sidebar-collapsed');
  });

  // Close sidebar
  closeBtn?.addEventListener('click', () => {
    sidebar?.classList.add('sheetgpt-sidebar-collapsed');
  });

  // Send message
  sendBtn?.addEventListener('click', handleSendMessage);

  // Enter to send (Shift+Enter for new line)
  input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });
}

async function handleSendMessage() {
  const input = document.getElementById('sheetgpt-input');
  const chat = document.getElementById('sheetgpt-chat');
  const query = input?.value?.trim();

  if (!query) return;

  // Добавляем сообщение пользователя
  addMessage(query, 'user');
  input.value = '';

  // Показываем loading
  const loadingId = addMessage('Анализирую данные...', 'ai', true);

  try {
    // Получаем данные из активного листа
    const sheetData = await getActiveSheetData();

    // Отправляем запрос в SheetGPT API
    const response = await fetch('https://sheetgpt-production.up.railway.app/api/v1/formula', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query,
        column_names: sheetData.headers,
        sheet_data: sheetData.data
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();

    // Удаляем loading
    removeMessage(loadingId);

    // Показываем результат
    await displayResult(result);

  } catch (error) {
    console.error('[SheetGPT] Error:', error);
    removeMessage(loadingId);
    addMessage(`Ошибка: ${error.message}`, 'ai');
  }
}

function addMessage(text, type, isLoading = false) {
  const chat = document.getElementById('sheetgpt-chat');
  const messageId = `msg-${Date.now()}`;

  const message = document.createElement('div');
  message.id = messageId;
  message.className = `sheetgpt-message sheetgpt-message-${type}`;
  if (isLoading) message.classList.add('sheetgpt-loading');

  message.innerHTML = `
    <div class="sheetgpt-message-content">${text}</div>
  `;

  chat?.appendChild(message);
  chat?.scrollTo(0, chat.scrollHeight);

  return messageId;
}

function removeMessage(messageId) {
  document.getElementById(messageId)?.remove();
}

async function displayResult(result) {
  let content = `<strong>${result.summary || 'Результат'}</strong>`;

  // Добавляем structured_data если есть
  if (result.structured_data) {
    content += '<br><br><em>Таблица создана! Нажмите "Вставить" чтобы добавить в лист.</em>';
    content += `<br><button class="sheetgpt-insert-btn" data-result='${JSON.stringify(result)}'>Вставить таблицу</button>`;
  }

  // Показываем сообщение
  const messageId = addMessage(content, 'ai');

  // ИСПРАВЛЕНИЕ: Фактически вызываем подсветку строк!
  if (result.highlight_rows && result.highlight_rows.length > 0) {
    console.log('[SheetGPT] Applying highlight to rows:', result.highlight_rows);

    try {
      const highlightResult = await highlightRows(
        result.highlight_rows,
        result.highlight_color || 'yellow'
      );

      // Обновляем сообщение с результатом подсветки
      const message = document.getElementById(messageId);
      if (message) {
        const icon = highlightResult.success ? '✅' : '❌';
        message.innerHTML += `<br><br><em>${icon} ${highlightResult.message}</em>`;
      }
    } catch (error) {
      console.error('[SheetGPT] Highlight error:', error);
      const message = document.getElementById(messageId);
      if (message) {
        message.innerHTML += `<br><br><em>❌ Ошибка выделения: ${error.message}</em>`;
      }
    }
  }

  // Добавляем обработчик для кнопки вставки
  setTimeout(() => {
    const insertBtn = document.querySelector(`#${messageId} .sheetgpt-insert-btn`);
    insertBtn?.addEventListener('click', () => {
      const data = JSON.parse(insertBtn.getAttribute('data-result'));
      insertTableToSheet(data.structured_data);
    });
  }, 100);
}

/**
 * Read sheet data directly from DOM (NO OAuth needed!)
 */
function readSheetDataFromDOM() {
  console.log('[SheetGPT] Reading data from DOM...');

  try {
    // First, find the main grid container to avoid reading UI elements
    const gridContainers = [
      '[role="grid"]',           // ARIA grid
      'table.waffle',            // Classic view
      '.grid-container',         // New view
      'table'                    // Fallback
    ];

    let gridContainer = null;
    for (const selector of gridContainers) {
      const container = document.querySelector(selector);
      if (container) {
        gridContainer = container;
        console.log(`[SheetGPT] ✅ Found grid container: "${selector}"`);
        break;
      }
    }

    if (!gridContainer) {
      console.warn('[SheetGPT] No grid container found');
      return null;
    }

    // Try multiple selector strategies for different Google Sheets versions
    const selectorStrategies = [
      // Strategy 1: ARIA roles (most reliable)
      { rows: '[role="row"]', cells: '[role="gridcell"]' },
      // Strategy 2: Table structure
      { rows: 'tbody tr, tr', cells: 'td' },
      // Strategy 3: Grid classes
      { rows: '.grid-row, .ritz .grid-row', cells: '.cell, [role="gridcell"]' },
      // Strategy 4: Generic rows
      { rows: 'tr', cells: 'td, [role="gridcell"]' }
    ];

    let rows = [];
    let cellSelector = null;

    // Try each strategy until we find rows WITHIN the grid container
    for (const strategy of selectorStrategies) {
      const foundRows = gridContainer.querySelectorAll(strategy.rows);
      console.log(`[SheetGPT] Trying selector "${strategy.rows}" in grid → found ${foundRows.length} rows`);

      if (foundRows.length > 0) {
        rows = Array.from(foundRows);
        cellSelector = strategy.cells;
        console.log(`[SheetGPT] ✅ Using strategy: rows="${strategy.rows}", cells="${strategy.cells}"`);
        break;
      }
    }

    if (rows.length === 0) {
      console.warn('[SheetGPT] No rows found with any selector strategy');
      return null;
    }

    const data = [];
    for (const row of rows.slice(0, 1000)) { // Limit to 1000 rows
      const cells = Array.from(row.querySelectorAll(cellSelector));
      if (cells.length > 0) {
        const rowData = cells.map(cell => cell.textContent.trim());
        if (rowData.some(val => val)) { // Skip empty rows
          data.push(rowData);
        }
      }
    }

    if (data.length < 1) {
      console.warn('[SheetGPT] No data found in DOM');
      return null;
    }

    const headers = data[0];
    const rows_data = data.slice(1);

    console.log(`[SheetGPT] ✅ Read from DOM: ${rows_data.length} rows, ${headers.length} columns`);
    console.log(`[SheetGPT] Headers:`, headers);
    console.log(`[SheetGPT] First row:`, rows_data[0]);
    console.log(`[SheetGPT] Second row:`, rows_data[1]);

    // Validate: all rows should have same number of columns as headers
    const invalidRows = rows_data.filter(row => row.length !== headers.length);
    if (invalidRows.length > 0) {
      console.warn(`[SheetGPT] ⚠️ Found ${invalidRows.length} rows with mismatched column count!`);
      console.warn(`[SheetGPT] Expected ${headers.length} columns, but found:`, invalidRows.map(r => r.length));
    }

    return { headers, data: rows_data };
  } catch (error) {
    console.error('[SheetGPT] Error reading from DOM:', error);
    return null;
  }
}

async function getActiveSheetData() {
  console.log('[SheetGPT] Getting active sheet data...');

  try {
    // ИСПРАВЛЕНИЕ: Пробуем Sheets API с коротким таймаутом, затем фоллбек на DOM
    console.log('[SheetGPT] Trying Sheets API first...');

    const apiPromise = chrome.runtime.sendMessage({
      action: 'GET_SHEET_DATA'
    });

    // Race between API call and 5-second timeout
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Sheets API timeout')), 5000)
    );

    const response = await Promise.race([apiPromise, timeoutPromise]);

    if (response && response.success) {
      console.log('[SheetGPT] ✅ Got data from Sheets API:', response.result);
      return response.result;
    }

    // If API returned error, fall through to DOM reading
    console.warn('[SheetGPT] ⚠️ Sheets API failed, trying DOM reading...');

  } catch (error) {
    console.warn('[SheetGPT] ⚠️ Sheets API error:', error.message, '- falling back to DOM reading');
  }

  // ФОЛЛБЕК: Read from DOM
  console.log('[SheetGPT] 📖 Reading data from DOM...');
  const domData = readSheetDataFromDOM();

  if (domData && domData.headers && domData.headers.length > 0) {
    console.log(`[SheetGPT] ✅ Got data from DOM: ${domData.data.length} rows`);
    return domData;
  }

  // If both failed, return empty data for AI table generation
  console.warn('[SheetGPT] ⚠️ Both API and DOM failed, returning empty data');
  return { headers: [], data: [] };
}

async function insertTableToSheet(structuredData) {
  // TODO: Реализовать запись данных в Google Sheets
  console.log('[SheetGPT] Inserting table to sheet:', structuredData);
  addMessage('Функция записи в разработке. Скоро будет доступна!', 'ai');
}

function openSidebar() {
  const container = document.getElementById('sheetgpt-sidebar-container');
  if (container) {
    container.style.transform = 'translateX(0px)';
    console.log('[SheetGPT] Sidebar opened');
  } else {
    console.log('[SheetGPT] Sidebar not found, injecting...');
    injectSidebar();
    setTimeout(() => {
      const newContainer = document.getElementById('sheetgpt-sidebar-container');
      if (newContainer) {
        newContainer.style.transform = 'translateX(0px)';
      }
    }, 100);
  }
}

// ===== POSTMESSAGE BRIDGE =====
// Listen for messages from sidebar iframe
window.addEventListener('message', async (event) => {
  console.log('[SheetGPT] Received postMessage:', {
    data: event.data,
    origin: event.origin,
    source: event.source,
    hasAction: event.data?.action,
    hasMessageId: event.data?.messageId
  });

  // Handle READY message from sidebar
  if (event.data && event.data.type === 'SHEETGPT_READY') {
    console.log('[SheetGPT] ✅ Sidebar is ready!');
    return;
  }

  // Verify it's a message from our sidebar (has our message structure)
  if (!event.data || typeof event.data !== 'object' || !event.data.action || !event.data.messageId) {
    console.log('[SheetGPT] Ignoring message - not from sidebar (missing action or messageId)');
    return;
  }

  const { action, data, messageId } = event.data;
  console.log('[SheetGPT] ✅ Processing action:', action, 'messageId:', messageId, 'data:', data);

  try {
    let result;

    switch (action) {
      case 'PROCESS_QUERY':
        result = await processQuery(data.query);
        break;

      case 'GET_CUSTOM_CONTEXT':
        result = await getCustomContext();
        break;

      case 'SAVE_CUSTOM_CONTEXT':
        result = await saveCustomContext(data.context);
        break;

      case 'INSERT_FORMULA':
        result = await insertFormula(data.formula, data.targetCell);
        break;

      case 'CREATE_TABLE_AND_CHART':
        result = await createTableAndChart(data.structuredData);
        break;

      case 'REPLACE_DATA_IN_CURRENT_SHEET':
        result = await replaceDataInCurrentSheet(data.structuredData);
        break;

      case 'HIGHLIGHT_ROWS':
        result = await highlightRows(data.rows, data.color);
        break;

      default:
        throw new Error(`Unknown action: ${action}`);
    }

    // Send success response back to iframe
    sendMessageToSidebar({
      messageId,
      success: true,
      result
    });

  } catch (error) {
    console.error('[SheetGPT] Error handling message:', error);

    // Send error response back to iframe
    sendMessageToSidebar({
      messageId,
      success: false,
      error: error.message
    });
  }
});

function sendMessageToSidebar(data) {
  const iframe = document.getElementById('sheetgpt-sidebar-iframe');
  console.log('[SheetGPT] Sending response to sidebar:', data);
  if (iframe && iframe.contentWindow) {
    iframe.contentWindow.postMessage(data, '*');
    console.log('[SheetGPT] ✅ Response sent to sidebar');
  } else {
    console.error('[SheetGPT] ❌ Cannot send to sidebar - iframe not found or no contentWindow');
  }
}

// ===== API HANDLERS =====

async function processQuery(query) {
  console.log('[SheetGPT] Processing query:', query);

  // Get data from active sheet (TODO: implement real sheet reading)
  const sheetData = await getActiveSheetData();

  // Get custom context from storage
  const { customContext } = await chrome.storage.local.get('customContext');

  // Call SheetGPT API
  const response = await fetch('https://sheetgpt-production.up.railway.app/api/v1/formula', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      column_names: sheetData.headers,
      sheet_data: sheetData.data,
      custom_context: customContext || null
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const result = await response.json();
  return result;
}

async function getCustomContext() {
  const { customContext } = await chrome.storage.local.get('customContext');
  return customContext || '';
}

async function saveCustomContext(context) {
  await chrome.storage.local.set({ customContext: context });
  return { success: true, message: 'Настройки сохранены' };
}

async function insertFormula(formula, targetCell) {
  // TODO: Implement formula insertion into Google Sheets
  // For now, show notification
  console.log('[SheetGPT] Insert formula:', formula, 'at', targetCell);
  return {
    success: true,
    message: 'Функция записи формул в разработке. Скопируйте формулу вручную.'
  };
}

async function createTableAndChart(structuredData) {
  console.log('[SheetGPT] Create table and chart:', structuredData);

  try {
    // Convert structured data to 2D array
    const values = convertStructuredDataToValues(structuredData);

    // Generate sheet title
    const timestamp = new Date().toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).replace(/[,\s:]/g, '_');
    const sheetTitle = `SheetGPT_${timestamp}`;

    // Create new sheet with data
    const response = await chrome.runtime.sendMessage({
      action: 'CREATE_NEW_SHEET',
      data: {
        sheetTitle,
        values
      }
    });

    if (!response.success) {
      throw new Error(response.error);
    }

    console.log('[SheetGPT] ✅ Table created:', response.result);
    return {
      success: true,
      message: `Таблица создана на листе "${sheetTitle}" (${response.result.rowsWritten} строк)`
    };
  } catch (error) {
    console.error('[SheetGPT] Error creating table:', error);
    return {
      success: false,
      message: `Ошибка создания таблицы: ${error.message}`
    };
  }
}

async function replaceDataInCurrentSheet(structuredData) {
  console.log('[SheetGPT] Replace data in current sheet:', structuredData);

  try {
    // Convert structured data to 2D array
    const values = convertStructuredDataToValues(structuredData);

    // Get current sheet name
    const sheetNameResponse = await chrome.runtime.sendMessage({
      action: 'GET_SHEET_DATA'
    });

    if (!sheetNameResponse.success) {
      throw new Error(sheetNameResponse.error);
    }

    // We need to extract sheet name - for now use "Sheet1" as fallback
    // TODO: Get actual active sheet name from page DOM
    const sheetName = 'Sheet1';

    // Write data to current sheet
    const response = await chrome.runtime.sendMessage({
      action: 'WRITE_SHEET_DATA',
      data: {
        sheetName,
        values,
        startCell: 'A1',
        mode: 'overwrite'
      }
    });

    if (!response.success) {
      throw new Error(response.error);
    }

    console.log('[SheetGPT] ✅ Data replaced:', response.result);
    return {
      success: true,
      message: `Данные обновлены на листе "${sheetName}" (${values.length} строк)`
    };
  } catch (error) {
    console.error('[SheetGPT] Error replacing data:', error);
    return {
      success: false,
      message: `Ошибка обновления данных: ${error.message}`
    };
  }
}

/**
 * Highlight rows directly in DOM (NO OAuth needed!)
 */
function highlightRowsInDOM(rowIndices, colorName) {
  console.log('[SheetGPT] Highlighting rows in DOM:', rowIndices, 'color:', colorName);

  try {
    // Convert color name to CSS color
    const colorMap = {
      'yellow': '#ffffe0',
      'green': '#e0ffe0',
      'red': '#ffe0e0',
      'blue': '#e0f0ff',
      'orange': '#ffe5cc'
    };
    const bgColor = colorMap[colorName?.toLowerCase()] || colorMap['yellow'];

    let highlightedCount = 0;

    // First, find the main grid container (same as readSheetDataFromDOM)
    const gridContainers = [
      '[role="grid"]',
      'table.waffle',
      '.grid-container',
      'table'
    ];

    let gridContainer = null;
    for (const selector of gridContainers) {
      const container = document.querySelector(selector);
      if (container) {
        gridContainer = container;
        console.log(`[SheetGPT] Highlight: found grid container "${selector}"`);
        break;
      }
    }

    if (!gridContainer) {
      throw new Error('Не найден контейнер таблицы');
    }

    // Try multiple selector strategies (same as readSheetDataFromDOM)
    const selectorStrategies = [
      { rows: '[role="row"]', cells: '[role="gridcell"]' },
      { rows: 'tbody tr, tr', cells: 'td' },
      { rows: '.grid-row, .ritz .grid-row', cells: '.cell, [role="gridcell"]' },
      { rows: 'tr', cells: 'td, [role="gridcell"]' }
    ];

    let allRows = [];
    let cellSelector = null;

    // Find rows using any working strategy WITHIN the grid container
    for (const strategy of selectorStrategies) {
      const foundRows = gridContainer.querySelectorAll(strategy.rows);
      console.log(`[SheetGPT] Highlight: trying "${strategy.rows}" in grid → ${foundRows.length} rows`);

      if (foundRows.length > 0) {
        allRows = Array.from(foundRows);
        cellSelector = strategy.cells;
        console.log(`[SheetGPT] ✅ Highlight using: rows="${strategy.rows}", cells="${strategy.cells}"`);
        break;
      }
    }

    if (allRows.length > 0) {
      // Highlight specified rows (rowIndices are 1-based, where 1=headers, 2=first data row)
      rowIndices.forEach(rowIndex => {
        // Convert to 0-based index for DOM
        const domIndex = rowIndex - 1;

        if (domIndex >= 0 && domIndex < allRows.length) {
          const row = allRows[domIndex];

          // Apply background color to all cells in the row
          const cells = row.querySelectorAll(cellSelector);
          console.log(`[SheetGPT] Row ${rowIndex}: found ${cells.length} cells`);

          cells.forEach(cell => {
            cell.style.backgroundColor = bgColor;
          });

          highlightedCount++;
          console.log(`[SheetGPT] ✅ Highlighted row ${rowIndex} (DOM index ${domIndex})`);
        }
      });
    }

    if (highlightedCount === 0) {
      throw new Error('Не удалось найти строки для подсветки в DOM');
    }

    console.log(`[SheetGPT] ✅ Total highlighted: ${highlightedCount} rows`);
    return {
      success: true,
      message: `Выделено строк: ${rowIndices.join(', ')}`
    };

  } catch (error) {
    console.error('[SheetGPT] Error highlighting rows in DOM:', error);
    return {
      success: false,
      message: `Ошибка выделения: ${error.message}`
    };
  }
}

async function highlightRows(rows, color) {
  console.log('[SheetGPT] Highlight rows:', rows, 'with color', color);

  try {
    // Convert color name to RGB
    const rgbColor = convertColorNameToRGB(color);

    // Get current sheet name (fallback to Sheet1)
    const sheetName = 'Sheet1'; // TODO: Get actual active sheet name

    // Highlight rows via Sheets API
    const response = await chrome.runtime.sendMessage({
      action: 'HIGHLIGHT_ROWS',
      data: {
        sheetName,
        rowIndices: rows,
        color: rgbColor
      }
    });

    if (!response.success) {
      throw new Error(response.error);
    }

    console.log('[SheetGPT] ✅ Rows highlighted via API:', response.result);
    return {
      success: true,
      message: `Выделено строк: ${rows.join(', ')}`
    };
  } catch (error) {
    console.error('[SheetGPT] Error highlighting rows:', error);
    return {
      success: false,
      message: `Ошибка выделения строк: ${error.message}`
    };
  }
}

// Helper function to convert structured data to 2D array
function convertStructuredDataToValues(structuredData) {
  console.log('[SheetGPT] Converting structured data:', structuredData);

  if (!structuredData) {
    throw new Error('Invalid structured data format: data is null or undefined');
  }

  // Backend returns format: { headers: [...], rows: [[...], [...]], ... }
  if (structuredData.headers && structuredData.rows) {
    console.log('[SheetGPT] Using headers/rows format');
    return [structuredData.headers, ...structuredData.rows];
  }

  // Alternative format: { columns: [...], data: [...] }
  if (structuredData.columns && structuredData.data) {
    console.log('[SheetGPT] Using columns/data format');
    const { columns, data } = structuredData;

    // Create header row
    const headers = columns.map(col => col.name || col);

    // Create data rows
    const rows = data.map(row => {
      return columns.map(col => {
        const colName = col.name || col;
        return row[colName] !== undefined ? row[colName] : '';
      });
    });

    return [headers, ...rows];
  }

  throw new Error(`Invalid structured data format. Expected {headers, rows} or {columns, data}, got: ${JSON.stringify(Object.keys(structuredData))}`);
}

// Helper function to convert color name to RGB
function convertColorNameToRGB(colorName) {
  const colorMap = {
    'yellow': { red: 1, green: 1, blue: 0.8 },
    'green': { red: 0.8, green: 1, blue: 0.8 },
    'red': { red: 1, green: 0.8, blue: 0.8 },
    'blue': { red: 0.8, green: 0.9, blue: 1 },
    'orange': { red: 1, green: 0.9, blue: 0.7 }
  };

  return colorMap[colorName?.toLowerCase()] || colorMap['yellow'];
}
