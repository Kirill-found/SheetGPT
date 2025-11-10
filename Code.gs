/**
 * SheetGPT - AI Assistant for Google Sheets
 * Main Apps Script file
 */

// Backend API URL
// Updated to new environment with v1.2.0 (methodology + intent fixes)
const API_URL = 'https://sheetgpt-sheet.up.railway.app';

/**
 * Запускается при открытии таблицы
 * Для Add-on меню создается автоматически из appsscript.json
 */
function onOpen(e) {
  try {
    // Создаем меню только если это не Add-on контекст
    if (e && e.authMode !== ScriptApp.AuthMode.NONE) {
      SpreadsheetApp.getUi()
        .createMenu('SheetGPT')
        .addItem('Открыть AI помощник', 'showSidebar')
        .addSeparator()
        .addItem('Новый разговор', 'startNewConversation')
        .addSeparator()
        .addItem('Справка', 'showHelp')
        .addToUi();
    }
  } catch (error) {
    // Игнорируем ошибки - меню создастся автоматически для Add-on
    console.log('onOpen: меню создается автоматически для Add-on');
  }
}

/**
 * Устанавливается при установке аддона
 */
function onInstall(e) {
  onOpen(e);
}

/**
 * Показывает sidebar с AI помощником
 * Для Add-on возвращает HtmlOutput напрямую
 */
function showSidebar(e) {
  try {
    Logger.log('=== showSidebar START ===');
    Logger.log('Parameter e: ' + e);

    const html = HtmlService.createHtmlOutputFromFile('Sidebar')
      .setTitle('SheetGPT AI')
      .setWidth(350);

    Logger.log('HTML created, title: ' + html.getTitle());
    Logger.log('HTML width: ' + html.getWidth());

    // Если вызвано как Add-on (есть параметр e или нет доступа к UI)
    if (e) {
      Logger.log('Returning HTML for Add-on context');
      return html;
    }

    Logger.log('Calling showSidebar...');
    SpreadsheetApp.getUi().showSidebar(html);
    Logger.log('✅ showSidebar completed successfully');
  } catch (error) {
    Logger.log('❌ ERROR in showSidebar:');
    Logger.log('Error name: ' + error.name);
    Logger.log('Error message: ' + error.message);
    Logger.log('Error stack: ' + error.stack);

    // Показываем ошибку пользователю
    SpreadsheetApp.getActiveSpreadsheet().toast(
      'Ошибка при открытии Sidebar: ' + error.message,
      'Ошибка',
      5
    );

    throw error; // Пробрасываем ошибку чтобы увидеть её в UI
  }
}

/**
 * Показывает приветственное сообщение
 */
function showWelcome() {
  try {
    const ui = SpreadsheetApp.getUi();
    ui.alert(
      'Добро пожаловать в SheetGPT!',
      'SheetGPT - ваш AI помощник для работы с таблицами.\n\n' +
      'Откройте меню SheetGPT → Открыть AI помощник',
      ui.ButtonSet.OK
    );
  } catch (error) {
    // Игнорируем для Add-on
    console.log('Welcome message skipped for Add-on');
  }
}

/**
 * Показывает справку
 */
function showHelp() {
  try {
    const ui = SpreadsheetApp.getUi();
    ui.alert(
      'Как пользоваться SheetGPT',
      'Примеры запросов:\n\n' +
      '• "Сумма продаж где сумма больше 500000"\n' +
      '• "Средний чек по каждому менеджеру"\n' +
      '• "Почему упали продажи в октябре?"\n' +
      '• "Создай отчет по продажам за неделю"\n\n' +
      'SheetGPT автоматически создаст формулу или даст ответ.',
      ui.ButtonSet.OK
    );
  } catch (error) {
    // Игнорируем для Add-on
    console.log('Help dialog not available in Add-on context');
  }
}

/**
 * ДИАГНОСТИКА: Тестирует соединение с API сервером
 * Запустите эту функцию чтобы проверить настройки
 */
function testAPIConnection() {
  try {
    Logger.log('🔍 Тестирование соединения с API...');
    Logger.log('API URL: ' + API_URL);

    // Проверка 1: Health check
    const healthUrl = API_URL + '/health';
    Logger.log('Запрос к: ' + healthUrl);

    const response = UrlFetchApp.fetch(healthUrl, {
      method: 'get',
      muteHttpExceptions: true
    });

    const statusCode = response.getResponseCode();
    const content = response.getContentText();

    Logger.log('Status: ' + statusCode);
    Logger.log('Response: ' + content);

    if (statusCode === 200) {
      const healthData = JSON.parse(content);
      Logger.log('✅ УСПЕХ! Сервер отвечает');
      Logger.log('Версия: ' + healthData.version);
      Logger.log('Статус: ' + healthData.status);

      // Проверка 2: Тест формулы
      Logger.log('\n🧪 Тестирование API формул...');
      const testPayload = {
        query: 'Сумма продаж',
        column_names: ['Товар', 'Продажи'],
        sheet_data: [['Товар','Продажи'],['Тест',1000]]
      };

      const formulaUrl = API_URL + '/api/v1/formula';
      const formulaResponse = UrlFetchApp.fetch(formulaUrl, {
        method: 'post',
        contentType: 'application/json',
        payload: JSON.stringify(testPayload),
        muteHttpExceptions: true
      });

      const formulaStatus = formulaResponse.getResponseCode();
      const formulaContent = formulaResponse.getContentText();

      Logger.log('Formula API Status: ' + formulaStatus);
      Logger.log('Formula API Response: ' + formulaContent);

      if (formulaStatus === 200) {
        Logger.log('✅ API формул работает!');
        SpreadsheetApp.getActiveSpreadsheet().toast(
          '✅ Соединение работает!\nВерсия: ' + healthData.version,
          'Тест API',
          5
        );
        return true;
      } else {
        Logger.log('❌ API формул вернул ошибку: ' + formulaStatus);
        SpreadsheetApp.getActiveSpreadsheet().toast(
          '⚠️ Health check OK, но API формул не работает\nПроверьте логи (Ctrl+Enter)',
          'Тест API',
          5
        );
        return false;
      }
    } else {
      Logger.log('❌ Сервер вернул статус: ' + statusCode);
      SpreadsheetApp.getActiveSpreadsheet().toast(
        '❌ Сервер вернул ошибку: ' + statusCode,
        'Тест API',
        5
      );
      return false;
    }
  } catch (error) {
    Logger.log('❌ ОШИБКА: ' + error.toString());
    Logger.log('Error name: ' + error.name);
    Logger.log('Error message: ' + error.message);

    if (error.message && error.message.indexOf('белом списке') !== -1) {
      Logger.log('\n⚠️ URL НЕ В WHITELIST!');
      Logger.log('Решение:');
      Logger.log('1. Откройте Project Settings (⚙️ слева)');
      Logger.log('2. Включите "Show appsscript.json in editor"');
      Logger.log('3. Обновите appsscript.json с правильным urlFetchWhitelist');

      SpreadsheetApp.getActiveSpreadsheet().toast(
        '❌ URL не в whitelist!\n' +
        'Откройте Project Settings → Show appsscript.json\n' +
        'Проверьте логи для деталей (Ctrl+Enter)',
        'Ошибка',
        10
      );
    } else {
      SpreadsheetApp.getActiveSpreadsheet().toast(
        '❌ Ошибка: ' + error.message + '\nПроверьте логи (Ctrl+Enter)',
        'Тест API',
        5
      );
    }

    return false;
  }
}

/**
 * Читает данные из активного листа
 */
function getSheetData() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const range = sheet.getDataRange();
  const values = range.getValues();

  // Ограничиваем до 1000 строк для производительности
  const maxRows = 1000;
  let data = values.slice(0, maxRows);

  // Получаем информацию о выделенном диапазоне
  const activeRange = sheet.getActiveRange();
  const activeCell = sheet.getActiveCell();

  let selectedRange = null;
  let activeCellA1 = null;

  if (activeRange) {
    selectedRange = activeRange.getA1Notation();
  }

  if (activeCell) {
    activeCellA1 = activeCell.getA1Notation();
  }

  // === УМНОЕ ОПРЕДЕЛЕНИЕ СТРОКИ ЗАГОЛОВКОВ ===
  let headerRowIndex = 0;

  // Ищем первую строку, где больше 50% ячеек содержат непустой текст
  for (let i = 0; i < Math.min(5, data.length); i++) {
    const row = data[i];
    let nonEmptyCount = 0;
    let textCount = 0;

    for (let cell of row) {
      if (cell !== null && cell !== undefined && cell !== '' && cell !== 0) {
        nonEmptyCount++;

        // Проверяем, что это текст (не число, не дата)
        if (typeof cell === 'string' && cell.trim() !== '' && isNaN(cell)) {
          textCount++;
        }
      }
    }

    // Если больше 30% ячеек - непустой текст, и больше 50% заполнено, это заголовки
    if (textCount >= row.length * 0.3 && nonEmptyCount >= row.length * 0.5) {
      headerRowIndex = i;
      Logger.log('✅ Найдена строка заголовков: ' + (i + 1));
      break;
    }
  }

  // Если нашли заголовки не в первой строке, пропускаем мусор сверху
  if (headerRowIndex > 0) {
    Logger.log('⚠️ Пропускаем ' + headerRowIndex + ' строк мусора сверху');
    data = data.slice(headerRowIndex);
  }

  // Преобразуем все значения в строки для совместимости с Pydantic
  const stringData = data.map(row => row.map(cell => {
    if (cell === null || cell === undefined) return '';
    if (cell instanceof Date) return cell.toISOString();
    return String(cell);
  }));

  const columnNames = stringData.length > 0 ? stringData[0] : [];

  Logger.log('📋 Column names: ' + columnNames.slice(0, 5).join(', '));
  Logger.log('📊 Data rows: ' + stringData.length);

  return {
    data: stringData,
    columnNames: columnNames,
    rowCount: values.length,
    sheetName: sheet.getName(),
    selectedRange: selectedRange,
    activeCell: activeCellA1,
    headerRowIndex: headerRowIndex + 1  // +1 для отображения пользователю (нумерация с 1)
  };
}

/**
 * Вставляет формулу в ячейку
 */
function insertFormula(formula, cell) {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();

    // Если cell не указана, берем первую свободную ячейку справа от данных
    if (!cell) {
      const lastColumn = sheet.getLastColumn();
      cell = columnToLetter(lastColumn + 1) + '1';
    }

    // ВАЖНО: Определяем - это формула или текст
    // Если начинается с "=" - это формула, иначе - текст
    const range = sheet.getRange(cell);
    if (formula && formula.toString().startsWith('=')) {
      // Конвертируем русские названия функций обратно в английские
      // Google Sheets API требует английские названия в setFormula()
      const englishFormula = convertToEnglishFunctions(formula);
      range.setFormula(englishFormula);
    } else {
      range.setValue(formula);
    }

    // Выделяем ячейку чтобы пользователь её видел
    sheet.setActiveRange(range);

    return {
      success: true,
      cell: cell,
      message: 'Значение вставлено в ячейку ' + cell
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Конвертирует русские названия функций в английские для Google Sheets API
 */
function convertToEnglishFunctions(formula) {
  // Словарь русских → английских названий функций
  const functionMap = {
    'ЕСЛИ': 'IF',
    'ЕПУСТО': 'ISBLANK',
    'ЕЧИСЛО': 'ISNUMBER',
    'ПОИСКПОЗ': 'MATCH',
    'СЧЁТЕСЛИ': 'COUNTIF',
    'СУММЕСЛИ': 'SUMIF',
    'СУММЕСЛИМН': 'SUMIFS',
    'СЧЁТЕСЛИМН': 'COUNTIFS',
    'СРЗНАЧЕСЛИ': 'AVERAGEIF',
    'СРЗНАЧЕСЛИМН': 'AVERAGEIFS',
    'ВПР': 'VLOOKUP',
    'ГПР': 'HLOOKUP',
    'ИНДЕКС': 'INDEX',
    'СУММ': 'SUM',
    'СРЗНАЧ': 'AVERAGE',
    'МАКС': 'MAX',
    'МИН': 'MIN',
    'СЧЁТ': 'COUNT',
    'СЧЁТЗ': 'COUNTA',
    'И': 'AND',
    'ИЛИ': 'OR',
    'НЕ': 'NOT',
    'ИСТИНА': 'TRUE',
    'ЛОЖЬ': 'FALSE',
    'ТЕКСТ': 'TEXT',
    'ЗНАЧЕН': 'VALUE',
    'ДЛСТР': 'LEN',
    'ЛЕВСИМВ': 'LEFT',
    'ПРАВСИМВ': 'RIGHT',
    'ПСТР': 'MID',
    'СЦЕПИТЬ': 'CONCATENATE',
    'ОБЪЕДИНИТЬ': 'TEXTJOIN',
    'СЕГОДНЯ': 'TODAY',
    'ТДАТА': 'NOW',
    'ГОД': 'YEAR',
    'МЕСЯЦ': 'MONTH',
    'ДЕНЬ': 'DAY',
    'ДАТА': 'DATE',
    'ЕОШИБКА': 'ISERROR',
    'ЕСЛИОШИБКА': 'IFERROR',
    'ОКРУГЛ': 'ROUND',
    'ОКРУГЛВВЕРХ': 'ROUNDUP',
    'ОКРУГЛВНИЗ': 'ROUNDDOWN',
    'ARRAYFORMULA': 'ARRAYFORMULA'
  };

  let result = formula;

  // Заменяем каждую русскую функцию на английскую
  // ВАЖНО: \b (word boundary) не работает с кириллицей!
  // Поэтому заменяем "ФУНКЦИЯ(" на "FUNCTION(" напрямую
  for (const [rus, eng] of Object.entries(functionMap)) {
    const pattern = new RegExp(rus + '\\(', 'g');
    result = result.replace(pattern, eng + '(');
  }

  // ВАЖНО: Точки с запятой НЕ заменяем!
  // В русской локализации Google Sheets API также использует точки с запятой

  return result;
}

/**
 * Конвертирует номер колонки в букву (1 → A, 27 → AA)
 */
function columnToLetter(column) {
  let temp, letter = '';
  while (column > 0) {
    temp = (column - 1) % 26;
    letter = String.fromCharCode(temp + 65) + letter;
    column = (column - temp - 1) / 26;
  }
  return letter;
}

/**
 * Вызывает backend API для генерации формулы
 */
function generateFormula(query) {
  try {
    const sheetData = getSheetData();

    // Получаем conversation_id для поддержки контекстных запросов
    const conversationId = getConversationId();

    const payload = {
      query: query,
      column_names: sheetData.columnNames,
      sheet_data: sheetData.data.slice(0, 10), // Отправляем только первые 10 строк
      selected_range: sheetData.selectedRange,
      active_cell: sheetData.activeCell,
      conversation_id: conversationId  // Отправляем conversation_id если есть
    };

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
      }
    };

    // Добавляем timestamp к URL для борьбы с кэшированием
    const url = API_URL + '/api/v1/formula?t=' + new Date().getTime();
    const response = UrlFetchApp.fetch(url, options);
    const result = JSON.parse(response.getContentText());

    if (response.getResponseCode() === 200) {
      // Сохраняем conversation_id из ответа для следующих запросов
      if (result.conversation_id) {
        saveConversationId(result.conversation_id);
      }

      return {
        success: true,
        formula: result.formula,
        explanation: result.explanation,
        confidence: result.confidence,
        targetCell: result.target_cell
      };
    } else {
      return {
        success: false,
        error: result.detail || 'Ошибка генерации формулы'
      };
    }
  } catch (error) {
    return {
      success: false,
      error: 'Ошибка связи с сервером: ' + error.toString()
    };
  }
}

/**
 * Получает историю запросов из UserProperties
 */
function getConversationHistory() {
  try {
    const userProps = PropertiesService.getUserProperties();
    const historyJson = userProps.getProperty('sheetgpt_history');
    if (historyJson) {
      return JSON.parse(historyJson);
    }
  } catch (error) {
    console.log('Не удалось загрузить историю: ' + error);
  }
  return [];
}

/**
 * Сохраняет историю запросов в UserProperties
 */
function saveConversationHistory(history) {
  try {
    const userProps = PropertiesService.getUserProperties();
    // Ограничиваем до последних 5 действий
    const limitedHistory = history.slice(-5);
    userProps.setProperty('sheetgpt_history', JSON.stringify(limitedHistory));
  } catch (error) {
    console.log('Не удалось сохранить историю: ' + error);
  }
}

/**
 * Очищает историю запросов
 */
function clearConversationHistory() {
  try {
    const userProps = PropertiesService.getUserProperties();
    userProps.deleteProperty('sheetgpt_history');
    return true;
  } catch (error) {
    console.log('Не удалось очистить историю: ' + error);
    return false;
  }
}

/**
 * Получает conversation_id из UserProperties
 * conversation_id используется для поддержки контекстных запросов ("попробуй еще раз", "измени", etc.)
 */
function getConversationId() {
  try {
    const userProps = PropertiesService.getUserProperties();
    return userProps.getProperty('sheetgpt_conversation_id');
  } catch (error) {
    console.log('Не удалось получить conversation_id: ' + error);
    return null;
  }
}

/**
 * Сохраняет conversation_id в UserProperties
 */
function saveConversationId(conversationId) {
  try {
    if (conversationId) {
      const userProps = PropertiesService.getUserProperties();
      userProps.setProperty('sheetgpt_conversation_id', conversationId);
    }
  } catch (error) {
    console.log('Не удалось сохранить conversation_id: ' + error);
  }
}

/**
 * Очищает conversation_id (начинает новый разговор)
 */
function clearConversationId() {
  try {
    const userProps = PropertiesService.getUserProperties();
    userProps.deleteProperty('sheetgpt_conversation_id');
    return true;
  } catch (error) {
    console.log('Не удалось очистить conversation_id: ' + error);
    return false;
  }
}

/**
 * Начинает новый разговор (очищает conversation_id)
 * Вызывается пользователем через меню
 */
function startNewConversation() {
  const cleared = clearConversationId();
  if (cleared) {
    SpreadsheetApp.getActiveSpreadsheet().toast(
      'Начат новый разговор. Теперь система не будет помнить предыдущие запросы.',
      'Новый разговор',
      5
    );
  } else {
    SpreadsheetApp.getActiveSpreadsheet().toast(
      'Не удалось начать новый разговор',
      'Ошибка',
      3
    );
  }
}

/**
 * ДИАГНОСТИЧЕСКАЯ ФУНКЦИЯ - Простой эхо-тест для проверки передачи параметров
 * Используется для диагностики проблем с google.script.run
 */
function simpleEcho(text) {
  Logger.log('=== simpleEcho START ===');
  Logger.log('Received text: ' + text);
  Logger.log('Type: ' + typeof text);
  Logger.log('Is undefined: ' + (text === undefined));
  Logger.log('Is null: ' + (text === null));

  if (text === undefined) {
    return {
      success: false,
      error: 'ПАРАМЕТР UNDEFINED',
      message: 'google.script.run НЕ ПЕРЕДАЛ параметр! Это означает проблему с iframe или настройками Apps Script.'
    };
  }

  if (text === null) {
    return {
      success: false,
      error: 'ПАРАМЕТР NULL',
      message: 'Параметр null (не undefined, но пустой)'
    };
  }

  if (typeof text !== 'string') {
    return {
      success: false,
      error: 'НЕВЕРНЫЙ ТИП',
      message: 'Параметр имеет тип: ' + typeof text + ', ожидалась строка'
    };
  }

  return {
    success: true,
    message: '✅ ПАРАМЕТР ПОЛУЧЕН УСПЕШНО!',
    received: text,
    type: typeof text,
    length: text.length
  };
}

/**
 * Обработка запроса (упрощенная версия - без UserProperties)
 * Параметры передаются напрямую
 */
function setQueryAndProcess(queryText) {
  try {
    Logger.log('=== setQueryAndProcess START ===');
    Logger.log('Received queryText: ' + queryText);
    Logger.log('Type: ' + typeof queryText);
    Logger.log('Length: ' + (queryText ? queryText.length : 'N/A'));

    // ВАЖНО: Если queryText undefined, значит google.script.run не передал параметр
    if (queryText === undefined || queryText === null || queryText === 'undefined') {
      Logger.log('❌ queryText is undefined/null - параметр НЕ ПЕРЕДАН!');
      throw new Error('КРИТИЧЕСКАЯ ОШИБКА: Параметр не передан из Sidebar. Проблема с google.script.run в iframe контексте.');
    }

    // Проверяем что query не пустой
    const query = String(queryText).trim();
    if (!query || query === '') {
      Logger.log('❌ Empty query after trim!');
      throw new Error('Запрос пустой. Пожалуйста, введите текст запроса.');
    }

    Logger.log('✅ Query validated, length: ' + query.length);

    // Напрямую вызываем processQueryWithParam без промежуточного хранилища
    return processQueryWithParam(query);
  } catch (error) {
    Logger.log('❌ setQueryAndProcess ERROR: ' + error.message);
    Logger.log('Error stack: ' + error.stack);
    throw error;
  }
}

/**
 * Обрабатывает запрос пользователя (для чата)
 * Возвращает результат напрямую без вставки формулы
 */
function processQuery(query) {
  // Для обратной совместимости
  if (query && typeof query === 'string' && query.trim() !== '') {
    return processQueryWithParam(query);
  }
  // Если query пустой, пробуем получить из временного хранилища
  return processQueryInternal();
}

/**
 * Внутренняя функция обработки запроса
 */
function processQueryInternal() {
  try {
    Logger.log('=== processQueryInternal START ===');

    // Получаем query из временного хранилища
    const userProps = PropertiesService.getUserProperties();
    const query = userProps.getProperty('temp_query');

    Logger.log('Query from storage: ' + query);
    Logger.log('Query type: ' + typeof query);

    // Проверяем что query не пустой
    if (!query || query === 'undefined' || String(query).trim() === '') {
      Logger.log('❌ Empty query received!');
      throw new Error('Запрос пустой. Пожалуйста, введите текст запроса.');
    }

    return processQueryWithParam(query);
  } catch (error) {
    Logger.log('❌ processQueryInternal ERROR: ' + error.message);
    throw error;
  }
}

/**
 * Обработка запроса с параметром
 */
function processQueryWithParam(query) {
  try {
    Logger.log('=== processQueryWithParam START ===');
    Logger.log('Query: ' + query);

    const sheetData = getSheetData();
    Logger.log('Columns: ' + sheetData.columnNames.length);

    // Получаем историю предыдущих запросов
    const history = getConversationHistory();
    Logger.log('History items: ' + history.length);

    // Получаем conversation_id для поддержки контекстных запросов
    const conversationId = getConversationId();
    Logger.log('ConvID: ' + conversationId);

    const payload = {
      query: query,
      column_names: sheetData.columnNames,
      sheet_data: sheetData.data.slice(0, 10),
      history: history,  // Добавляем историю в запрос
      conversation_id: conversationId  // Отправляем conversation_id если есть
    };

    Logger.log('=== PAYLOAD DEBUG ===');
    Logger.log('query type: ' + typeof payload.query);
    Logger.log('query value: ' + payload.query);
    Logger.log('column_names type: ' + typeof payload.column_names);
    Logger.log('column_names length: ' + (payload.column_names ? payload.column_names.length : 'null'));
    Logger.log('column_names[0]: ' + (payload.column_names && payload.column_names.length > 0 ? payload.column_names[0] : 'N/A'));
    Logger.log('sheet_data type: ' + typeof payload.sheet_data);
    Logger.log('sheet_data length: ' + (payload.sheet_data ? payload.sheet_data.length : 'null'));
    Logger.log('history type: ' + typeof payload.history);
    Logger.log('history length: ' + (payload.history ? payload.history.length : 'null'));
    Logger.log('conversation_id type: ' + typeof payload.conversation_id);
    Logger.log('conversation_id value: ' + payload.conversation_id);

    Logger.log('Creating JSON...');
    const payloadStr = JSON.stringify(payload);
    Logger.log('JSON size: ' + payloadStr.length);
    Logger.log('JSON first 500 chars: ' + payloadStr.substring(0, 500));

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: payloadStr,
      muteHttpExceptions: true,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
      }
    };

    // Добавляем timestamp к URL для борьбы с кэшированием
    const url = API_URL + '/api/v1/formula?t=' + new Date().getTime();
    Logger.log('URL: ' + url);
    Logger.log('Sending request...');

    const response = UrlFetchApp.fetch(url, options);
    const statusCode = response.getResponseCode();
    Logger.log('Status: ' + statusCode);

    const responseText = response.getContentText();
    Logger.log('Response size: ' + responseText.length);

    const result = JSON.parse(responseText);

    if (statusCode === 200) {
      Logger.log('✅ Success!');

      // Сохраняем conversation_id из ответа для следующих запросов
      if (result.conversation_id) {
        saveConversationId(result.conversation_id);
      }

      // Сохраняем это действие в историю
      const historyItem = {
        query: query,
        actions: result.insights || []
      };
      history.push(historyItem);
      saveConversationHistory(history);

      // ВАЖНО: Явно возвращаем все поля, чтобы Google Apps Script не отфильтровал их
      const finalResult = {
        formula: result.formula || null,
        explanation: result.explanation || '',
        target_cell: result.target_cell || null,
        confidence: result.confidence || 0,
        response_type: result.response_type || 'formula',
        insights: result.insights || [],
        suggested_actions: result.suggested_actions || null,
        // Analysis fields
        summary: result.summary || null,
        methodology: result.methodology || null,
        key_findings: result.key_findings || []
      };

      Logger.log('=== processQuery END (success) ===');
      return finalResult;
    } else {
      Logger.log('❌ Non-200 status');
      Logger.log('Result detail type: ' + typeof result.detail);
      Logger.log('Result detail: ' + JSON.stringify(result.detail));

      // Правильно обрабатываем ошибку от FastAPI
      let errorMessage = 'Ошибка обработки запроса';
      if (result.detail) {
        if (typeof result.detail === 'string') {
          errorMessage = result.detail;
        } else if (Array.isArray(result.detail)) {
          // FastAPI validation errors возвращают массив
          errorMessage = result.detail.map(e => e.msg || e.message || JSON.stringify(e)).join('; ');
        } else if (typeof result.detail === 'object') {
          errorMessage = JSON.stringify(result.detail);
        }
      }

      Logger.log('Error message: ' + errorMessage);
      throw new Error(errorMessage);
    }
  } catch (error) {
    Logger.log('❌ EXCEPTION: ' + error.name);
    Logger.log('Message: ' + error.message);
    Logger.log('Stack: ' + error.stack);

    // Если ошибка уже обработана выше, просто пробрасываем её
    if (error.message && !error.message.includes('UrlFetchApp')) {
      throw error;
    }

    // Иначе оборачиваем в понятное сообщение
    throw new Error('Ошибка связи с сервером: ' + error.message);
  }
}

/**
 * ТЕСТ: Проверка processQuery с параметром
 */
function testProcessQuery() {
  return processQuery('Сумма продаж');
}

/**
 * ДИАГНОСТИКА: Проверка загрузки Sidebar
 * Запустите эту функцию чтобы проверить, может ли Apps Script найти файл Sidebar
 */
function testSidebarLoad() {
  try {
    Logger.log('🔍 Проверка загрузки Sidebar...');

    // Попытка загрузить HTML файл
    const html = HtmlService.createHtmlOutputFromFile('Sidebar');

    Logger.log('✅ Sidebar загружен успешно!');
    Logger.log('Title: ' + html.getTitle());
    Logger.log('Width: ' + html.getWidth());

    // Попытка получить содержимое
    const content = html.getContent();
    Logger.log('Content length: ' + content.length + ' символов');
    Logger.log('Первые 100 символов: ' + content.substring(0, 100));

    SpreadsheetApp.getActiveSpreadsheet().toast(
      '✅ Sidebar файл найден и загружен!',
      'Тест Sidebar',
      3
    );

    return true;
  } catch (error) {
    Logger.log('❌ ОШИБКА при загрузке Sidebar:');
    Logger.log('Error name: ' + error.name);
    Logger.log('Error message: ' + error.message);
    Logger.log('Error stack: ' + error.stack);

    SpreadsheetApp.getActiveSpreadsheet().toast(
      '❌ Не удалось загрузить Sidebar!\nПроверьте логи (Ctrl+Enter)',
      'Ошибка',
      5
    );

    return false;
  }
}

/**
 * Получает текущий статус пользователя
 */
function getUserStatus() {
  // TODO: Добавить реальную проверку подписки через backend
  const userEmail = Session.getActiveUser().getEmail();

  return {
    email: userEmail,
    tier: 'free',
    queriesUsed: 5,
    queriesLimit: 20
  };
}

// ============================================
// РАСШИРЕННЫЕ ФУНКЦИИ ДЛЯ СЛОЖНЫХ ЗАДАЧ
// ============================================

/**
 * Создает график/диаграмму
 */
function createChart(config) {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();

    // Парсим диапазон данных
    const dataRange = sheet.getRange(config.dataRange);

    // Определяем тип графика
    let chartBuilder = sheet.newChart()
      .setPosition(config.row || 5, config.column || 8, 0, 0);

    // Выбираем тип графика
    switch (config.type) {
      case 'column':
        chartBuilder.setChartType(Charts.ChartType.COLUMN);
        break;
      case 'bar':
        chartBuilder.setChartType(Charts.ChartType.BAR);
        break;
      case 'line':
        chartBuilder.setChartType(Charts.ChartType.LINE);
        break;
      case 'pie':
        chartBuilder.setChartType(Charts.ChartType.PIE);
        break;
      case 'area':
        chartBuilder.setChartType(Charts.ChartType.AREA);
        break;
      default:
        chartBuilder.setChartType(Charts.ChartType.COLUMN);
    }

    // Добавляем данные и параметры
    chartBuilder
      .addRange(dataRange)
      .setOption('title', config.title || 'График')
      .setOption('width', config.width || 600)
      .setOption('height', config.height || 400)
      .setOption('legend', { position: 'bottom' });

    // Создаем график
    const chart = chartBuilder.build();
    sheet.insertChart(chart);

    return {
      success: true,
      message: 'График создан успешно'
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Форматирует ячейки (цвет, шрифт, границы)
 */
function formatCells(config) {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();
    const range = sheet.getRange(config.range);

    // Цвет фона
    if (config.backgroundColor) {
      range.setBackground(config.backgroundColor);
    }

    // Цвет текста
    if (config.textColor) {
      range.setFontColor(config.textColor);
    }

    // Жирный шрифт
    if (config.bold) {
      range.setFontWeight('bold');
    }

    // Размер шрифта
    if (config.fontSize) {
      range.setFontSize(config.fontSize);
    }

    // Выравнивание
    if (config.horizontalAlignment) {
      range.setHorizontalAlignment(config.horizontalAlignment);
    }

    // Границы
    if (config.borders) {
      range.setBorder(true, true, true, true, true, true);
    }

    return {
      success: true,
      message: 'Форматирование применено'
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Применяет условное форматирование
 */
function applyConditionalFormat(config) {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();
    const range = sheet.getRange(config.range);

    // Удаляем существующие правила условного форматирования для этого диапазона
    const rules = sheet.getConditionalFormatRules();
    const newRules = rules.filter(rule => {
      const ruleRange = rule.getRanges()[0];
      return !ruleRange || ruleRange.getA1Notation() !== config.range;
    });

    // Создаем новое правило
    let rule;

    if (config.type === 'date_expired') {
      // Правило для истекших дат
      // ВАЖНО: Используем $column для абсолютной ссылки на колонку
      // Например: =$I2<TODAY() - фиксирует колонку I, но строка меняется
      const formula = '=$' + config.column + '2<TODAY()';
      rule = SpreadsheetApp.newConditionalFormatRule()
        .whenFormulaSatisfied(formula)
        .setBackground(config.backgroundColor || '#f4cccc')
        .setRanges([range])
        .build();
    } else if (config.type === 'custom_formula') {
      // Кастомная формула
      rule = SpreadsheetApp.newConditionalFormatRule()
        .whenFormulaSatisfied(config.formula)
        .setBackground(config.backgroundColor || '#fff2cc')
        .setRanges([range])
        .build();
    } else {
      throw new Error('Неизвестный тип условного форматирования: ' + config.type);
    }

    newRules.push(rule);
    sheet.setConditionalFormatRules(newRules);

    return {
      success: true,
      message: 'Условное форматирование применено к диапазону ' + config.range
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Вставляет данные в таблицу
 */
function insertData(config) {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();
    const startRow = config.startRow || sheet.getLastRow() + 1;
    const startColumn = config.startColumn || 1;

    // Вставляем данные
    const range = sheet.getRange(
      startRow,
      startColumn,
      config.data.length,
      config.data[0].length
    );
    range.setValues(config.data);

    return {
      success: true,
      message: `Данные вставлены в диапазон ${range.getA1Notation()}`
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Создает новый лист
 */
function createNewSheet(name) {
  try {
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const newSheet = spreadsheet.insertSheet(name);

    return {
      success: true,
      sheetName: newSheet.getName(),
      message: `Лист "${name}" создан`
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Применяет фильтр к диапазону
 */
function applyFilter(config) {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();
    const range = sheet.getRange(config.range);

    // Создаем фильтр
    const filter = range.createFilter();

    // Применяем условия фильтрации
    if (config.columnIndex && config.criteria) {
      const filterCriteria = SpreadsheetApp.newFilterCriteria()
        .whenTextContains(config.criteria)
        .build();
      filter.setColumnFilterCriteria(config.columnIndex, filterCriteria);
    }

    return {
      success: true,
      message: 'Фильтр применен'
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Сортирует данные
 */
function sortData(config) {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();
    const range = sheet.getRange(config.range);

    // Сортируем по указанной колонке
    range.sort({
      column: config.column,
      ascending: config.ascending !== false
    });

    return {
      success: true,
      message: 'Данные отсортированы'
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Выполняет список действий от AI
 */
function executeActions(actions) {
  const results = [];

  for (const action of actions) {
    let result;

    switch (action.type) {
      case 'create_chart':
        result = createChart(action.config);
        break;

      case 'format_cells':
        result = formatCells(action.config);
        break;

      case 'apply_conditional_format':
        result = applyConditionalFormat(action.config);
        break;

      case 'insert_data':
        result = insertData(action.config);
        break;

      case 'insert_formula':
        result = insertFormula(action.config.formula, action.config.cell);
        break;

      case 'create_sheet':
        result = createNewSheet(action.config.name);
        break;

      case 'apply_filter':
        result = applyFilter(action.config);
        break;

      case 'sort_data':
        result = sortData(action.config);
        break;

      default:
        result = {
          success: false,
          error: 'Неизвестный тип действия: ' + action.type
        };
    }

    results.push({
      action: action.type,
      ...result
    });
  }

  return {
    success: results.every(r => r.success),
    results: results,
    message: `Выполнено ${results.filter(r => r.success).length}/${results.length} действий`
  };
}

/**
 * Отменяет выполненное действие
 */
function undoAction(action, result) {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();

    switch (action.type) {
      case 'create_chart':
        // Удаляем последний созданный график
        const charts = sheet.getCharts();
        if (charts.length > 0) {
          const lastChart = charts[charts.length - 1];
          sheet.removeChart(lastChart);
          return {
            success: true,
            message: 'График удален'
          };
        } else {
          return {
            success: false,
            error: 'График не найден'
          };
        }

      case 'format_cells':
        // Очищаем форматирование в указанном диапазоне
        if (action.config && action.config.range) {
          const range = sheet.getRange(action.config.range);

          // Сбрасываем только визуальное форматирование (не данные)
          if (action.config.backgroundColor) {
            range.setBackground(null);
          }
          if (action.config.textColor) {
            range.setFontColor(null);
          }
          if (action.config.bold) {
            range.setFontWeight('normal');
          }
          if (action.config.fontSize) {
            range.setFontSize(10); // Default size
          }

          return {
            success: true,
            message: 'Форматирование очищено'
          };
        } else {
          return {
            success: false,
            error: 'Диапазон не указан'
          };
        }

      default:
        return {
          success: false,
          error: 'Отмена не поддерживается для действия: ' + action.type
        };
    }
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}
