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
    // СТРАТЕГИЯ 1: Найти grid container и работать внутри него
    const gridContainers = [
      '.grid4-inner-container',
      '.waffle-background-container',
      '.waffle',
      'table.waffle',
      '[role="grid"]',
      '.docs-sheet-container'
    ];

    for (const containerSelector of gridContainers) {
      const container = document.querySelector(containerSelector);
      if (!container) continue;

      console.log(`[SheetGPT] Found container: ${containerSelector}`);

      // Попробуем разные способы извлечь данные из контейнера
      const result = tryExtractFromContainer(container);
      if (result && validateSheetData(result)) {
        console.log(`[SheetGPT] ✅ Success with container "${containerSelector}"`);
        return result;
      }
    }

    // СТРАТЕГИЯ 2: "Умный" поиск - найти все divs/cells и сгруппировать по координатам
    console.log('[SheetGPT] Trying smart extraction by coordinates...');
    const smartResult = trySmartExtraction();
    if (smartResult && validateSheetData(smartResult)) {
      console.log('[SheetGPT] ✅ Success with smart extraction');
      return smartResult;
    }

    // СТРАТЕГИЯ 3: Старые селекторы как fallback
    console.log('[SheetGPT] Trying legacy selectors...');
    const legacyResult = tryLegacySelectors();
    if (legacyResult && validateSheetData(legacyResult)) {
      console.log('[SheetGPT] ✅ Success with legacy selectors');
      return legacyResult;
    }

    console.warn('[SheetGPT] ❌ All extraction strategies failed');
    return null;

  } catch (error) {
    console.error('[SheetGPT] Error reading from DOM:', error);
    return null;
  }
}

/**
 * Попытка извлечь данные из конкретного контейнера
 */
function tryExtractFromContainer(container) {
  // Ищем все элементы которые могут быть ячейками
  const cellSelectors = [
    '[data-col][data-row]',  // Cells with data attributes
    '[role="gridcell"]',
    '.cell',
    '[class*="s"]',  // Any class containing "s" (Google Sheets uses s0, s1, s2, ...)
    'td',
    'div[role="gridcell"]'
  ];

  for (const cellSelector of cellSelectors) {
    const cells = container.querySelectorAll(cellSelector);
    if (cells.length < 3) continue;  // Need reasonable number of cells (lowered from 5 to 3)

    console.log(`[SheetGPT] Found ${cells.length} cells with selector "${cellSelector}"`);

    // Группируем ячейки по строкам
    const rowsMap = new Map();

    for (const cell of cells) {
      // Пытаемся найти row index
      const rowAttr = cell.getAttribute('data-row') ||
                     cell.parentElement?.getAttribute('data-row') ||
                     cell.closest('[data-row]')?.getAttribute('data-row');

      const colAttr = cell.getAttribute('data-col') ||
                     cell.parentElement?.getAttribute('data-col') ||
                     cell.closest('[data-col]')?.getAttribute('data-col');

      // Если нет data-атрибутов, пробуем по позиции
      const rowIndex = rowAttr ? parseInt(rowAttr) : guessRowIndex(cell);
      const colIndex = colAttr ? parseInt(colAttr) : guessColIndex(cell);

      if (rowIndex !== null && colIndex !== null) {
        if (!rowsMap.has(rowIndex)) {
          rowsMap.set(rowIndex, new Map());
        }
        rowsMap.get(rowIndex).set(colIndex, cell.textContent.trim());
      }
    }

    // Конвертируем Map в массив массивов
    if (rowsMap.size >= 2) {
      const sortedRows = Array.from(rowsMap.keys()).sort((a, b) => a - b);
      const data = sortedRows.map(rowIdx => {
        const row = rowsMap.get(rowIdx);
        const sortedCols = Array.from(row.keys()).sort((a, b) => a - b);
        return sortedCols.map(colIdx => row.get(colIdx) || '');
      });

      if (data.length >= 2 && data[0].length >= 1) {
        console.log(`[SheetGPT] Extracted ${data.length} rows from container`);
        return { headers: data[0], data: data.slice(1) };
      }
    }
  }

  // FALLBACK: Если ничего не нашли, попробуем все divs внутри контейнера
  console.log('[SheetGPT] No cells found with known selectors, trying all divs...');
  const allDivs = container.querySelectorAll('div');
  console.log(`[SheetGPT] Found ${allDivs.length} divs in container`);

  if (allDivs.length >= 5) {  // Lowered from 10 to 5
    const cellCandidates = Array.from(allDivs).filter(div => {
      // Фильтруем: должен иметь текст, небольшой размер (похож на ячейку), видим
      const text = div.textContent?.trim();

      // Более мягкие критерии фильтрации
      const nestedDivs = div.querySelectorAll('div').length;

      return text &&
             text.length > 0 &&
             text.length < 300 &&  // Увеличено с 200 до 300
             div.offsetHeight > 3 &&  // Снижено с 5 до 3
             div.offsetHeight < 150 &&  // Увеличено с 100 до 150
             div.offsetWidth > 5 &&  // Снижено с 10 до 5
             div.offsetWidth < 800 &&   // Увеличено с 500 до 800
             div.offsetParent !== null &&
             // Исключаем большие контейнеры (много вложенных divs)
             // Allow up to 50 nested divs (Google Sheets cells are complex)
             nestedDivs < 50;  // Changed from < 10 to < 50
    });

    console.log(`[SheetGPT] Filtered to ${cellCandidates.length} cell candidates`);

    // DEBUG: Show first few candidates
    if (cellCandidates.length > 0) {
      console.log('[SheetGPT] First 5 candidates:',
        cellCandidates.slice(0, 5).map(c => ({
          text: c.textContent.trim().substring(0, 50),
          height: c.offsetHeight,
          width: c.offsetWidth,
          top: c.offsetTop,
          left: c.offsetLeft
        }))
      );
    }

    if (cellCandidates.length >= 5) {  // Lowered from 10 to 5
      // Группируем по координатам
      const rowsMap = new Map();

      for (const cell of cellCandidates) {
        const rowIdx = guessRowIndex(cell);
        const colIdx = guessColIndex(cell);

        console.log(`[SheetGPT] Cell "${cell.textContent.trim().substring(0, 20)}" → row=${rowIdx}, col=${colIdx}`);

        if (rowIdx !== null && colIdx !== null && rowIdx < 1000 && colIdx < 50) {
          if (!rowsMap.has(rowIdx)) {
            rowsMap.set(rowIdx, new Map());
          }
          rowsMap.get(rowIdx).set(colIdx, cell.textContent.trim());
        } else {
          console.warn(`[SheetGPT] Skipped cell: rowIdx=${rowIdx}, colIdx=${colIdx}`);
        }
      }

      console.log(`[SheetGPT] Grouped into ${rowsMap.size} rows`);

      if (rowsMap.size >= 2) {
        const sortedRows = Array.from(rowsMap.keys()).sort((a, b) => a - b);
        const data = sortedRows.map(rowIdx => {
          const row = rowsMap.get(rowIdx);
          const sortedCols = Array.from(row.keys()).sort((a, b) => a - b);
          return sortedCols.map(colIdx => row.get(colIdx) || '');
        });

        if (data.length >= 2 && data[0].length >= 1) {
          console.log(`[SheetGPT] Extracted ${data.length} rows using div fallback`);
          return { headers: data[0], data: data.slice(1) };
        }
      }
    }
  }

  return null;
}

/**
 * Угадать row index по позиции элемента
 */
function guessRowIndex(cell) {
  // Пробуем найти родительский элемент строки
  const rowParent = cell.closest('tr') ||
                   cell.closest('[role="row"]') ||
                   cell.closest('div[data-row]');

  if (rowParent) {
    const rowAttr = rowParent.getAttribute('data-row');
    if (rowAttr) return parseInt(rowAttr);

    // Считаем индекс среди siblings
    const siblings = Array.from(rowParent.parentElement?.children || []);
    return siblings.indexOf(rowParent);
  }

  // Пробуем по offsetTop
  const top = cell.offsetTop;
  return Math.floor(top / 21);  // Типичная высота строки ~21px
}

/**
 * Угадать col index по позиции элемента
 */
function guessColIndex(cell) {
  const colAttr = cell.getAttribute('data-col') ||
                 cell.closest('[data-col]')?.getAttribute('data-col');
  if (colAttr) return parseInt(colAttr);

  // Считаем индекс среди siblings
  const row = cell.closest('tr') || cell.closest('[role="row"]') || cell.parentElement;
  if (row) {
    const cells = Array.from(row.querySelectorAll('td, [role="gridcell"], .cell'));
    return cells.indexOf(cell);
  }

  // Пробуем по offsetLeft
  const left = cell.offsetLeft;
  return Math.floor(left / 100);  // Примерная ширина колонки
}

/**
 * "Умное" извлечение - найти все элементы похожие на ячейки
 */
function trySmartExtraction() {
  // Ищем все элементы с классом содержащим "cell" или "s[0-9]"
  const allElements = document.querySelectorAll('*');
  const potentialCells = [];

  for (const el of allElements) {
    const className = String(el.className || '');
    const hasDataAttrs = el.hasAttribute('data-row') || el.hasAttribute('data-col');

    // Проверяем: содержит "cell", или класс типа "s0", "s1", ..., или data-атрибуты
    const isCell = /cell/i.test(className) ||
                   /\bs\d+\b/.test(className) ||  // Match "s0", "s1", etc. as whole word
                   hasDataAttrs;

    // Фильтруем: должен иметь текст, разумный размер, и быть видимым
    if (isCell &&
        el.textContent &&
        el.offsetHeight > 5 &&
        el.offsetWidth > 10 &&
        el.offsetParent !== null) {  // Check if visible
      potentialCells.push(el);
    }
  }

  console.log(`[SheetGPT] Smart extraction found ${potentialCells.length} potential cells`);

  // DEBUG: Show first few cells
  if (potentialCells.length > 0) {
    console.log('[SheetGPT] First 5 potential cells:',
      potentialCells.slice(0, 5).map(c => ({
        text: c.textContent.trim().substring(0, 50),
        className: c.className,
        height: c.offsetHeight,
        width: c.offsetWidth,
        top: c.offsetTop,
        left: c.offsetLeft
      }))
    );
  }

  if (potentialCells.length < 2) return null;  // Lowered from 3 to 2

  // Группируем по координатам
  const rowsMap = new Map();

  for (const cell of potentialCells) {
    const rowIdx = guessRowIndex(cell);
    const colIdx = guessColIndex(cell);

    if (rowIdx !== null && colIdx !== null && rowIdx < 1000 && colIdx < 100) {
      if (!rowsMap.has(rowIdx)) {
        rowsMap.set(rowIdx, new Map());
      }
      const text = cell.textContent.trim();
      if (text) {
        rowsMap.get(rowIdx).set(colIdx, text);
      }
    }
  }

  if (rowsMap.size >= 2) {
    const sortedRows = Array.from(rowsMap.keys()).sort((a, b) => a - b).slice(0, 1000);
    const data = sortedRows.map(rowIdx => {
      const row = rowsMap.get(rowIdx);
      const maxCol = Math.max(...Array.from(row.keys()));
      const result = [];
      for (let i = 0; i <= maxCol; i++) {
        result.push(row.get(i) || '');
      }
      return result;
    });

    if (data.length >= 2 && data[0].length >= 1) {
      return { headers: data[0], data: data.slice(1) };
    }
  }

  return null;
}

/**
 * Старые селекторы как fallback
 */
function tryLegacySelectors() {
  const selectorStrategies = [
    { rows: '[role="row"]', cells: '[role="gridcell"], [role="columnheader"]' },
    { rows: 'table.waffle tbody tr', cells: 'td' },
    { rows: '.grid-row, .ritz .grid-row', cells: '.cell, [role="gridcell"]' },
    { rows: 'table tr', cells: 'td, th' },
    { rows: 'div[role="row"]', cells: 'div[role="gridcell"], div[role="columnheader"]' }
  ];

  for (const strategy of selectorStrategies) {
    const foundRows = document.querySelectorAll(strategy.rows);
    if (foundRows.length < 2) continue;

    const data = [];
    for (const row of Array.from(foundRows).slice(0, 1000)) {
      const cells = Array.from(row.querySelectorAll(strategy.cells));
      if (cells.length > 0) {
        const rowData = cells.map(cell => cell.textContent.trim());
        if (rowData.some(val => val)) {
          data.push(rowData);
        }
      }
    }

    if (data.length >= 2 && data[0].length >= 1) {
      console.log(`[SheetGPT] Legacy selector worked: "${strategy.rows}"`);
      return { headers: data[0], data: data.slice(1) };
    }
  }

  return null;
}

/**
 * Валидация извлеченных данных
 */
function validateSheetData(result) {
  if (!result || !result.headers || !result.data) {
    return false;
  }

  const { headers, data } = result;

  // Минимальные требования
  if (headers.length < 1 || data.length < 1) {
    console.warn('[SheetGPT] ⚠️ Not enough data:', { headers: headers.length, rows: data.length });
    return false;
  }

  // Пропускаем таблицы с подозрительно длинными заголовками (UI элементы)
  const hasInvalidHeaders = headers.some(h => h && h.length > 100);
  if (hasInvalidHeaders) {
    console.warn('[SheetGPT] ⚠️ Headers too long (> 100 chars)');
    return false;
  }

  // Проверяем консистентность колонок
  const allRows = [headers, ...data];
  const avgColumns = allRows.reduce((sum, row) => sum + row.length, 0) / allRows.length;
  const hasConsistentColumns = allRows.every(row => Math.abs(row.length - avgColumns) <= 3);

  if (!hasConsistentColumns) {
    console.warn('[SheetGPT] ⚠️ Inconsistent column counts');
    return false;
  }

  // Проверяем что есть хоть какие-то непустые данные
  const hasContent = data.some(row => row.some(cell => cell && cell.length > 0));
  if (!hasContent) {
    console.warn('[SheetGPT] ⚠️ No content in data rows');
    return false;
  }

  console.log(`[SheetGPT] ✅ Validation passed: ${data.length} rows, ${headers.length} columns`);
  console.log(`[SheetGPT] Headers:`, headers);
  console.log(`[SheetGPT] First row:`, data[0]);
  if (data[1]) console.log(`[SheetGPT] Second row:`, data[1]);

  return true;
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
