/**
 * SheetGPT Chrome Extension - Popup Script
 */

// Проверяем на какой странице мы находимся
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const currentTab = tabs[0];
  const isOnSheets = currentTab?.url?.includes('docs.google.com/spreadsheets');

  const openSheetsBtn = document.getElementById('open-sheets-btn');
  const openSidebarBtn = document.getElementById('open-sidebar-btn');

  if (isOnSheets) {
    // Мы на странице Sheets - показываем кнопку открытия sidebar
    openSheetsBtn?.classList.add('hidden');
    openSidebarBtn?.classList.remove('hidden');
  } else {
    // Не на Sheets - показываем кнопку перехода
    openSheetsBtn?.classList.remove('hidden');
    openSidebarBtn?.classList.add('hidden');
  }
});

// Открыть sidebar
document.getElementById('open-sidebar-btn')?.addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // Отправляем сообщение content script чтобы открыть sidebar
  chrome.tabs.sendMessage(tab.id, { action: 'OPEN_SIDEBAR' });

  // Закрываем popup
  window.close();
});

// Проверка подключения
document.getElementById('test-btn')?.addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = 'Проверка подключения...';
  statusDiv.className = 'status';

  try {
    const response = await fetch('https://sheetgpt-production.up.railway.app/api/v1/health');

    if (response.ok) {
      const data = await response.json();
      statusDiv.textContent = `✓ Подключение успешно! Версия: ${data.version || '7.3.1'}`;
      statusDiv.className = 'status success';
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    statusDiv.textContent = `✗ Ошибка подключения: ${error.message}`;
    statusDiv.className = 'status error';
  }
});
