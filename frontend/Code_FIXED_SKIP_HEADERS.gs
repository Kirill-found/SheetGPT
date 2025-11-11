/**
 * SheetGPT - FIXED VERSION - SKIPS HEADER ROW
 * VERSION: 3.1 - ПРАВИЛЬНО ПРОПУСКАЕТ ЗАГОЛОВКИ
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

  // КРИТИЧЕСКИ ВАЖНО: ПРОПУСКАЕМ ПЕРВУЮ СТРОКУ С ЗАГОЛОВКАМИ!
  // Проверяем, есть ли в первой строке текстовые заголовки
  const firstRow = values[0];
  const hasHeaders = firstRow.some(cell =>
    typeof cell === 'string' &&
    (cell.includes('Товар') || cell.includes('Поставщик') || cell.includes('Цена') || cell.includes('Объем'))
  );

  // Создаем автоматические названия колонок
  const numColumns = firstRow.length;
  const columnNames = [];
  for (let i = 0; i < numColumns; i++) {
    columnNames.push(`Колонка ${String.fromCharCode(65 + i)}`);
  }

  // ВАЖНО: Если есть заголовки - пропускаем первую строку!
  // ОТПРАВЛЯЕМ ВСЕ ДАННЫЕ (до 1000 строк)
  let dataToSend;
  if (hasHeaders) {
    console.log('HEADERS DETECTED - Skipping first row');
    dataToSend = values.slice(1, Math.min(1001, values.length)); // ВСЕ строки кроме заголовка (макс 1000)
  } else {
    console.log('NO HEADERS - Using all rows');
    dataToSend = values.slice(0, Math.min(1000, values.length)); // ВСЕ строки (макс 1000)
  }

  console.log('Columns:', columnNames);
  console.log('Data rows:', dataToSend.length);
  console.log('First data row:', dataToSend[0]);

  // DEBUG: Показать что в каждой колонке
  if (dataToSend.length > 0) {
    console.log('=== DEBUG: Column values ===');
    for (let i = 0; i < Math.min(5, numColumns); i++) {
      console.log(`Колонка ${String.fromCharCode(65 + i)}: ${dataToSend[0][i]}`);
    }
    console.log('=========================');
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

    console.log('SENDING:', JSON.stringify(payload).substring(0, 500));

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(API_URL + '/api/v1/formula', options);
    const result = JSON.parse(response.getContentText());

    console.log('RESPONSE:', JSON.stringify(result).substring(0, 500));

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
    console.error('ERROR:', error.toString());
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