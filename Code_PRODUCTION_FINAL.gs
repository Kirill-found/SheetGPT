/**
 * SheetGPT PRODUCTION v3.1 - ОТПРАВЛЯЕТ ВСЕ ДАННЫЕ
 * ИСПРАВЛЕНО:
 * - Отправляет ВСЕ строки (до 1000), не только 10
 * - Правильно пропускает заголовки
 * - Корректно агрегирует дубликаты товаров/поставщиков
 */

const API_URL = 'https://sheetgpt-production.up.railway.app';

function onOpen(e) {
  SpreadsheetApp.getUi()
    .createMenu('SheetGPT')
    .addItem('Открыть AI помощник', 'showSidebar')
    .addSeparator()
    .addItem('Справка', 'showHelp')
    .addToUi();
}

function onInstall(e) {
  onOpen(e);
}

function showSidebar() {
  const html = HtmlService.createHtmlOutputFromFile('Sidebar')
    .setTitle('SheetGPT AI')
    .setWidth(350);
  SpreadsheetApp.getUi().showSidebar(html);
}

function showHelp() {
  const ui = SpreadsheetApp.getUi();
  ui.alert(
    'Как пользоваться SheetGPT',
    'Примеры запросов:\n\n' +
    '• "У какого поставщика больше всего продаж"\n' +
    '• "Топ 3 товара по продажам"\n' +
    '• "Какой товар самый прибыльный"\n\n' +
    'SheetGPT автоматически проанализирует данные.',
    ui.ButtonSet.OK
  );
}

function getSheetData() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const range = sheet.getDataRange();
  const values = range.getValues();

  if (!values || values.length === 0) {
    return {
      data: [],
      columnNames: [],
      error: 'Нет данных в таблице'
    };
  }

  // Проверяем, есть ли в первой строке текстовые заголовки
  const firstRow = values[0];
  const hasHeaders = firstRow.some(cell =>
    typeof cell === 'string' &&
    (cell.includes('Товар') || cell.includes('Поставщик') ||
     cell.includes('Цена') || cell.includes('Объем') ||
     cell.includes('Продаж') || cell.includes('Сумма'))
  );

  // Создаем автоматические названия колонок
  const numColumns = firstRow.length;
  const columnNames = [];
  for (let i = 0; i < numColumns; i++) {
    columnNames.push(`Колонка ${String.fromCharCode(65 + i)}`);
  }

  // КРИТИЧЕСКИ ВАЖНО: ОТПРАВЛЯЕМ ВСЕ ДАННЫЕ!
  let dataToSend;
  let startRow = hasHeaders ? 1 : 0; // Если есть заголовки, начинаем с 1 строки

  // Берем ВСЕ строки данных (максимум 1000 для оптимизации)
  dataToSend = values.slice(startRow, Math.min(startRow + 1000, values.length));

  console.log('=== ОТПРАВКА ДАННЫХ ===');
  console.log('Обнаружены заголовки:', hasHeaders);
  console.log('Колонки:', columnNames);
  console.log('Всего строк в таблице:', values.length);
  console.log('Отправляем строк данных:', dataToSend.length);
  console.log('Первая строка данных:', dataToSend[0]);
  console.log('Последняя строка данных:', dataToSend[dataToSend.length - 1]);
  console.log('=====================');

  // Показать примеры данных из разных колонок
  if (dataToSend.length > 0) {
    console.log('=== ПРИМЕРЫ ДАННЫХ ===');
    for (let i = 0; i < Math.min(5, numColumns); i++) {
      const samples = [];
      for (let j = 0; j < Math.min(3, dataToSend.length); j++) {
        if (dataToSend[j][i] !== null && dataToSend[j][i] !== undefined) {
          samples.push(dataToSend[j][i]);
        }
      }
      console.log(`Колонка ${String.fromCharCode(65 + i)}: ${samples.join(', ')}`);
    }
    console.log('====================');
  }

  return {
    data: dataToSend,
    columnNames: columnNames,
    selectedRange: null,
    activeCell: null
  };
}

function processQuery(query) {
  try {
    const sheetData = getSheetData();

    if (sheetData.error) {
      throw new Error(sheetData.error);
    }

    if (!query || query === 'undefined' || typeof query === 'undefined') {
      throw new Error('Запрос пустой. Пожалуйста, введите вопрос.');
    }

    const payload = {
      query: query,
      column_names: sheetData.columnNames,
      sheet_data: sheetData.data,
      history: getConversationHistory()
    };

    console.log('ОТПРАВКА НА API:', {
      query: query,
      columns: payload.column_names,
      rows: payload.sheet_data.length,
      sample: payload.sheet_data.slice(0, 3)
    });

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(API_URL + '/api/v1/formula', options);
    const result = JSON.parse(response.getContentText());

    console.log('ОТВЕТ API:', {
      status: response.getResponseCode(),
      type: result.response_type,
      summary: result.summary ? result.summary.substring(0, 100) : 'нет'
    });

    if (response.getResponseCode() === 200) {
      // Сохраняем в историю
      const history = getConversationHistory();
      const historyItem = {
        query: query,
        actions: result.insights || []
      };
      history.push(historyItem);
      saveConversationHistory(history);

      return {
        formula: result.formula || null,
        explanation: result.explanation || '',
        target_cell: result.target_cell || null,
        confidence: result.confidence || 0,
        response_type: result.response_type || 'formula',
        insights: result.insights || [],
        suggested_actions: result.suggested_actions || null,
        summary: result.summary || null,
        methodology: result.methodology || null,
        key_findings: result.key_findings || []
      };
    } else {
      throw new Error(result.detail || 'Ошибка обработки запроса');
    }
  } catch (error) {
    console.error('ОШИБКА:', error.toString());
    throw new Error('Ошибка связи с сервером: ' + error.toString());
  }
}

function getConversationHistory() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const historyJson = scriptProperties.getProperty('conversation_history');

  if (historyJson) {
    try {
      return JSON.parse(historyJson);
    } catch (e) {
      console.log('Failed to parse history:', e);
      return [];
    }
  }

  return [];
}

function saveConversationHistory(history) {
  try {
    const scriptProperties = PropertiesService.getScriptProperties();
    // Keep only last 10 items
    const trimmedHistory = history.slice(-10);
    scriptProperties.setProperty('conversation_history', JSON.stringify(trimmedHistory));
  } catch (e) {
    console.log('Failed to save history:', e);
  }
}

function applyFormula(formula, targetCell) {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();
    const range = sheet.getRange(targetCell);
    range.setFormula(formula);

    SpreadsheetApp.flush();

    return { success: true };
  } catch (error) {
    console.error('Error applying formula:', error);
    return {
      success: false,
      error: error.toString()
    };
  }
}

// Функция для быстрых кнопок (нужна для Sidebar.html)
function setQueryAndProcess(query) {
  try {
    return processQuery(query);
  } catch (error) {
    console.error('Error in setQueryAndProcess:', error);
    throw error;
  }
}

// Тестовая функция для проверки отправки данных
function testDataCheck() {
  const ui = SpreadsheetApp.getUi();
  const data = getSheetData();

  let message = 'ПРОВЕРКА ОТПРАВКИ ДАННЫХ\n\n';
  message += `Всего строк для отправки: ${data.data.length}\n`;
  message += `Колонки: ${data.columnNames.join(', ')}\n\n`;

  // Подсчитаем дубликаты
  const items = {};
  for (const row of data.data) {
    const item = row[0]; // Первая колонка - товар
    if (item) {
      items[item] = (items[item] || 0) + 1;
    }
  }

  message += 'Товары с дубликатами:\n';
  for (const [item, count] of Object.entries(items)) {
    if (count > 1) {
      message += `${item}: ${count} строк\n`;
    }
  }

  ui.alert('Проверка данных', message, ui.ButtonSet.OK);
}