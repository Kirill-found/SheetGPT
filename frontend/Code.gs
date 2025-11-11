/**
 * SheetGPT - AI Assistant for Google Sheets
 * Main Apps Script file
 */

// Backend API URL
const API_URL = 'https://sheetgpt-production.up.railway.app';

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
  const html = HtmlService.createHtmlOutputFromFile('Sidebar')
    .setTitle('SheetGPT AI')
    .setWidth(350);

  // Если вызвано как Add-on (есть параметр e или нет доступа к UI)
  try {
    if (e) {
      return html;
    }
    SpreadsheetApp.getUi().showSidebar(html);
  } catch (error) {
    // Fallback для Add-on контекста
    return html;
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
 * Читает данные из активного листа
 */
function getSheetData() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const range = sheet.getDataRange();
  const values = range.getValues();

  // Ограничиваем до 1000 строк для производительности
  const maxRows = 1000;
  const data = values.slice(0, maxRows);

  return {
    data: data,
    columnNames: data.length > 0 ? data[0] : [],
    rowCount: values.length,
    sheetName: sheet.getName()
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
      range.setFormula(formula);
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

    const payload = {
      query: query,
      column_names: sheetData.columnNames,
      sheet_data: sheetData.data.slice(0, 10) // Отправляем только первые 10 строк
    };

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(API_URL + '/api/v1/formula', options);
    const result = JSON.parse(response.getContentText());

    if (response.getResponseCode() === 200) {
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
 * Обрабатывает запрос пользователя (для чата)
 * Возвращает результат напрямую без вставки формулы
 */
function processQuery(query) {
  try {
    const sheetData = getSheetData();

    // Получаем историю предыдущих запросов
    const history = getConversationHistory();

    // КРИТИЧЕСКАЯ ПРОВЕРКА: query не должен быть undefined/null
    if (!query || query === 'undefined' || typeof query === 'undefined') {
      throw new Error('Запрос пустой. Пожалуйста, введите вопрос.');
    }

    // КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: НОВАЯ ЛОГИКА ОБРАБОТКИ
    console.log('=== DATA DETECTION START ===');
    console.log('First row:', sheetData.columnNames);
    console.log('Total rows:', sheetData.data.length);

    let columnNames, dataToSend;

    // УНИВЕРСАЛЬНАЯ ПРОВЕРКА: смотрим ПЕРВУЮ СТРОКУ ДАННЫХ
    // Если она содержит строки вида "ООО", "ИП" - это ДАННЫЕ, НЕ заголовки!
    const firstDataRow = sheetData.data.length > 0 ? sheetData.data[0] : [];
    const hasCompanyNames = firstDataRow.some(cell =>
      typeof cell === 'string' && (cell.includes('ООО') || cell.includes('ИП'))
    );

    if (hasCompanyNames) {
      // ПЕРВАЯ СТРОКА - ЭТО ДАННЫЕ! Нет заголовков!
      console.log('⚠️ DETECTED: First row contains data (companies), NO headers!');
      const numColumns = firstDataRow.length;
      columnNames = [];
      for (let i = 0; i < numColumns; i++) {
        columnNames.push(`Колонка ${String.fromCharCode(65 + i)}`);  // A, B, C, D, E
      }
      dataToSend = sheetData.data.slice(0, 10);  // Берём ВСЕ строки включая первую
    } else {
      // Возможно есть заголовки
      const firstCell = sheetData.columnNames[0];
      const looksLikeHeaders = typeof firstCell === 'string' &&
                                !(/^\d+$/.test(firstCell)) &&  // Не число
                                firstCell.length > 0 &&
                                firstCell !== '' &&
                                !firstCell.includes('Товар ');  // Не "Товар 1", а просто "Товар"

      if (looksLikeHeaders) {
        console.log('✅ DETECTED: Headers found in first row');
        columnNames = sheetData.columnNames;
        dataToSend = sheetData.data.slice(1, 11);  // Пропускаем заголовки
      } else {
        console.log('⚠️ DETECTED: No clear headers, using automatic columns');
        const numColumns = firstDataRow.length || 5;
        columnNames = [];
        for (let i = 0; i < numColumns; i++) {
          columnNames.push(`Колонка ${String.fromCharCode(65 + i)}`);
        }
        dataToSend = sheetData.data.slice(0, 10);  // Берём все строки
      }
    }

    console.log('Final columnNames:', columnNames);
    console.log('Rows to send:', dataToSend.length);
    console.log('First data row:', dataToSend[0]);

    const payload = {
      query: query,
      column_names: columnNames,
      sheet_data: dataToSend,
      history: history  // Добавляем историю в запрос
    };

    // КРИТИЧЕСКАЯ ОТЛАДКА - ПОКАЗЫВАЕМ ЧТО ОТПРАВЛЯЕМ!
    console.log('=== SENDING TO API ===');
    console.log('Payload:', JSON.stringify(payload, null, 2));
    console.log('Column names:', columnNames);
    console.log('Data rows count:', dataToSend.length);
    console.log('First data row:', dataToSend[0]);
    console.log('==================');

    // ПОКАЗЫВАЕМ АЛЕРТ С ОТЛАДКОЙ!
    const debugInfo = `ОТЛАДКА SHEETGPT:

Заголовки: ${columnNames.join(', ')}
Строк данных: ${dataToSend.length}
Первая строка: ${dataToSend[0] ? dataToSend[0].join(' | ') : 'НЕТ'}

Если видите "Колонка A, B, C..." - нет заголовков
Если видите "Товар, Поставщик..." - есть заголовки`;

    // Раскомментируй для отладки:
    // SpreadsheetApp.getUi().alert('DEBUG', debugInfo, SpreadsheetApp.getUi().ButtonSet.OK);

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(API_URL + '/api/v1/formula', options);
    const result = JSON.parse(response.getContentText());

    if (response.getResponseCode() === 200) {
      // Сохраняем это действие в историю
      const historyItem = {
        query: query,
        actions: result.insights || []
      };
      history.push(historyItem);
      saveConversationHistory(history);

      // ВАЖНО: Явно возвращаем все поля, чтобы Google Apps Script не отфильтровал их
      return {
        formula: result.formula || null,
        explanation: result.explanation || '',
        target_cell: result.target_cell || null,
        confidence: result.confidence || 0,
        response_type: result.response_type || 'formula',
        insights: result.insights || [],
        suggested_actions: result.suggested_actions || null,
        // КРИТИЧЕСКИ ВАЖНО: Поля для анализа
        summary: result.summary || null,
        methodology: result.methodology || null,
        key_findings: result.key_findings || []
      };
    } else {
      throw new Error(result.detail || 'Ошибка обработки запроса');
    }
  } catch (error) {
    throw new Error('Ошибка связи с сервером: ' + error.toString());
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
 * Обрабатывает batch запрос для диапазона ячеек
 * Применяет один запрос к нескольким строкам
 */
function processBatchQuery(query, range) {
  try {
    console.log('=== BATCH QUERY START ===');
    console.log('Query:', query);
    console.log('Range:', range);

    const sheet = SpreadsheetApp.getActiveSheet();
    const rangeData = sheet.getRange(range);
    const values = rangeData.getValues();

    console.log('Rows to process:', values.length);

    // Get context from full sheet
    const sheetData = getSheetData();
    const columnNames = sheetData.columnNames;

    const results = [];
    const totalRows = values.length;

    // Process each row
    for (let i = 0; i < values.length; i++) {
      const row = values[i];
      const rowNumber = rangeData.getRow() + i;

      console.log(`Processing row ${i + 1}/${totalRows}:`, row);

      try {
        // Create payload with single row context
        const payload = {
          query: query,
          column_names: columnNames,
          sheet_data: [row],  // Send only this row
          context_data: sheetData.data.slice(0, 10),  // Full context for reference
          history: []
        };

        const options = {
          method: 'post',
          contentType: 'application/json',
          payload: JSON.stringify(payload),
          muteHttpExceptions: true
        };

        const response = UrlFetchApp.fetch(API_URL + '/api/v1/formula', options);
        const result = JSON.parse(response.getContentText());

        if (response.getResponseCode() === 200) {
          results.push({
            row: rowNumber,
            success: true,
            summary: result.summary || result.explanation || 'OK',
            data: result
          });
        } else {
          results.push({
            row: rowNumber,
            success: false,
            error: result.detail || 'Unknown error'
          });
        }

      } catch (error) {
        results.push({
          row: rowNumber,
          success: false,
          error: error.toString()
        });
      }

      // Progress update (можно добавить callback)
      console.log(`Progress: ${i + 1}/${totalRows} (${Math.round((i + 1) / totalRows * 100)}%)`);
    }

    console.log('=== BATCH QUERY COMPLETE ===');
    console.log('Success:', results.filter(r => r.success).length);
    console.log('Failed:', results.filter(r => !r.success).length);

    return {
      success: true,
      total: totalRows,
      processed: results.length,
      succeeded: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length,
      results: results
    };

  } catch (error) {
    throw new Error('Batch processing error: ' + error.toString());
  }
}

/**
 * Wrapper function для вызова из sidebar
 * Google Apps Script требует чтобы функции вызываемые через google.script.run
 * были определены на верхнем уровне
 */
function setQueryAndProcess(query) {
  console.log("=== setQueryAndProcess called ===");
  console.log("Query received:", query);
  console.log("Query type:", typeof query);

  if (!query) {
    throw new Error('Запрос пустой. Пожалуйста, введите вопрос.');
  }

  return processQuery(query);
}
