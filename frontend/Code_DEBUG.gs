/**
 * SheetGPT DEBUG VERSION - показывает что отправляется на сервер
 */

const API_URL = 'https://sheetgpt-production.up.railway.app';

function onOpen(e) {
  SpreadsheetApp.getUi()
    .createMenu('SheetGPT DEBUG')
    .addItem('Открыть DEBUG панель', 'showSidebar')
    .addItem('ТЕСТ: Проверить данные', 'testDataSending')
    .addToUi();
}

function showSidebar() {
  const html = HtmlService.createHtmlOutputFromFile('Sidebar')
    .setTitle('SheetGPT DEBUG')
    .setWidth(350);
  SpreadsheetApp.getUi().showSidebar(html);
}

// ТЕСТОВАЯ ФУНКЦИЯ - показывает что отправляется
function testDataSending() {
  const ui = SpreadsheetApp.getUi();
  const sheet = SpreadsheetApp.getActiveSheet();

  // Читаем данные
  const range = sheet.getDataRange();
  const values = range.getValues();

  // Первые 10 строк
  const dataToSend = values.slice(0, 10);

  // Создаем автоматические заголовки
  const numColumns = dataToSend[0] ? dataToSend[0].length : 5;
  const columnNames = [];
  for (let i = 0; i < numColumns; i++) {
    columnNames.push(`Колонка ${String.fromCharCode(65 + i)}`);
  }

  // Показываем что отправляем
  let message = `ОТПРАВЛЯЕМЫЕ ДАННЫЕ:\n\n`;
  message += `Колонки: ${columnNames.join(', ')}\n\n`;
  message += `Первая строка данных:\n${JSON.stringify(dataToSend[0])}\n\n`;
  message += `Всего строк: ${dataToSend.length}`;

  ui.alert('DEBUG INFO', message, ui.ButtonSet.OK);

  // Теперь отправляем запрос
  const payload = {
    query: "у какого поставщика больше всего продаж",
    column_names: columnNames,
    sheet_data: dataToSend,
    history: []
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    const response = UrlFetchApp.fetch(API_URL + '/api/v1/formula', options);
    const result = JSON.parse(response.getContentText());

    ui.alert('ОТВЕТ СЕРВЕРА',
      `Summary: ${result.summary || 'НЕТ'}\n\n` +
      `Methodology: ${result.methodology || 'НЕТ'}`,
      ui.ButtonSet.OK);

  } catch (error) {
    ui.alert('ОШИБКА', error.toString(), ui.ButtonSet.OK);
  }
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

  // ВСЕГДА используем автоматические заголовки
  const numColumns = values[0] ? values[0].length : 5;
  const columnNames = [];
  for (let i = 0; i < numColumns; i++) {
    columnNames.push(`Колонка ${String.fromCharCode(65 + i)}`);
  }

  // Берем ВСЕ первые 10 строк
  const dataToSend = values.slice(0, 10);

  console.log('DEBUG: Columns:', columnNames);
  console.log('DEBUG: Rows to send:', dataToSend.length);
  console.log('DEBUG: First row:', dataToSend[0]);

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

    const payload = {
      query: query,
      column_names: sheetData.columnNames,
      sheet_data: sheetData.data,
      history: []
    };

    // DEBUG: Показываем что отправляем
    console.log('SENDING TO API:', JSON.stringify(payload).substring(0, 500));

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(API_URL + '/api/v1/formula', options);
    const result = JSON.parse(response.getContentText());

    console.log('API RESPONSE:', JSON.stringify(result).substring(0, 500));

    if (response.getResponseCode() === 200) {
      return result;
    } else {
      throw new Error(result.detail || 'Ошибка обработки запроса');
    }
  } catch (error) {
    console.error('ERROR:', error);
    throw error;
  }
}

function getConversationHistory() {
  return [];
}

function saveConversationHistory(history) {
  // Not implemented for debug
}

function applyFormula(formula, targetCell) {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();
    const range = sheet.getRange(targetCell);
    range.setFormula(formula);
    return { success: true };
  } catch (error) {
    return { success: false, error: error.toString() };
  }
}