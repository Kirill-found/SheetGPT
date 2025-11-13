/**
 * SheetGPT Code.gs - SIMPLIFIED VERSION v6.4.0
 * Упрощенная версия с максимальной надежностью создания графиков
 */

/**
 * ГЛАВНАЯ ФУНКЦИЯ - создает таблицу и график
 */
function createTableAndChart(structuredData) {
  console.log('=== SheetGPT v6.4.0 SIMPLIFIED ===');
  console.log('Input data:', JSON.stringify(structuredData));

  try {
    // 1. Проверяем входные данные
    if (!structuredData || !structuredData.headers || !structuredData.rows) {
      console.error('ERROR: Invalid input data');
      return {
        success: false,
        error: 'Invalid input data',
        message: '❌ Неверные входные данные'
      };
    }

    // 2. Создаем новый лист
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const title = structuredData.table_title || 'Анализ данных';

    // Генерируем уникальное имя листа
    let sheetName = title.substring(0, 50); // Ограничиваем длину
    let counter = 1;
    while (ss.getSheetByName(sheetName)) {
      sheetName = title.substring(0, 45) + ' (' + counter + ')';
      counter++;
    }

    console.log('Creating sheet:', sheetName);
    const sheet = ss.insertSheet(sheetName);

    // 3. Вставляем данные
    const headers = structuredData.headers;
    const rows = structuredData.rows;
    const allData = [headers].concat(rows);

    console.log('Inserting data:', allData.length + ' rows x ' + headers.length + ' columns');

    const numRows = allData.length;
    const numCols = headers.length;
    const dataRange = sheet.getRange(1, 1, numRows, numCols);
    dataRange.setValues(allData);

    // 4. Форматируем заголовки
    const headerRange = sheet.getRange(1, 1, 1, numCols);
    headerRange
      .setFontWeight('bold')
      .setBackground('#4285F4')
      .setFontColor('#FFFFFF')
      .setHorizontalAlignment('center');

    // 5. Добавляем границы
    dataRange.setBorder(true, true, true, true, true, true, '#000000', SpreadsheetApp.BorderStyle.SOLID);

    // 6. Автоподбор ширины колонок
    for (let col = 1; col <= numCols; col++) {
      sheet.autoResizeColumn(col);
    }

    // 7. Закрепляем заголовок
    sheet.setFrozenRows(1);

    // 8. Активируем лист
    sheet.activate();

    console.log('Table created successfully');

    // 9. СОЗДАЁМ ГРАФИК (если рекомендован)
    let chartCreated = false;
    let chartMessage = '';

    if (structuredData.chart_recommended) {
      console.log('Creating chart, type:', structuredData.chart_recommended);

      try {
        // САМЫЙ ПРОСТОЙ СПОСОБ СОЗДАНИЯ ГРАФИКА
        const chartType = structuredData.chart_recommended;
        let chartEnum = Charts.ChartType.COLUMN; // По умолчанию

        // Определяем тип графика
        switch(chartType) {
          case 'pie':
            chartEnum = Charts.ChartType.PIE;
            break;
          case 'bar':
            chartEnum = Charts.ChartType.BAR;
            break;
          case 'line':
            chartEnum = Charts.ChartType.LINE;
            break;
          case 'area':
            chartEnum = Charts.ChartType.AREA;
            break;
          default:
            chartEnum = Charts.ChartType.COLUMN;
        }

        console.log('Chart enum:', chartEnum);

        // СОЗДАЁМ ГРАФИК С МИНИМАЛЬНЫМИ НАСТРОЙКАМИ
        const chart = sheet.newChart()
          .setChartType(chartEnum)
          .addRange(dataRange)
          .setPosition(2, numCols + 2, 0, 0) // Справа от таблицы
          .setOption('title', title)
          .build();

        console.log('Chart built, inserting...');
        sheet.insertChart(chart);

        // Проверяем что график создан
        const charts = sheet.getCharts();
        console.log('Charts on sheet:', charts.length);

        if (charts.length > 0) {
          chartCreated = true;
          chartMessage = ' График создан!';
        } else {
          chartMessage = ' (график не удалось создать)';
        }

      } catch (chartError) {
        console.error('Chart creation error:', chartError.toString());
        chartMessage = ' (ошибка графика: ' + chartError.toString() + ')';
      }
    }

    // 10. Возвращаем результат
    const successMessage = '✅ Таблица "' + sheetName + '" создана!' + chartMessage;
    console.log('FINAL RESULT:', successMessage);

    return {
      success: true,
      sheetName: sheetName,
      chartCreated: chartCreated,
      message: successMessage
    };

  } catch (error) {
    console.error('CRITICAL ERROR:', error.toString());
    console.error('Stack:', error.stack);

    return {
      success: false,
      error: error.toString(),
      message: '❌ ОШИБКА: ' + error.toString()
    };
  }
}

/**
 * АЛЬТЕРНАТИВНАЯ ФУНКЦИЯ для создания таблицы (старая совместимость)
 */
function createTableInSheet(structuredData) {
  console.log('[LEGACY] createTableInSheet called, redirecting to createTableAndChart');
  return createTableAndChart(structuredData);
}

/**
 * АЛЬТЕРНАТИВНАЯ ФУНКЦИЯ для создания графика (старая совместимость)
 */
function createChartFromTable(sheetName, dataRange, chartType, title) {
  console.log('[LEGACY] createChartFromTable called');

  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
    if (!sheet) {
      return { success: false, error: 'Sheet not found' };
    }

    const range = sheet.getRange(dataRange);

    // Простейший график
    const chart = sheet.newChart()
      .setChartType(Charts.ChartType.COLUMN)
      .addRange(range)
      .setPosition(2, 5, 0, 0)
      .build();

    sheet.insertChart(chart);

    return { success: true, message: 'Chart created' };

  } catch (e) {
    return { success: false, error: e.toString() };
  }
}

/**
 * ТЕСТОВАЯ ФУНКЦИЯ - запусти вручную в Apps Script
 */
function TEST_SIMPLE_CHART() {
  const testData = {
    headers: ["Товар", "Продажи"],
    rows: [
      ["Товар A", 1000],
      ["Товар B", 1500],
      ["Товар C", 750],
      ["Товар D", 2000],
      ["Товар E", 1200]
    ],
    table_title: "Тест графика v6.4.0",
    chart_recommended: "pie"
  };

  console.log('=== RUNNING TEST ===');
  const result = createTableAndChart(testData);
  console.log('Test result:', JSON.stringify(result));

  // Показываем результат
  SpreadsheetApp.getUi().alert(result.message);

  return result;
}

/**
 * Обработка формул (основная функция для AI)
 */
function processFormula(data) {
  try {
    console.log('=== PROCESS FORMULA START ===');
    console.log('Input:', JSON.stringify(data));

    // Если есть structured_data - создаем таблицу/график
    if (data.structured_data) {
      console.log('Has structured_data, creating table/chart');
      const tableResult = createTableAndChart(data.structured_data);

      return {
        success: true,
        formula: data.formula,
        explanation: data.explanation,
        target_cell: data.target_cell,
        table_created: tableResult.success,
        table_message: tableResult.message,
        structured_data: data.structured_data
      };
    }

    // Если есть формула - применяем её
    if (data.formula && data.target_cell) {
      const sheet = SpreadsheetApp.getActiveSheet();
      const cell = sheet.getRange(data.target_cell);
      cell.setFormula(data.formula);

      return {
        success: true,
        formula: data.formula,
        explanation: data.explanation,
        target_cell: data.target_cell,
        message: 'Формула применена к ячейке ' + data.target_cell
      };
    }

    // Если есть action_type - выполняем действие
    if (data.action_type === 'highlight_rows' && data.highlight_rows) {
      const sheet = SpreadsheetApp.getActiveSheet();
      const color = data.highlight_color || '#FFFF00';

      data.highlight_rows.forEach(function(row) {
        if (row > 0) {
          const range = sheet.getRange(row, 1, 1, sheet.getLastColumn());
          range.setBackground(color);
        }
      });

      return {
        success: true,
        action_type: data.action_type,
        message: data.highlight_message || 'Строки выделены'
      };
    }

    // Просто анализ
    return {
      success: true,
      response_type: data.response_type || 'analysis',
      summary: data.summary,
      key_findings: data.key_findings,
      message: 'Анализ выполнен'
    };

  } catch (error) {
    console.error('processFormula error:', error.toString());
    return {
      success: false,
      error: error.toString(),
      message: 'Ошибка обработки: ' + error.toString()
    };
  }
}

/**
 * Получение данных с активного листа
 */
function getSheetData() {
  try {
    const sheet = SpreadsheetApp.getActiveSheet();
    const lastRow = sheet.getLastRow();
    const lastCol = sheet.getLastColumn();

    if (lastRow === 0 || lastCol === 0) {
      return {
        success: false,
        message: 'Активный лист пуст'
      };
    }

    const range = sheet.getRange(1, 1, lastRow, lastCol);
    const values = range.getValues();

    // Берем первую строку как заголовки
    const headers = values[0];
    const data = values.slice(1);

    return {
      success: true,
      sheetName: sheet.getName(),
      headers: headers,
      data: data,
      rowCount: lastRow,
      columnCount: lastCol
    };

  } catch (error) {
    console.error('getSheetData error:', error.toString());
    return {
      success: false,
      error: error.toString(),
      message: 'Ошибка получения данных: ' + error.toString()
    };
  }
}

/**
 * Проверка работоспособности
 */
function checkHealth() {
  return {
    success: true,
    version: '6.4.0',
    timestamp: new Date().toISOString(),
    message: 'SheetGPT работает нормально'
  };
}

console.log('Code.gs v6.4.0 SIMPLIFIED loaded successfully');