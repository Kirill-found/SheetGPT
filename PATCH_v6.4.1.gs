// ПАТЧ v6.4.1 - ЗАМЕНИ ТОЛЬКО ЭТИ ДВЕ ФУНКЦИИ В СУЩЕСТВУЮЩЕМ Code.gs

// 1. НАЙДИ function createTableAndChart (строка ~997) и ЗАМЕНИ на эту:

function createTableAndChart(structuredData) {
  try {
    console.log('[CHART] createTableAndChart called');
    console.log('[CHART] chart_recommended:', structuredData.chart_recommended);
    console.log('[CHART] headers:', structuredData.headers);
    console.log('[CHART] rows count:', structuredData.rows ? structuredData.rows.length : 0);

    // Сначала создаем таблицу
    const tableResult = createTableInSheet(structuredData);

    if (!tableResult.success) {
      console.log('[CHART] Table creation failed:', tableResult.message);
      return tableResult;
    }

    console.log('[CHART] Table created successfully:', tableResult.sheetName);

    // Если рекомендован график - создаем его
    if (structuredData.chart_recommended) {
      console.log('[CHART] Creating chart with type:', structuredData.chart_recommended);

      const chartResult = createChartFromTable(
        tableResult.sheetName,
        tableResult.dataRange,
        structuredData.chart_recommended,
        structuredData.table_title || 'График анализа'
      );

      console.log('[CHART] Chart result:', JSON.stringify(chartResult));

      // ВАЖНО: Проверяем успешность создания графика
      if (chartResult && !chartResult.success) {
        console.error('[CHART] Chart creation failed:', chartResult.error);
        return {
          success: false,
          table: tableResult,
          chart: chartResult,
          message: `⚠️ Таблица создана, но график не удалось построить: ${chartResult.error || chartResult.message}`
        };
      }

      console.log('[CHART] SUCCESS! Chart created');
      return {
        success: true,
        table: tableResult,
        chart: chartResult,
        message: `✅ Таблица и график "${tableResult.sheetName}" созданы успешно`
      };
    }

    // Если график не рекомендован - возвращаем только результат таблицы
    return {
      success: true,
      table: tableResult,
      chart: null,
      message: tableResult.message
    };

  } catch (error) {
    console.error('[CHART] CRITICAL ERROR:', error.toString());
    console.error('[CHART] Stack:', error.stack);
    return {
      success: false,
      error: error.toString(),
      message: 'Ошибка создания таблицы и графика: ' + error.toString()
    };
  }
}

// 2. НАЙДИ function createChartFromTable (строка ~839) и ЗАМЕНИ на эту:

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

    // Получаем первые 3 строки для логирования
    const values = range.getValues();
    console.log('First 3 rows:', JSON.stringify(values.slice(0, 3)));

    // Определяем тип графика
    let chartTypeEnum;
    switch (chartType) {
      case 'column':
        chartTypeEnum = Charts.ChartType.COLUMN;
        break;
      case 'bar':
        chartTypeEnum = Charts.ChartType.BAR;
        break;
      case 'line':
        chartTypeEnum = Charts.ChartType.LINE;
        break;
      case 'pie':
        chartTypeEnum = Charts.ChartType.PIE;
        break;
      case 'area':
        chartTypeEnum = Charts.ChartType.AREA;
        break;
      case 'scatter':
        chartTypeEnum = Charts.ChartType.SCATTER;
        break;
      default:
        chartTypeEnum = Charts.ChartType.COLUMN;
        console.log('Unknown chart type, using COLUMN as default');
    }

    console.log('Chart type enum:', chartTypeEnum);

    try {
      // СОЗДАЁМ ГРАФИК С МИНИМАЛЬНЫМИ НАСТРОЙКАМИ ДЛЯ МАКСИМАЛЬНОЙ СОВМЕСТИМОСТИ
      console.log('Building chart...');

      const chartBuilder = sheet.newChart()
        .setChartType(chartTypeEnum)
        .addRange(range)
        .setPosition(2, range.getLastColumn() + 2, 0, 0); // Справа от таблицы

      // Добавляем только базовые опции
      chartBuilder
        .setOption('title', title || 'График')
        .setOption('width', 600)
        .setOption('height', 400);

      // Для круговой диаграммы - специальные настройки
      if (chartType === 'pie') {
        chartBuilder.setOption('pieSliceText', 'percentage');
      }

      const chart = chartBuilder.build();
      console.log('Chart built successfully, chart object exists:', !!chart);

      console.log('Inserting chart into sheet...');
      sheet.insertChart(chart);
      console.log('insertChart() completed');

      // Проверяем что график действительно появился
      const charts = sheet.getCharts();
      console.log('Total charts on sheet after insert:', charts.length);

      if (charts.length === 0) {
        console.error('WARNING: Chart was not inserted despite no errors!');
        return {
          success: false,
          error: 'Chart insertion failed silently',
          message: 'График не был создан (возможно, ограничения аккаунта)'
        };
      }

      console.log('=== CREATE CHART SUCCESS ===');

      return {
        success: true,
        sheetName: sheetName,
        chartType: chartType,
        chartsCount: charts.length,
        message: `График "${title}" создан успешно (всего графиков на листе: ${charts.length})`
      };

    } catch (chartError) {
      console.error('Chart building/insertion error:', chartError.toString());
      console.error('Error stack:', chartError.stack);

      return {
        success: false,
        error: chartError.toString(),
        message: 'Ошибка при создании графика: ' + chartError.toString()
      };
    }

  } catch (error) {
    console.error('CREATE CHART ERROR:', error.toString());
    console.error('Error stack:', error.stack);

    return {
      success: false,
      error: error.toString(),
      message: 'Ошибка создания графика: ' + error.toString()
    };
  }
}

// 3. ДОПОЛНИТЕЛЬНО: Добавь эту ТЕСТОВУЮ функцию в конец файла:

function TEST_CHART_CREATION() {
  // Простой тест создания графика
  const testData = {
    headers: ["Продукт", "Продажи"],
    rows: [
      ["Продукт A", 1000],
      ["Продукт B", 1500],
      ["Продукт C", 750],
      ["Продукт D", 2000],
      ["Продукт E", 1200]
    ],
    table_title: "Тест создания графика",
    chart_recommended: "pie"
  };

  console.log('=== STARTING TEST_CHART_CREATION ===');
  console.log('Test data:', JSON.stringify(testData));

  const result = createTableAndChart(testData);

  console.log('Test result:', JSON.stringify(result));

  // Показываем результат пользователю
  const ui = SpreadsheetApp.getUi();
  if (result.success) {
    ui.alert('✅ УСПЕХ!\n\n' + result.message + '\n\nПроверьте новый лист!');
  } else {
    ui.alert('❌ ОШИБКА!\n\n' + result.message);
  }

  return result;
}