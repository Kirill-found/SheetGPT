// ЗАМЕНИ createChartFromTable НА ЭТУ УПРОЩЕННУЮ ВЕРСИЮ

function createChartFromTable(sheetName, dataRange, chartType, title) {
  try {
    console.log('=== CREATE CHART START ===');
    console.log('Sheet:', sheetName);
    console.log('Range:', dataRange);
    console.log('Type:', chartType);
    console.log('Title:', title);

    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = spreadsheet.getSheetByName(sheetName);

    if (!sheet) {
      console.error('Sheet not found:', sheetName);
      return {
        success: false,
        error: 'Sheet not found: ' + sheetName,
        message: 'Лист не найден: ' + sheetName
      };
    }

    // Получаем диапазон данных
    const range = sheet.getRange(dataRange);
    console.log('Range object created:', range.getA1Notation());
    console.log('Range dimensions:', range.getNumRows(), 'x', range.getNumColumns());

    // ПРОСТЕЙШИЙ ГРАФИК БЕЗ СЛОЖНЫХ ОПЦИЙ
    let chartTypeEnum = Charts.ChartType.COLUMN; // По умолчанию столбчатая

    if (chartType === 'pie') {
      chartTypeEnum = Charts.ChartType.PIE;
    } else if (chartType === 'bar') {
      chartTypeEnum = Charts.ChartType.BAR;
    } else if (chartType === 'line') {
      chartTypeEnum = Charts.ChartType.LINE;
    }

    console.log('Chart type enum:', chartTypeEnum);
    console.log('Building chart...');

    // СОЗДАЁМ ГРАФИК С МИНИМУМОМ ОПЦИЙ
    const chart = sheet.newChart()
      .setChartType(chartTypeEnum)
      .addRange(range)
      .setPosition(2, 4, 0, 0)  // Строка 2, колонка 4 (справа от таблицы)
      .setOption('title', title || 'График')
      .setOption('width', 600)
      .setOption('height', 400)
      .build();

    console.log('Chart built, inserting...');
    sheet.insertChart(chart);
    console.log('Chart inserted!');

    // Проверяем что график появился
    const charts = sheet.getCharts();
    console.log('Total charts on sheet:', charts.length);

    if (charts.length === 0) {
      console.error('ERROR: Chart was not created!');
      return {
        success: false,
        error: 'Chart was not inserted',
        message: 'График не был создан на листе'
      };
    }

    console.log('=== CREATE CHART SUCCESS ===');

    // ВАЖНО: Возвращаем объект с success
    return {
      success: true,
      sheetName: sheetName,
      chartType: chartType,
      chartsCount: charts.length,
      message: 'График "' + title + '" создан успешно'
    };

  } catch (error) {
    console.error('CREATE CHART ERROR:', error.toString());
    console.error('Stack trace:', error.stack);

    return {
      success: false,
      error: error.toString(),
      message: 'Ошибка создания графика: ' + error.toString()
    };
  }
}