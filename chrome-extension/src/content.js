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

async function getActiveSheetData() {
  console.log('[SheetGPT] Getting active sheet data via Sheets API...');

  try {
    const response = await chrome.runtime.sendMessage({
      action: 'GET_SHEET_DATA'
    });

    if (!response) {
      throw new Error('Нет ответа от background script. Перезагрузите расширение в chrome://extensions');
    }

    if (!response.success) {
      throw new Error(response.error || 'API вернул ошибку');
    }

    console.log('[SheetGPT] ✅ Got data from Sheets API:', response.result);
    return response.result;

  } catch (error) {
    console.error('[SheetGPT] ❌ Sheets API error:', error);
    throw new Error(`Ошибка чтения данных: ${error.message}`);
  }
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
