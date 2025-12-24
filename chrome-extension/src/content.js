/**
 * SheetGPT Chrome Extension - Content Script
 * Инжектит sidebar в Google Sheets
 *
 * v7.9.4: Added extension context validation and auto-recovery
 */

console.log('[SheetGPT] Content script loaded');

// v12.0: Deduplication - prevent processing same message twice
const processedMessageIds = new Set();
const MAX_PROCESSED_IDS = 100; // Limit memory usage

// Debug: expose function to test activation from console
window.testSheetGPTActivation = function(key) {
  const iframe = document.getElementById('sheetgpt-sidebar-iframe');
  if (iframe && iframe.contentWindow) {
    console.log('[SheetGPT] Sending test activation to sidebar...');
    iframe.contentWindow.postMessage({ type: 'DEBUG_ACTIVATE', key: key || 'TEST-TEST-TEST-TEST' }, '*');
  } else {
    console.error('[SheetGPT] Sidebar iframe not found!');
  }
};

window.checkSheetGPTSidebar = function() {
  const iframe = document.getElementById('sheetgpt-sidebar-iframe');
  const container = document.getElementById('sheetgpt-sidebar-container');
  console.log('[SheetGPT] Debug info:', {
    containerExists: !!container,
    iframeExists: !!iframe,
    iframeSrc: iframe?.src,
    containerTransform: container?.style.transform
  });
};

// v7.9.4: Check if extension context is valid
function isExtensionContextValid() {
  try {
    // Try to access chrome.runtime.id - this will throw if context is invalid
    return !!(chrome.runtime && chrome.runtime.id);
  } catch (e) {
    return false;
  }
}

// v11.3: Get current active sheet name from DOM (not cached)
function getCurrentSheetNameFromDOM() {
  // Helper to clean sheet name from hidden characters
  function cleanSheetName(name) {
    if (!name) return null;
    // Remove all non-printable characters and control characters
    // Keep only letters, numbers, spaces, and common punctuation
    const cleaned = name.replace(/[^\p{L}\p{N}\s\-_.,!()]/gu, '').trim();
    console.log('[SheetGPT] 🧹 Cleaned sheet name:', JSON.stringify(name), '->', JSON.stringify(cleaned));
    return cleaned || null;
  }

  // Method 1: Find active tab with specific class and get the tab name element
  const activeTab = document.querySelector('.docs-sheet-tab.docs-sheet-active-tab');
  if (activeTab) {
    // Look for the tab name element inside (it has the actual visible text)
    const tabNameEl = activeTab.querySelector('.docs-sheet-tab-name');
    if (tabNameEl) {
      const name = cleanSheetName(tabNameEl.textContent);
      if (name) {
        console.log('[SheetGPT] 📋 Active sheet from tab-name element:', name);
        return name;
      }
    }
    // Fallback: get innerText which excludes hidden elements
    const name = cleanSheetName(activeTab.innerText);
    if (name) {
      console.log('[SheetGPT] 📋 Active sheet from innerText:', name);
      return name;
    }
  }

  // Method 2: Find tab with aria-selected
  const selectedTab = document.querySelector('[role="tab"][aria-selected="true"]');
  if (selectedTab) {
    const tabNameEl = selectedTab.querySelector('.docs-sheet-tab-name');
    if (tabNameEl) {
      const name = cleanSheetName(tabNameEl.textContent);
      if (name) {
        console.log('[SheetGPT] 📋 Active sheet from aria-selected tab-name:', name);
        return name;
      }
    }
    const name = cleanSheetName(selectedTab.innerText);
    if (name) {
      console.log('[SheetGPT] 📋 Active sheet from aria-selected innerText:', name);
      return name;
    }
  }

  // Method 3: Look in sheet tabs container
  const tabsContainer = document.querySelector('.docs-sheet-tab-container');
  if (tabsContainer) {
    const tabs = tabsContainer.querySelectorAll('.docs-sheet-tab');
    for (const tab of tabs) {
      if (tab.classList.contains('docs-sheet-active-tab')) {
        const tabNameEl = tab.querySelector('.docs-sheet-tab-name');
        if (tabNameEl) {
          const name = cleanSheetName(tabNameEl.textContent);
          if (name) {
            console.log('[SheetGPT] 📋 Active sheet from container tab-name:', name);
            return name;
          }
        }
        const name = cleanSheetName(tab.innerText);
        if (name) {
          console.log('[SheetGPT] 📋 Active sheet from container innerText:', name);
          return name;
        }
      }
    }
  }

  console.log('[SheetGPT] ⚠️ Could not determine active sheet from DOM');
  return null;
}

// v7.9.4: Show reload notification when context is invalidated
function showReloadNotification() {
  // Remove existing notification if present
  const existing = document.getElementById('sheetgpt-reload-notification');
  if (existing) existing.remove();

  const notification = document.createElement('div');
  notification.id = 'sheetgpt-reload-notification';
  notification.innerHTML = `
    <div style="
      position: fixed;
      top: 20px;
      right: 20px;
      background: linear-gradient(135deg, #6366F1 0%, #A855F7 100%);
      color: white;
      padding: 16px 20px;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
      z-index: 9999999;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      max-width: 320px;
      animation: slideIn 0.3s ease;
    ">
      <style>
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      </style>
      <div style="font-weight: 600; margin-bottom: 8px; font-size: 14px;">
        🔄 SheetGPT обновился
      </div>
      <div style="font-size: 13px; opacity: 0.95; margin-bottom: 12px;">
        Расширение было обновлено. Перезагрузите страницу для продолжения работы.
      </div>
      <button id="sheetgpt-reload-btn" style="
        background: white;
        color: #6366F1;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        font-size: 13px;
        transition: transform 0.2s;
      ">
        Перезагрузить страницу
      </button>
      <button id="sheetgpt-dismiss-btn" style="
        background: transparent;
        color: white;
        border: 1px solid rgba(255,255,255,0.3);
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
        margin-left: 8px;
      ">
        Позже
      </button>
    </div>
  `;

  document.body.appendChild(notification);

  // Add event listeners
  document.getElementById('sheetgpt-reload-btn')?.addEventListener('click', () => {
    window.location.reload();
  });

  document.getElementById('sheetgpt-dismiss-btn')?.addEventListener('click', () => {
    notification.remove();
  });
}

// v7.9.4: Wrap chrome.runtime.sendMessage with context check
async function safeSendMessage(message) {
  if (!isExtensionContextValid()) {
    console.warn('[SheetGPT] Extension context invalidated, showing reload notification');
    showReloadNotification();
    throw new Error('Extension context invalidated. Please reload the page.');
  }

  try {
    return await chrome.runtime.sendMessage(message);
  } catch (error) {
    if (error.message?.includes('Extension context invalidated') ||
        error.message?.includes('context invalidated')) {
      console.warn('[SheetGPT] Extension context invalidated during sendMessage');
      showReloadNotification();
      throw new Error('Extension context invalidated. Please reload the page.');
    }
    throw error;
  }
}

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

  // Log iframe loading
  iframe.addEventListener('load', () => {
    console.log('[SheetGPT] ✅ Sidebar iframe loaded successfully');
  });

  iframe.addEventListener('error', (e) => {
    console.error('[SheetGPT] ❌ Sidebar iframe failed to load:', e);
  });

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

    // Отправляем запрос в SheetGPT API (CleanAnalyst v1.0)
    const response = await fetch('https://sheetgpt-production.up.railway.app/api/v1/analyze', {
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
    // v7.9.4: Use safeSendMessage to handle context invalidation
    const response = await safeSendMessage({
      action: 'GET_SHEET_DATA'
    });

    if (!response) {
      throw new Error('Нет ответа от background script. Перезагрузите страницу (F5)');
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

  // Handle SAVE_CONTEXT message from sidebar
  if (event.data && event.data.type === 'SHEETGPT_SAVE_CONTEXT') {
    console.log('[SheetGPT] 💾 Saving context to chrome.storage:', event.data.context);
    try {
      await chrome.storage.local.set({ customContext: event.data.context });
      console.log('[SheetGPT] ✅ Context saved to chrome.storage');
    } catch (e) {
      console.error('[SheetGPT] Failed to save context:', e);
    }
    return;
  }

  // Handle OVERWRITE_SHEET_DATA message from sidebar (VLOOKUP results)
  if (event.data && event.data.type === 'OVERWRITE_SHEET_DATA') {
    console.log('[SheetGPT] 📝 Overwriting sheet data:', event.data.data);
    try {
      await overwriteSheetData(event.data.data);
      event.source.postMessage({
        type: 'OVERWRITE_SHEET_DATA_RESPONSE',
        success: true
      }, event.origin);
      console.log('[SheetGPT] ✅ Sheet data overwritten successfully');
    } catch (e) {
      console.error('[SheetGPT] ❌ Failed to overwrite sheet data:', e);
      event.source.postMessage({
        type: 'OVERWRITE_SHEET_DATA_RESPONSE',
        success: false,
        error: e.message
      }, event.origin);
    }
    return;
  }

  // v10.1.1: Handle APPEND_COLUMN_BY_KEY message from sidebar (VLOOKUP - add column to the right)
  if (event.data && event.data.type === 'APPEND_COLUMN_BY_KEY') {
    console.log('[SheetGPT] 🔗 VLOOKUP: Appending column by key:', event.data.data);
    try {
      const result = await appendColumnByKey(event.data.data);
      event.source.postMessage({
        type: 'APPEND_COLUMN_BY_KEY_RESPONSE',
        success: true,
        result: result
      }, event.origin);
      console.log('[SheetGPT] ✅ Column appended successfully');
    } catch (e) {
      console.error('[SheetGPT] ❌ Failed to append column:', e);
      event.source.postMessage({
        type: 'APPEND_COLUMN_BY_KEY_RESPONSE',
        success: false,
        error: e.message
      }, event.origin);
    }
    return;
  }

  // v11.1: Handle FILL_COLUMN message from sidebar (direct column write without key matching)
  if (event.data && event.data.type === 'FILL_COLUMN') {
    console.log('[SheetGPT] 📝 FILL_COLUMN: Writing values to column:', event.data.data);
    try {
      const result = await fillColumnDirect(event.data.data);
      event.source.postMessage({
        type: 'FILL_COLUMN_RESPONSE',
        success: true,
        result: result
      }, event.origin);
      console.log('[SheetGPT] ✅ Column filled successfully');
    } catch (e) {
      console.error('[SheetGPT] ❌ Failed to fill column:', e);
      event.source.postMessage({
        type: 'FILL_COLUMN_RESPONSE',
        success: false,
        error: e.message
      }, event.origin);
    }
    return;
  }

  // v11.3: Handle FILL_COLUMNS message from sidebar (multiple columns at once)
  if (event.data && event.data.type === 'FILL_COLUMNS') {
    console.log('[SheetGPT] 📝 FILL_COLUMNS: Writing values to multiple columns:', event.data.data);
    try {
      const result = await fillColumnsDirect(event.data.data);
      event.source.postMessage({
        type: 'FILL_COLUMNS_RESPONSE',
        success: true,
        result: result
      }, event.origin);
      console.log('[SheetGPT] ✅ All columns filled successfully');
    } catch (e) {
      console.error('[SheetGPT] ❌ Failed to fill columns:', e);
      event.source.postMessage({
        type: 'FILL_COLUMNS_RESPONSE',
        success: false,
        error: e.message
      }, event.origin);
    }
    return;
  }

  // Verify it's a message from our sidebar (has our message structure)
  if (!event.data || typeof event.data !== 'object' || !event.data.action || !event.data.messageId) {
    console.log('[SheetGPT] Ignoring message - not from sidebar (missing action or messageId)');
    return;
  }

  const { action, data, messageId } = event.data;

  // v12.0: Deduplication - skip if already processed
  if (processedMessageIds.has(messageId)) {
    console.log('[SheetGPT] ⏭️ Skipping duplicate message:', messageId);
    return;
  }
  processedMessageIds.add(messageId);
  // Cleanup old messageIds to prevent memory leak
  if (processedMessageIds.size > MAX_PROCESSED_IDS) {
    const idsArray = Array.from(processedMessageIds);
    processedMessageIds.clear();
    idsArray.slice(-50).forEach(id => processedMessageIds.add(id));
  }

  console.log('[SheetGPT] ✅ Processing action:', action, 'messageId:', messageId, 'data:', data);

  try {
    let result;

    switch (action) {
      case 'PROCESS_QUERY':
        result = await processQuery(data.query, data.history, data.licenseKey, data.referenceSheet);
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

      case 'SORT_RANGE':
        result = await sortRangeInSheet(data.columnIndex, data.sortOrder);
        break;

      case 'FREEZE_ROWS':
        result = await freezeRowsInSheet(data.freezeRows, data.freezeColumns);
        break;

      case 'FORMAT_ROW':
        result = await formatRowInSheet(data.rowIndex, data.bold, data.backgroundColor);
        break;

      case 'CREATE_CHART':
        console.log('[SheetGPT] 📊 CREATE_CHART received with spec:', JSON.stringify(data.chartSpec));
        result = await createChartInSheet(data.chartSpec);
        console.log('[SheetGPT] 📊 CREATE_CHART result:', result);
        break;

      case 'APPLY_CONDITIONAL_FORMAT':
        result = await applyConditionalFormat(data.rule);
        break;

      case 'APPLY_COLOR_SCALE':
        console.log('[SheetGPT] 🎨 APPLY_COLOR_SCALE received with rule:', JSON.stringify(data.rule));
        result = await applyColorScaleInSheet(data.rule);
        console.log('[SheetGPT] 🎨 APPLY_COLOR_SCALE result:', result);
        break;

      case 'OVERWRITE_SHEET_DATA':
        result = await overwriteSheetData(data.cleanedData);
        break;

      case 'SET_DATA_VALIDATION':
        result = await setDataValidationInSheet(data.rule);
        break;

      case 'CONVERT_TO_NUMBERS':
        console.log('[SheetGPT] 🔢 CONVERT_TO_NUMBERS received:', data);
        result = await convertColumnToNumbersInSheet(data.columnIndex, data.columnName, data.rowCount);
        console.log('[SheetGPT] 🔢 CONVERT_TO_NUMBERS result:', result);
        break;

      case 'CREATE_NEW_SHEET_WITH_DATA':
        console.log('[SheetGPT] 📋 CREATE_NEW_SHEET_WITH_DATA received:', data);
        result = await createNewSheetWithData(data.sheetName, data.structuredData);
        console.log('[SheetGPT] 📋 CREATE_NEW_SHEET_WITH_DATA result:', result);
        break;

      case 'GET_SHEET_DATA_FOR_UNDO':
        console.log('[SheetGPT] 📸 GET_SHEET_DATA_FOR_UNDO - saving snapshot');
        result = await getSheetDataForUndo();
        break;

      case 'RESTORE_SHEET_DATA':
        console.log('[SheetGPT] ↩️ RESTORE_SHEET_DATA - restoring snapshot, data:', data);
        // Handle different nesting levels: data.data.data or data.data or data
        const snapshot = data?.data?.data || data?.data || data;
        console.log('[SheetGPT] ↩️ Extracted snapshot:', snapshot);
        result = await restoreSheetData(snapshot);
        break;

      case 'WRITE_CELL_VALUE':
        console.log('[SheetGPT] ✏️ WRITE_CELL_VALUE - writing to cell:', data.targetCell, 'value:', data.value);
        result = await writeCellValue(data.targetCell, data.value);
        break;

      case 'ADD_FORMULA_COLUMN':
        console.log('[SheetGPT] ➕ ADD_FORMULA_COLUMN - adding column:', data.columnName, 'formula:', data.formulaTemplate);
        result = await addFormulaColumn(data.columnName, data.formulaTemplate, data.rowCount, data.targetColumn);
        break;

      case 'CLEAR_ROW_COLORS':
        console.log('[SheetGPT] ↩️ CLEAR_ROW_COLORS - clearing highlight from rows:', data.rows);
        result = await clearRowColors(data.rows, data.sheetName);
        break;

      case 'DELETE_COLUMN':
        console.log('[SheetGPT] ↩️ DELETE_COLUMN - deleting column:', data.column);
        result = await deleteColumn(data.column, data.sheetName);
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

// ===== API CONFIGURATION =====
// Set to 'local' to test with local server (http://localhost:8000)
// Set to 'production' for Railway server
const API_MODE = 'production';  // Change to 'production' for Railway server

const API_URLS = {
  local: 'http://localhost:8000/api/v1/analyze',
  production: 'https://sheetgpt-production.up.railway.app/api/v1/analyze'
};

// ===== API HANDLERS =====

async function processQuery(query, history = [], licenseKey = null, referenceSheet = null) {
  console.log('[SheetGPT] Processing query:', query);
  console.log('[SheetGPT] API Mode:', API_MODE, '| URL:', API_URLS[API_MODE]);
  console.log('[SheetGPT] 🔍 referenceSheet param:', referenceSheet);
  if (referenceSheet) {
    console.log('[SheetGPT] ✅ Reference sheet:', referenceSheet.name, 'with', referenceSheet.headers?.length, 'cols');
  } else {
    console.log('[SheetGPT] ❌ No reference sheet');
  }

  // v7.9.4: Check context before any operations
  if (!isExtensionContextValid()) {
    showReloadNotification();
    throw new Error('Extension context invalidated. Please reload the page.');
  }

  // Get data from active sheet (TODO: implement real sheet reading)
  const sheetData = await getActiveSheetData();

  // v11.5: Detect CSV data and handle locally (avoid GPT token limits)
  const csvSplitPatterns = ['разбей', 'разделить', 'split', 'разбить'];
  const isCsvSplitQuery = csvSplitPatterns.some(p => query.toLowerCase().includes(p));

  if (isCsvSplitQuery && sheetData.headers.length === 1 && sheetData.data.length > 0) {
    // Check if data looks like CSV (single column with commas)
    const firstRow = sheetData.data[0]?.[0] || '';
    const headerRow = sheetData.headers[0] || '';

    if (headerRow.includes(',') && firstRow.includes(',')) {
      console.log('[SheetGPT] 🔧 Detected CSV data, processing locally...');

      // Split header and data by comma
      const newHeaders = headerRow.split(',').map(h => h.trim());
      const newRows = sheetData.data.map(row => {
        const cell = row[0] || '';
        return cell.split(',').map(v => v.trim());
      });

      console.log('[SheetGPT] 📊 CSV split result:', newHeaders.length, 'columns,', newRows.length, 'rows');

      // Return local result without calling API
      return {
        success: true,
        response_type: 'action',
        action_type: 'replace_data',
        structured_data: {
          headers: newHeaders,
          rows: newRows
        },
        summary: `Данные разбиты: ${newHeaders.length} колонок × ${newRows.length} строк`,
        methodology: {
          name: 'csv_split',
          reason: 'Данные были в формате CSV (разделитель - запятая). Разбивка выполнена локально.',
          formula: 'SPLIT(A1, ",")'
        }
      };
    }
  }

  // Get custom context from storage (v7.9.4: with context check)
  let customContext = '';
  try {
    const result = await chrome.storage.local.get('customContext');
    customContext = result.customContext;
  } catch (e) {
    if (e.message?.includes('Extension context invalidated')) {
      showReloadNotification();
      throw new Error('Extension context invalidated. Please reload the page.');
    }
  }

  // Call SheetGPT API (v9.1.0: with license key for subscription enforcement)
  const headers = {
    'Content-Type': 'application/json',
  };

  // Add license key header if available
  if (licenseKey) {
    headers['X-License-Key'] = licenseKey;
    console.log('[SheetGPT] Sending request with license key');
  }

  // DEBUG: Log what we're sending to backend
  console.log('[SheetGPT] 📤 Sending to backend:');
  console.log('[SheetGPT] 📤 column_names:', sheetData.headers);
  console.log('[SheetGPT] 📤 sheet_data first row:', sheetData.data[0]);
  console.log('[SheetGPT] 📤 sheet_data rows:', sheetData.data.length);
  // v10.0.9: Log reference sheet data being sent
  if (referenceSheet) {
    console.log('[SheetGPT] 📤 reference_sheet_name:', referenceSheet.name);
    console.log('[SheetGPT] 📤 reference_sheet_headers:', referenceSheet.headers);
    console.log('[SheetGPT] 📤 reference_sheet_data rows:', referenceSheet.data?.length);
  } else {
    console.log('[SheetGPT] 📤 reference_sheet: NOT SENDING (null)');
  }

  const response = await fetch(API_URLS[API_MODE], {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({
      query: query,
      column_names: sheetData.headers,
      sheet_data: sheetData.data,
      custom_context: customContext || null,
      history: history || [],
      // v9.2.0: Cross-sheet VLOOKUP support
      reference_sheet_name: referenceSheet?.name || null,
      reference_sheet_headers: referenceSheet?.headers || null,
      reference_sheet_data: referenceSheet?.data || null
    })
  });

  if (!response.ok) {
    // v9.1.0: Handle rate limit (429) specially
    if (response.status === 429) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || 'Дневной лимит запросов исчерпан. Обновите план до PRO.');
    }
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const result = await response.json();
  console.log('[SheetGPT] 📥 API Response:', JSON.stringify(result, null, 2));
  console.log('[SheetGPT] 📥 Has chart_spec?', !!result.chart_spec, result.chart_spec);
  return result;
}

async function getCustomContext() {
  // v7.9.4: Context validation
  if (!isExtensionContextValid()) {
    showReloadNotification();
    throw new Error('Extension context invalidated. Please reload the page.');
  }
  try {
    const { customContext } = await chrome.storage.local.get('customContext');
    return customContext || '';
  } catch (e) {
    if (e.message?.includes('Extension context invalidated')) {
      showReloadNotification();
      throw new Error('Extension context invalidated. Please reload the page.');
    }
    throw e;
  }
}

async function saveCustomContext(context) {
  // v7.9.4: Context validation
  if (!isExtensionContextValid()) {
    showReloadNotification();
    throw new Error('Extension context invalidated. Please reload the page.');
  }
  try {
    await chrome.storage.local.set({ customContext: context });
    return { success: true, message: 'Настройки сохранены' };
  } catch (e) {
    if (e.message?.includes('Extension context invalidated')) {
      showReloadNotification();
      throw new Error('Extension context invalidated. Please reload the page.');
    }
    throw e;
  }
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
  console.log('[SheetGPT] Create table and chart called');
  console.log('[SheetGPT] structuredData:', JSON.stringify(structuredData, null, 2));

  try {
    // v9.0.2: Enhanced validation
    if (!structuredData) {
      throw new Error('structuredData is null or undefined');
    }

    console.log('[SheetGPT] structuredData keys:', Object.keys(structuredData));
    console.log('[SheetGPT] headers:', structuredData.headers);
    console.log('[SheetGPT] rows:', structuredData.rows);
    console.log('[SheetGPT] rows count:', structuredData.rows?.length);

    // v9.0.2: Validate that we have actual data to write
    if (!structuredData.headers || !Array.isArray(structuredData.headers) || structuredData.headers.length === 0) {
      throw new Error('No headers in structured data');
    }

    if (!structuredData.rows || !Array.isArray(structuredData.rows)) {
      throw new Error('No rows array in structured data');
    }

    if (structuredData.rows.length === 0) {
      console.warn('[SheetGPT] ⚠️ Warning: rows array is empty, creating sheet with headers only');
    }

    // Convert structured data to 2D array
    const values = convertStructuredDataToValues(structuredData);
    console.log('[SheetGPT] Converted values:', values);
    console.log('[SheetGPT] Values length:', values.length);

    // v9.0.2: Double-check values before sending
    if (!values || values.length === 0) {
      throw new Error('Converted values array is empty');
    }

    // Get spreadsheet ID and active sheet name
    const match = window.location.href.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
    if (!match) {
      throw new Error('Could not get spreadsheet ID from URL');
    }
    const spreadsheetId = match[1];

    // v11.2: Get active sheet name from DOM (not cached) to ensure we write to correct sheet
    let sheetName = getCurrentSheetNameFromDOM();
    if (!sheetName) {
      // Fallback to cached name if DOM detection fails
      const storageKey = `sheetName_${spreadsheetId}`;
      const storage = await chrome.storage.local.get([storageKey]);
      sheetName = storage[storageKey];
    }
    if (!sheetName) {
      throw new Error('Could not get active sheet name. Try refreshing the page.');
    }
    console.log('[SheetGPT] 📋 Will write to sheet:', sheetName);

    // v10.0.4: Respect display_mode - create new sheet or overwrite current
    // 'create_sheet' and 'preview' both create new sheets (to avoid overwriting data)
    if (structuredData.display_mode === 'create_sheet' || structuredData.display_mode === 'preview') {
      // Generate unique sheet name based on headers or timestamp
      const newSheetName = structuredData.headers[0] + '_' + new Date().toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
      console.log('[SheetGPT] 📋 display_mode=' + structuredData.display_mode + ', creating new sheet:', newSheetName);

      const response = await safeSendMessage({
        action: 'CREATE_NEW_SHEET',
        data: {
          sheetTitle: newSheetName,
          values: values
        }
      });

      if (!response.success) {
        throw new Error(response.error);
      }

      console.log('[SheetGPT] ✅ New sheet created:', response.result);
      return {
        success: true,
        message: `Создан новый лист "${newSheetName}" (${values.length - 1} строк)`
      };
    }

    // Default: write to current sheet
    console.log('[SheetGPT] Writing table to current sheet:', sheetName);
    const response = await safeSendMessage({
      action: 'WRITE_SHEET_DATA',
      data: {
        sheetName: sheetName,
        values: values,
        startCell: 'A1',
        mode: 'overwrite'
      }
    });

    if (!response.success) {
      throw new Error(response.error);
    }

    console.log('[SheetGPT] ✅ Table created:', response.result);
    return {
      success: true,
      message: `Данные вставлены в лист "${sheetName}" (${response.result?.updatedRows || values.length} строк)`
    };
  } catch (error) {
    console.error('[SheetGPT] Error creating table:', error);
    return {
      success: false,
      message: `Ошибка создания таблицы: ${error.message}`
    };
  }
}

/**
 * Create a NEW sheet and write data to it (does not overwrite current sheet!)
 * Used for pivot tables and summaries that should not replace existing data
 */
async function createNewSheetWithData(newSheetName, structuredData) {
  console.log('[SheetGPT] 📋 Creating NEW sheet with data:', newSheetName);
  console.log('[SheetGPT] structuredData:', JSON.stringify(structuredData, null, 2));

  try {
    if (!structuredData) {
      throw new Error('structuredData is null or undefined');
    }

    if (!structuredData.headers || !Array.isArray(structuredData.headers) || structuredData.headers.length === 0) {
      throw new Error('No headers in structured data');
    }

    if (!structuredData.rows || !Array.isArray(structuredData.rows)) {
      throw new Error('No rows array in structured data');
    }

    // Convert structured data to 2D array
    const values = convertStructuredDataToValues(structuredData);
    console.log('[SheetGPT] Converted values:', values);

    if (!values || values.length === 0) {
      throw new Error('Converted values array is empty');
    }

    // CREATE_NEW_SHEET creates sheet AND writes data in one call
    console.log('[SheetGPT] Creating new sheet and writing data:', newSheetName);
    let response = await safeSendMessage({
      action: 'CREATE_NEW_SHEET',
      data: {
        sheetTitle: newSheetName,
        values: values
      }
    });

    // If sheet already exists, try with a unique name
    if (!response.success && response.error?.includes('already exists')) {
      const uniqueName = `${newSheetName} (${Date.now()})`;
      console.log('[SheetGPT] Sheet exists, trying unique name:', uniqueName);
      response = await safeSendMessage({
        action: 'CREATE_NEW_SHEET',
        data: {
          sheetTitle: uniqueName,
          values: values
        }
      });
      if (response.success) {
        newSheetName = uniqueName;
      }
    }

    if (!response.success) {
      throw new Error(response.error);
    }

    console.log('[SheetGPT] ✅ New sheet created with data:', response.result);
    return {
      success: true,
      message: `Сводная таблица создана на новом листе "${newSheetName}" (${response.result?.rowsWritten || values.length} строк)`
    };
  } catch (error) {
    console.error('[SheetGPT] Error creating new sheet with data:', error);
    return {
      success: false,
      message: `Ошибка создания листа: ${error.message}`
    };
  }
}

/**
 * Get current sheet data for undo snapshot
 * Returns all values and formatting from current sheet
 */
async function getSheetDataForUndo() {
  console.log('[SheetGPT] 📸 Getting sheet data for undo...');

  try {
    // Get spreadsheet ID
    const match = window.location.href.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
    if (!match) {
      throw new Error('Could not get spreadsheet ID from URL');
    }
    const spreadsheetId = match[1];

    // Get current sheet name from storage
    const storageKey = `sheetName_${spreadsheetId}`;
    const storage = await chrome.storage.local.get([storageKey]);
    const sheetName = storage[storageKey];
    if (!sheetName) {
      throw new Error('Could not get active sheet name');
    }

    // Get sheet data via background script
    const response = await safeSendMessage({
      action: 'GET_SHEET_DATA'
    });

    if (!response.success) {
      throw new Error(response.error || 'Failed to get sheet data');
    }

    // GET_SHEET_DATA returns { headers, data }, not { headers, values }
    // For undo we need the raw data rows including headers
    const rawData = response.result.data || [];
    const headers = response.result.headers || [];

    // Combine headers + data for full restore
    const allValues = [headers, ...rawData];

    console.log('[SheetGPT] ✅ Snapshot captured:', allValues.length, 'rows (including header)');
    return {
      success: true,
      data: {
        sheetName: sheetName,
        values: allValues,
        headers: headers
      }
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ Error getting sheet data for undo:', error);
    return {
      success: false,
      message: error.message
    };
  }
}

/**
 * Restore sheet data from undo snapshot
 * @param {Object} snapshot - The saved sheet state
 */
async function restoreSheetData(snapshot) {
  console.log('[SheetGPT] ↩️ Restoring sheet data...');

  try {
    if (!snapshot || !snapshot.values) {
      throw new Error('Invalid snapshot data');
    }

    const sheetName = snapshot.sheetName;
    const values = snapshot.values;

    console.log('[SheetGPT] Restoring to sheet:', sheetName, 'with', values.length, 'rows');

    // Write data back to sheet
    const response = await safeSendMessage({
      action: 'WRITE_SHEET_DATA',
      data: {
        sheetName: sheetName,
        values: values,
        startCell: 'A1',
        mode: 'overwrite'
      }
    });

    if (!response.success) {
      throw new Error(response.error || 'Failed to restore data');
    }

    console.log('[SheetGPT] ✅ Sheet data restored successfully');
    return {
      success: true,
      message: `Данные восстановлены (${values.length} строк)`
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ Error restoring sheet data:', error);
    return {
      success: false,
      message: error.message
    };
  }
}

/**
 * Clear background color from specified rows (for highlight undo)
 * @param {Array} rows - Row numbers to clear (1-indexed)
 * @param {string} sheetName - Name of the sheet
 */
async function clearRowColors(rows, sheetName) {
  console.log('[SheetGPT] ↩️ Clearing colors from rows:', rows);

  try {
    if (!rows || rows.length === 0) {
      return { success: true, message: 'No rows to clear' };
    }

    const response = await safeSendMessage({
      action: 'CLEAR_ROW_COLORS',
      data: {
        sheetName: sheetName || 'Sheet1',
        rowIndices: rows
      }
    });

    if (!response.success) {
      throw new Error(response.error || 'Failed to clear row colors');
    }

    console.log('[SheetGPT] ✅ Row colors cleared');
    return {
      success: true,
      message: `Цвет убран с ${rows.length} строк`
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ Error clearing row colors:', error);
    return {
      success: false,
      message: error.message
    };
  }
}

/**
 * Delete a column from the sheet
 * @param {string} column - Column letter (e.g., "M")
 * @param {string} sheetName - Name of the sheet
 */
async function deleteColumn(column, sheetName) {
  console.log('[SheetGPT] ↩️ Deleting column:', column);

  try {
    if (!column) {
      return { success: false, message: 'No column specified' };
    }

    const response = await safeSendMessage({
      action: 'DELETE_COLUMN',
      data: {
        sheetName: sheetName || 'Sheet1',
        column: column
      }
    });

    if (!response.success) {
      throw new Error(response.error || 'Failed to delete column');
    }

    console.log('[SheetGPT] ✅ Column deleted');
    return {
      success: true,
      message: `Колонка ${column} удалена`
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ Error deleting column:', error);
    return {
      success: false,
      message: error.message
    };
  }
}

/**
 * Write a single value to a specific cell
 * @param {string} targetCell - Cell address like "B12", "C5"
 * @param {any} value - Value to write
 */
async function writeCellValue(targetCell, value) {
  console.log('[SheetGPT] ✏️ Writing value to cell:', targetCell, value);

  try {
    // Get spreadsheet ID
    const match = window.location.href.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
    if (!match) {
      throw new Error('Could not get spreadsheet ID from URL');
    }
    const spreadsheetId = match[1];

    // Get current sheet name from storage
    const storageKey = `sheetName_${spreadsheetId}`;
    const storage = await chrome.storage.local.get([storageKey]);
    const sheetName = storage[storageKey];
    if (!sheetName) {
      throw new Error('Could not get active sheet name');
    }

    // Build the range - include sheet name for safety
    const range = `${sheetName}!${targetCell}`;
    console.log('[SheetGPT] Writing to range:', range);

    // Write single value via background script
    const response = await safeSendMessage({
      action: 'WRITE_SHEET_DATA',
      data: {
        sheetName: sheetName,
        values: [[value]],  // 2D array with single value
        startCell: targetCell,
        mode: 'overwrite'
      }
    });

    if (!response.success) {
      throw new Error(response.error || 'Failed to write value');
    }

    console.log('[SheetGPT] ✅ Value written successfully to', targetCell);
    return {
      success: true,
      message: `Значение ${value} записано в ячейку ${targetCell}`
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ Error writing cell value:', error);
    return {
      success: false,
      message: error.message
    };
  }
}

/**
 * Add a new column with a formula
 * @param {string} columnName - Name for the new column header
 * @param {string} formulaTemplate - Formula template like "=H{row}+E{row}"
 * @param {number} rowCount - Number of data rows
 */
async function addFormulaColumn(columnName, formulaTemplate, rowCount, targetColumn = null) {
  console.log('[SheetGPT] ➕ Adding formula column:', columnName, formulaTemplate, rowCount, 'target:', targetColumn);

  try {
    // Get spreadsheet ID
    const match = window.location.href.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
    if (!match) {
      throw new Error('Could not get spreadsheet ID from URL');
    }
    const spreadsheetId = match[1];

    // Get current sheet name from storage
    const storageKey = `sheetName_${spreadsheetId}`;
    const storage = await chrome.storage.local.get([storageKey]);
    const sheetName = storage[storageKey];
    if (!sheetName) {
      throw new Error('Could not get active sheet name');
    }

    // Get current sheet data to find the next empty column
    const sheetData = await safeSendMessage({
      action: 'GET_SHEET_DATA'
    });

    console.log('[SheetGPT] sheetData response:', sheetData);

    // GET_SHEET_DATA returns { success: true, result: { headers: [...], data: [...] } }
    if (!sheetData || !sheetData.success || !sheetData.result?.headers) {
      throw new Error('Could not get sheet data');
    }

    // Determine target column
    let targetColLetter;
    let skipHeader = false; // If using existing column, don't overwrite header

    if (targetColumn) {
      // Use specified column
      targetColLetter = targetColumn.toUpperCase();
      console.log('[SheetGPT] Using specified target column:', targetColLetter);
    } else {
      // Check if column with same name already exists
      const headers = sheetData.result.headers;
      const existingColIndex = headers.findIndex(h =>
        h && h.toString().toLowerCase().trim() === columnName.toLowerCase().trim()
      );

      if (existingColIndex >= 0) {
        // Use existing column
        targetColLetter = String.fromCharCode(65 + existingColIndex);
        skipHeader = true; // Don't overwrite existing header
        console.log('[SheetGPT] Found existing column "' + columnName + '" at:', targetColLetter);
      } else {
        // Find next empty column index (after last column with data)
        const numCols = headers.length;
        const nextColIndex = numCols; // 0-indexed, so this is the first empty column
        targetColLetter = String.fromCharCode(65 + nextColIndex); // A=0, B=1, etc.
        console.log('[SheetGPT] Using next empty column:', targetColLetter, 'index:', nextColIndex);
      }
    }

    // Build formula values array:
    // Row 1 = header (columnName) - skip if using existing column
    // Row 2+ = formulas with row numbers replaced
    const formulas = skipHeader ? [] : [[columnName]]; // Header only if new column
    const actualRowCount = rowCount || sheetData.result?.data?.length || 100;
    const startRow = skipHeader ? 2 : 2; // Always start formulas from row 2

    for (let i = startRow; i <= actualRowCount + 1; i++) {
      // Replace {row} placeholder with actual row number
      const formula = formulaTemplate.replace(/\{row\}/g, i.toString());
      formulas.push([formula]);
    }

    console.log('[SheetGPT] Writing formulas to column', targetColLetter, ':', formulas.slice(0, 3), '...');

    // Write the formulas to the new column
    const response = await safeSendMessage({
      action: 'WRITE_SHEET_DATA',
      data: {
        sheetName: sheetName,
        values: formulas,
        startCell: skipHeader ? `${targetColLetter}2` : `${targetColLetter}1`,
        mode: 'overwrite',
        valueInputOption: 'USER_ENTERED' // Important! This interprets formulas
      }
    });

    if (!response.success) {
      throw new Error(response.error || 'Failed to write formulas');
    }

    console.log('[SheetGPT] ✅ Formula column added successfully');
    return {
      success: true,
      message: `Столбец "${columnName}" с формулой добавлен в колонку ${targetColLetter}`,
      column: targetColLetter
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ Error adding formula column:', error);
    return {
      success: false,
      message: error.message
    };
  }
}

async function replaceDataInCurrentSheet(structuredData) {
  console.log('[SheetGPT] Replace data in current sheet:', structuredData);

  try {
    // Convert structured data to 2D array
    const values = convertStructuredDataToValues(structuredData);

    // Get current sheet name (v7.9.4: use safeSendMessage)
    const sheetNameResponse = await safeSendMessage({
      action: 'GET_SHEET_DATA'
    });

    if (!sheetNameResponse.success) {
      throw new Error(sheetNameResponse.error);
    }

    // We need to extract sheet name - for now use "Sheet1" as fallback
    // TODO: Get actual active sheet name from page DOM
    const sheetName = 'Sheet1';

    // Write data to current sheet (v7.9.4: use safeSendMessage)
    const response = await safeSendMessage({
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

    // Highlight rows via Sheets API (v7.9.4: use safeSendMessage)
    const response = await safeSendMessage({
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

async function sortRangeInSheet(columnIndex, sortOrder) {
  console.log('[SheetGPT] Sort range by column:', columnIndex, 'order:', sortOrder);

  try {
    // Sort via Sheets API
    const response = await safeSendMessage({
      action: 'SORT_RANGE',
      data: {
        columnIndex: columnIndex,
        sortOrder: sortOrder  // "ASCENDING" or "DESCENDING"
      }
    });

    if (!response.success) {
      throw new Error(response.error);
    }

    console.log('[SheetGPT] ✅ Range sorted via API:', response.result);
    return {
      success: true,
      message: `Данные отсортированы ${sortOrder === 'DESCENDING' ? 'по убыванию' : 'по возрастанию'}`
    };
  } catch (error) {
    console.error('[SheetGPT] Error sorting range:', error);
    return {
      success: false,
      message: `Ошибка сортировки: ${error.message}`
    };
  }
}

async function freezeRowsInSheet(freezeRows, freezeColumns) {
  console.log('[SheetGPT] Freeze rows:', freezeRows, 'columns:', freezeColumns);

  try {
    const response = await safeSendMessage({
      action: 'FREEZE_ROWS',
      data: {
        freezeRows: freezeRows || 0,
        freezeColumns: freezeColumns || 0
      }
    });

    if (!response.success) {
      throw new Error(response.error);
    }

    console.log('[SheetGPT] ✅ Rows/columns frozen via API:', response.result);

    let message = '';
    if (freezeRows === 0 && freezeColumns === 0) {
      message = 'Закрепление снято';
    } else {
      const parts = [];
      if (freezeRows > 0) parts.push(`${freezeRows} строк`);
      if (freezeColumns > 0) parts.push(`${freezeColumns} столбцов`);
      message = `Закреплено: ${parts.join(' и ')}`;
    }

    return {
      success: true,
      message: message
    };
  } catch (error) {
    console.error('[SheetGPT] Error freezing rows:', error);
    return {
      success: false,
      message: `Ошибка закрепления: ${error.message}`
    };
  }
}

async function formatRowInSheet(rowIndex, bold, backgroundColor) {
  console.log('[SheetGPT] Format row:', rowIndex, 'bold:', bold, 'bg:', backgroundColor);

  try {
    const response = await safeSendMessage({
      action: 'FORMAT_ROW',
      data: {
        rowIndex: rowIndex || 0,
        bold: bold,
        backgroundColor: backgroundColor
      }
    });

    if (!response.success) {
      throw new Error(response.error);
    }

    console.log('[SheetGPT] ✅ Row formatted via API:', response.result);
    return {
      success: true,
      message: 'Заголовки отформатированы'
    };
  } catch (error) {
    console.error('[SheetGPT] Error formatting row:', error);
    return {
      success: false,
      message: `Ошибка форматирования: ${error.message}`
    };
  }
}

async function createChartInSheet(chartSpec) {
  console.log('[SheetGPT] Create chart:', chartSpec);

  try {
    const response = await safeSendMessage({
      action: 'CREATE_CHART',
      data: {
        chartSpec: chartSpec
      }
    });

    if (!response || !response.success) {
      throw new Error(response?.error || 'Неизвестная ошибка при создании диаграммы');
    }

    console.log('[SheetGPT] ✅ Chart created via API:', response.result);
    return {
      success: true,
      message: `Диаграмма "${chartSpec.title || 'Диаграмма'}" создана`
    };
  } catch (error) {
    console.error('[SheetGPT] Error creating chart:', error);
    // Re-throw error so it's properly handled by the message handler
    throw new Error(`Ошибка создания диаграммы: ${error.message}`);
  }
}

async function applyConditionalFormat(rule) {
  console.log('[SheetGPT] Apply conditional format:', rule);

  try {
    const response = await safeSendMessage({
      action: 'APPLY_CONDITIONAL_FORMAT',
      data: {
        rule: rule
      }
    });

    if (!response || !response.success) {
      throw new Error(response?.error || 'Неизвестная ошибка');
    }

    console.log('[SheetGPT] ✅ Conditional format applied via API:', response.result);
    return {
      success: true,
      message: `Условное форматирование применено к колонке "${rule.column_name}"`
    };
  } catch (error) {
    console.error('[SheetGPT] Error applying conditional format:', error);
    throw new Error(`Ошибка условного форматирования: ${error.message}`);
  }
}

async function applyColorScaleInSheet(rule) {
  console.log('[SheetGPT] Apply color scale:', rule);

  try {
    const response = await safeSendMessage({
      action: 'APPLY_COLOR_SCALE',
      data: {
        rule: rule
      }
    });

    if (!response || !response.success) {
      throw new Error(response?.error || 'Неизвестная ошибка при применении цветовой шкалы');
    }

    console.log('[SheetGPT] ✅ Color scale applied via API:', response.result);
    return {
      success: true,
      message: `Цветовая шкала применена к колонке "${rule.column_name}"`
    };
  } catch (error) {
    console.error('[SheetGPT] Error applying color scale:', error);
    throw new Error(`Ошибка применения цветовой шкалы: ${error.message}`);
  }
}

async function overwriteSheetData(cleanedData) {
  console.log('[SheetGPT] Overwrite sheet with cleaned data:', cleanedData);

  try {
    if (!cleanedData || !cleanedData.headers || !cleanedData.rows) {
      throw new Error('Invalid cleaned data format');
    }

    // Get spreadsheet ID from URL
    const match = window.location.href.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);

    if (!match) {
      throw new Error('Could not get spreadsheet ID from URL');
    }
    const spreadsheetId = match[1];

    // Get active sheet name from storage
    const storageKey = `sheetName_${spreadsheetId}`;
    const storage = await chrome.storage.local.get([storageKey]);
    const sheetName = storage[storageKey];
    if (!sheetName) {
      throw new Error('Could not get active sheet name. Try refreshing the page.');
    }

    console.log('[SheetGPT] Writing to sheet:', sheetName);

    // Convert to 2D array
    const values = convertStructuredDataToValues(cleanedData);

    // Write to current sheet (overwrite from A1)
    const response = await safeSendMessage({
      action: 'WRITE_SHEET_DATA',
      data: {
        sheetName: sheetName,
        values: values,
        startCell: 'A1',
        mode: 'overwrite'
      }
    });

    if (!response || !response.success) {
      throw new Error(response?.error || 'Неизвестная ошибка');
    }

    console.log('[SheetGPT] ✅ Data overwritten via API:', response.result);
    return {
      success: true,
      message: `Данные заменены (${values.length - 1} строк)`
    };
  } catch (error) {
    console.error('[SheetGPT] Error overwriting data:', error);
    throw new Error(`Ошибка замены данных: ${error.message}`);
  }
}

async function setDataValidationInSheet(rule) {
  console.log('[SheetGPT] Set data validation:', rule);

  try {
    if (!rule || !rule.allowed_values || rule.allowed_values.length === 0) {
      throw new Error('Invalid validation rule');
    }

    const response = await safeSendMessage({
      action: 'SET_DATA_VALIDATION',
      data: {
        rule: rule
      }
    });

    if (!response || !response.success) {
      throw new Error(response?.error || 'Неизвестная ошибка');
    }

    console.log('[SheetGPT] ✅ Data validation set via API:', response.result);
    return {
      success: true,
      message: `Выпадающий список создан для "${rule.column_name}" (${rule.allowed_values.length} вариантов)`
    };
  } catch (error) {
    console.error('[SheetGPT] Error setting data validation:', error);
    throw new Error(`Ошибка создания валидации: ${error.message}`);
  }
}

async function convertColumnToNumbersInSheet(columnIndex, columnName, rowCount) {
  console.log('[SheetGPT] 🔢 Converting column to numbers:', columnIndex, columnName);

  try {
    const response = await safeSendMessage({
      action: 'CONVERT_TO_NUMBERS',
      data: {
        columnIndex: columnIndex,
        rowCount: rowCount || 1000
      }
    });

    if (!response || !response.success) {
      throw new Error(response?.error || 'Неизвестная ошибка');
    }

    console.log('[SheetGPT] ✅ Column converted to numbers:', response.result);
    return {
      success: true,
      message: `Колонка "${columnName}" преобразована в числа`
    };
  } catch (error) {
    console.error('[SheetGPT] Error converting to numbers:', error);
    throw new Error(`Ошибка преобразования: ${error.message}`);
  }
}

// Helper function to convert structured data to 2D array
function convertStructuredDataToValues(structuredData) {
  console.log('[SheetGPT] Converting structured data:', structuredData);

  if (!structuredData) {
    throw new Error('Invalid structured data format: data is null or undefined');
  }

  // If we have rows but no headers, extract headers from first row keys
  if (structuredData.rows && structuredData.rows.length > 0 && !structuredData.headers) {
    const firstRow = structuredData.rows[0];
    if (firstRow && typeof firstRow === 'object' && !Array.isArray(firstRow)) {
      structuredData.headers = Object.keys(firstRow);
      console.log('[SheetGPT] Auto-extracted headers:', structuredData.headers);
    }
  }

  // Backend returns format: { headers: [...], rows: [...], ... }
  if (structuredData.headers && structuredData.rows) {
    console.log('[SheetGPT] Using headers/rows format');
    const headers = structuredData.headers;

    // Check if rows are objects (from DataFrame.to_dict('records')) or arrays
    const firstRow = structuredData.rows[0];
    if (firstRow && typeof firstRow === 'object' && !Array.isArray(firstRow)) {
      // Rows are objects - convert to arrays using headers as keys
      console.log('[SheetGPT] 🔄 Converting object rows to arrays using headers:', headers);
      const convertedRows = structuredData.rows.map((row, idx) => {
        const convertedRow = headers.map(header => {
          const value = row[header];
          return value !== undefined && value !== null ? String(value) : '';
        });
        if (idx === 0) console.log('[SheetGPT] First converted row:', convertedRow);
        return convertedRow;
      });
      console.log('[SheetGPT] ✅ Converted', convertedRows.length, 'rows');
      return [headers, ...convertedRows];
    } else {
      // Rows are already arrays
      console.log('[SheetGPT] Rows are already arrays');
      return [headers, ...structuredData.rows];
    }
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

// Helper function to convert color name or hex to RGB
function convertColorNameToRGB(color) {
  // Handle hex colors like "#B3D9FF"
  if (color && color.startsWith('#')) {
    const hex = color.slice(1);
    const r = parseInt(hex.substring(0, 2), 16) / 255;
    const g = parseInt(hex.substring(2, 4), 16) / 255;
    const b = parseInt(hex.substring(4, 6), 16) / 255;
    return { red: r, green: g, blue: b };
  }

  // Handle color names
  const colorMap = {
    'yellow': { red: 1, green: 1, blue: 0.8 },
    'green': { red: 0.8, green: 1, blue: 0.8 },
    'red': { red: 1, green: 0.8, blue: 0.8 },
    'blue': { red: 0.8, green: 0.9, blue: 1 },
    'orange': { red: 1, green: 0.9, blue: 0.7 }
  };

  return colorMap[color?.toLowerCase()] || colorMap['yellow'];
}

// v10.1.1: Append column by key (VLOOKUP mode)
// Adds new column(s) to the RIGHT of existing data, matching rows by key column
async function appendColumnByKey({ keyColumn, writeHeaders, writeData }) {
  console.log('[SheetGPT] 🔗 appendColumnByKey:', { keyColumn, writeHeaders, writeData });

  try {
    // 1. Get current sheet data
    const sheetData = await safeSendMessage({
      action: 'GET_SHEET_DATA'
    });

    if (!sheetData || !sheetData.success || !sheetData.result) {
      throw new Error('Could not get current sheet data');
    }

    const currentHeaders = sheetData.result.headers || [];
    const currentData = sheetData.result.data || [];
    console.log('[SheetGPT] 📊 Current sheet:', currentHeaders.length, 'cols,', currentData.length, 'rows');

    // 2. Find the key column index in current sheet
    const keyColIndex = currentHeaders.findIndex(h =>
      h && h.toString().toLowerCase().trim() === keyColumn.toLowerCase().trim()
    );

    if (keyColIndex < 0) {
      throw new Error(`Key column "${keyColumn}" not found in current sheet. Available: ${currentHeaders.join(', ')}`);
    }
    console.log('[SheetGPT] 🔑 Key column index:', keyColIndex, 'name:', currentHeaders[keyColIndex]);

    // 3. Build a map of key values -> row index in current sheet
    const keyToRowIndex = new Map();
    currentData.forEach((row, rowIdx) => {
      const keyValue = row[keyColIndex];
      if (keyValue !== null && keyValue !== undefined && keyValue !== '') {
        // Normalize key for matching (trim, lowercase)
        const normalizedKey = String(keyValue).trim().toLowerCase();
        keyToRowIndex.set(normalizedKey, rowIdx);
      }
    });
    console.log('[SheetGPT] 🗺️ Built key map with', keyToRowIndex.size, 'entries');

    // 4. Determine new columns to add (skip the key column from writeHeaders)
    const keyIdxInWrite = writeHeaders.findIndex(h =>
      h && h.toString().toLowerCase().trim() === keyColumn.toLowerCase().trim()
    );
    if (keyIdxInWrite < 0) {
      throw new Error(`Key column "${keyColumn}" not found in write headers: ${writeHeaders.join(', ')}`);
    }

    // New columns are all columns except the key column
    const newColumnHeaders = writeHeaders.filter((_, idx) => idx !== keyIdxInWrite);
    const newColumnIndices = writeHeaders.map((_, idx) => idx).filter(idx => idx !== keyIdxInWrite);
    console.log('[SheetGPT] ➕ New columns to add:', newColumnHeaders);

    // 5. Find the next empty column letter (after current columns)
    const nextColIndex = currentHeaders.length;
    console.log('[SheetGPT] 📍 Will write to column index:', nextColIndex);

    // 6. Build values array for the new column(s)
    // First row = header(s)
    const valuesToWrite = [newColumnHeaders];

    // Create empty array for each row in current data
    for (let i = 0; i < currentData.length; i++) {
      valuesToWrite.push(new Array(newColumnHeaders.length).fill(''));
    }

    // 7. Fill in values by matching keys (with fuzzy matching for truncated keys)
    let matchCount = 0;
    let fuzzyMatchCount = 0;
    writeData.forEach(row => {
      const keyValue = row[keyIdxInWrite];
      if (keyValue !== null && keyValue !== undefined) {
        const normalizedKey = String(keyValue).trim().toLowerCase();
        let targetRowIdx = keyToRowIndex.get(normalizedKey);

        // If exact match not found, try fuzzy matching (GPT sometimes truncates long keys)
        if (targetRowIdx === undefined && normalizedKey.length >= 10) {
          // Try to find a key that starts with our truncated key or vice versa
          for (const [sheetKey, rowIdx] of keyToRowIndex.entries()) {
            if (sheetKey.startsWith(normalizedKey) || normalizedKey.startsWith(sheetKey)) {
              targetRowIdx = rowIdx;
              fuzzyMatchCount++;
              break;
            }
          }
        }

        if (targetRowIdx !== undefined) {
          // Found matching row - fill in values (skip key column)
          newColumnIndices.forEach((srcIdx, destIdx) => {
            valuesToWrite[targetRowIdx + 1][destIdx] = row[srcIdx]; // +1 for header row
          });
          matchCount++;
        }
      }
    });
    console.log('[SheetGPT] ✅ Matched', matchCount, 'rows out of', writeData.length, '(fuzzy:', fuzzyMatchCount, ')');

    // 8. Get spreadsheet ID and sheet name
    const match = window.location.href.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
    if (!match) {
      throw new Error('Could not get spreadsheet ID from URL');
    }
    const spreadsheetId = match[1];

    // v11.2: Get active sheet name from DOM (not cached) to ensure we write to correct sheet
    let sheetName = getCurrentSheetNameFromDOM();
    if (!sheetName) {
      // Fallback to cached name if DOM detection fails
      const storageKey = `sheetName_${spreadsheetId}`;
      const storage = await chrome.storage.local.get([storageKey]);
      sheetName = storage[storageKey];
    }
    if (!sheetName) {
      throw new Error('Could not get active sheet name');
    }
    console.log('[SheetGPT] 📋 Will write to sheet:', sheetName);

    // 9. Write new column(s) to the sheet
    const startColLetter = String.fromCharCode(65 + nextColIndex); // A=0, B=1, etc.
    console.log('[SheetGPT] 📝 Writing', valuesToWrite.length, 'rows to column', startColLetter);

    const response = await safeSendMessage({
      action: 'WRITE_SHEET_DATA',
      data: {
        sheetName: sheetName,
        values: valuesToWrite,
        startCell: `${startColLetter}1`,
        mode: 'overwrite'
      }
    });

    if (!response || !response.success) {
      throw new Error(response?.error || 'Failed to write column data');
    }

    console.log('[SheetGPT] ✅ Column appended successfully!', response.result);
    return {
      success: true,
      message: `Добавлена колонка "${newColumnHeaders.join(', ')}" (${matchCount} совпадений)`,
      matchedRows: matchCount,
      totalRows: writeData.length
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ appendColumnByKey error:', error);
    throw error;
  }
}

// v11.1: Fill column directly (without key matching)
// Writes values directly to a specific column by letter (e.g., "E")
async function fillColumnDirect({ targetColumn, columnName, startRow, values }) {
  console.log('[SheetGPT] 📝 fillColumnDirect:', { targetColumn, columnName, startRow, valuesCount: values?.length });
  console.log('[SheetGPT] 📝 First value type:', typeof values?.[0], Array.isArray(values?.[0]) ? 'is array' : 'not array');

  try {
    // 1. Get spreadsheet ID and sheet name
    const match = window.location.href.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
    if (!match) {
      throw new Error('Could not get spreadsheet ID from URL');
    }
    const spreadsheetId = match[1];

    // v11.2: Get active sheet name from DOM (not cached) to ensure we write to correct sheet
    let sheetName = getCurrentSheetNameFromDOM();
    if (!sheetName) {
      // Fallback to cached name if DOM detection fails
      const storageKey = `sheetName_${spreadsheetId}`;
      const storage = await chrome.storage.local.get([storageKey]);
      sheetName = storage[storageKey];
    }
    if (!sheetName) {
      throw new Error('Could not get active sheet name');
    }
    console.log('[SheetGPT] 📋 Will write to sheet:', sheetName);

    // v11.4: Get current headers to auto-correct column letter
    let headers = [];
    try {
      const sheetData = await getActiveSheetData();
      headers = sheetData?.headers || [];
      console.log('[SheetGPT] 📋 Current headers for column correction:', headers);
    } catch (e) {
      console.log('[SheetGPT] ⚠️ Could not get headers for correction:', e.message);
    }

    // 2. Convert column letter to uppercase and auto-correct if needed
    let colLetter = targetColumn.toUpperCase();
    if (columnName && headers.length > 0) {
      const headerIndex = headers.findIndex(h =>
        h && h.toString().toLowerCase().includes(columnName.toLowerCase()) ||
        columnName.toLowerCase().includes(h?.toString().toLowerCase() || '')
      );
      if (headerIndex >= 0) {
        const correctLetter = String.fromCharCode(65 + headerIndex);
        if (correctLetter !== colLetter) {
          console.log('[SheetGPT] 🔧 Column correction:', columnName, colLetter, '→', correctLetter);
          colLetter = correctLetter;
        }
      }
    }

    // 3. Determine the actual start row
    // If startRow is provided, use it; otherwise default based on columnName presence
    let actualStartRow = startRow || 2;

    // 4. Build values array
    // Each row should be an array with one element (for single column write)
    const valuesToWrite = [];

    // v11.5: ALWAYS write header if columnName is provided (fixes missing header bug)
    if (columnName) {
      console.log('[SheetGPT] 📝 Writing header:', columnName, 'to', colLetter + '1');
      await safeSendMessage({
        action: 'WRITE_SHEET_DATA',
        data: {
          sheetName: sheetName,
          values: [[columnName]],
          startCell: colLetter + '1',
          mode: 'overwrite'
        }
      });
    }

    // Add all values - handle both flat array and nested array formats
    values.forEach(val => {
      // If val is already an array, take the first element (GPT sometimes returns nested arrays)
      // If val is a primitive, wrap it in array
      if (Array.isArray(val)) {
        // For single column, take first element only
        valuesToWrite.push([val[0]]);
      } else {
        valuesToWrite.push([val]);
      }
    });

    // v11.5: Header is written separately, so data always starts at startRow (default 2)
    const writeStartRow = startRow || 2;

    console.log('[SheetGPT] 📝 Writing', valuesToWrite.length, 'rows to column', colLetter, 'starting at row', writeStartRow);
    console.log('[SheetGPT] 📝 Sample values:', valuesToWrite.slice(0, 3));

    const response = await safeSendMessage({
      action: 'WRITE_SHEET_DATA',
      data: {
        sheetName: sheetName,
        values: valuesToWrite,
        startCell: `${colLetter}${writeStartRow}`,
        mode: 'overwrite'
      }
    });

    if (!response || !response.success) {
      throw new Error(response?.error || 'Failed to write column data');
    }

    console.log('[SheetGPT] ✅ Column filled successfully!', response.result);
    return {
      success: true,
      message: `Колонка ${colLetter} заполнена (${values.length} значений)`,
      rowsWritten: values.length
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ fillColumnDirect error:', error);
    throw error;
  }
}

// v11.3: Fill multiple columns at once
async function fillColumnsDirect({ startRow, columns }) {
  console.log('[SheetGPT] 📝 fillColumnsDirect:', { startRow, columnsCount: columns?.length });

  try {
    // Get current active sheet name from DOM
    const sheetName = getCurrentSheetNameFromDOM();
    if (!sheetName) {
      throw new Error('Could not determine active sheet name');
    }
    console.log('[SheetGPT] 📋 Will write to sheet:', sheetName);

    // v11.4: Get current headers to auto-correct column letters
    let headers = [];
    let dataRowCount = 0;
    try {
      const sheetData = await getActiveSheetData();
      headers = sheetData?.headers || [];
      dataRowCount = sheetData?.data?.length || 0;
      console.log('[SheetGPT] 📋 Current headers for column correction:', headers);
      console.log('[SheetGPT] 📋 Data rows count:', dataRowCount);
    } catch (e) {
      console.log('[SheetGPT] ⚠️ Could not get headers for correction:', e.message);
    }

    const writeStartRow = startRow || 2;
    const results = [];

    // v11.6: Skip column correction if target is already AFTER existing data
    // e.g., GPT says target: "I" and we have 8 headers (A-H) → I is column 9, skip correction
    const firstTarget = columns[0]?.target?.toUpperCase() || '';
    const firstTargetIndex = firstTarget.charCodeAt(0) - 65; // A=0, B=1, I=8
    const targetIsAfterExistingData = firstTargetIndex >= headers.length;
    const hasRowGap = writeStartRow > dataRowCount + 1;
    const skipColumnCorrection = targetIsAfterExistingData || hasRowGap;
    const isSummary = skipColumnCorrection;
    if (isSummary) {
      console.log('[SheetGPT] 📊 Skip column correction:', {
        firstTarget,
        firstTargetIndex,
        headersCount: headers.length,
        targetIsAfterExistingData,
        hasRowGap
      });
    }

    // For summary, calculate first column after existing data
    const firstSummaryColumn = headers.length > 0 ? headers.length : 0;

    // Process each column
    let summaryColOffset = 0;
    for (const col of columns) {
      const { target, name, values } = col;
      if (!target || !values || values.length === 0) {
        console.log('[SheetGPT] ⚠️ Skipping column - missing target or values:', col);
        continue;
      }

      let colLetter;

      if (isSummary) {
        // v11.5: For summary, write to columns AFTER existing data (I, J, K...)
        colLetter = String.fromCharCode(65 + firstSummaryColumn + summaryColOffset);
        console.log('[SheetGPT] 📊 Summary column:', name, '→', colLetter, '(after existing data)');
        summaryColOffset++;
      } else {
        // v11.4: Auto-correct column letter based on header name (for regular fill)
        colLetter = target.toUpperCase();
        if (name && headers.length > 0) {
          const headerIndex = headers.findIndex(h =>
            h && h.toString().toLowerCase().includes(name.toLowerCase()) ||
            name.toLowerCase().includes(h?.toString().toLowerCase() || '')
          );
          if (headerIndex >= 0) {
            const correctLetter = String.fromCharCode(65 + headerIndex); // A=65
            if (correctLetter !== colLetter) {
              console.log('[SheetGPT] 🔧 Column correction:', name, colLetter, '→', correctLetter);
              colLetter = correctLetter;
            }
          }
        }
      }

      // Prepare values for this column
      const valuesToWrite = values.map(v => [v]);

      console.log('[SheetGPT] 📝 Writing', valuesToWrite.length, 'rows to column', colLetter, '(', name, ') starting at row', writeStartRow);

      const response = await safeSendMessage({
        action: 'WRITE_SHEET_DATA',
        data: {
          sheetName: sheetName,
          values: valuesToWrite,
          startCell: `${colLetter}${writeStartRow}`,
          mode: 'overwrite'
        }
      });

      if (!response || !response.success) {
        throw new Error(`Failed to write column ${colLetter}: ${response?.error || 'Unknown error'}`);
      }

      results.push({
        column: colLetter,
        name: name,
        rowsWritten: values.length
      });
    }

    console.log('[SheetGPT] ✅ All columns filled successfully!', results);
    return {
      success: true,
      message: `Заполнено ${results.length} колонок`,
      columns: results
    };
  } catch (error) {
    console.error('[SheetGPT] ❌ fillColumnsDirect error:', error);
    throw error;
  }
}
