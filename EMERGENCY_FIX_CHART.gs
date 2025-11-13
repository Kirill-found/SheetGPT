// ЭКСТРЕННОЕ ИСПРАВЛЕНИЕ - ЗАМЕНИ createTableAndChart НА ЭТУ ВЕРСИЮ

function createTableAndChart(structuredData) {
  try {
    console.log('[EMERGENCY] Starting createTableAndChart');
    console.log('[EMERGENCY] chart_recommended:', structuredData.chart_recommended);

    // Сначала создаем таблицу
    const tableResult = createTableInSheet(structuredData);

    if (!tableResult.success) {
      console.log('[EMERGENCY] Table creation failed');
      return tableResult;
    }

    console.log('[EMERGENCY] Table created successfully:', tableResult.sheetName);

    // Если рекомендован график - создаем ПРОСТЕЙШИЙ ГРАФИК
    if (structuredData.chart_recommended) {
      console.log('[EMERGENCY] Creating SIMPLE chart');

      try {
        const ss = SpreadsheetApp.getActiveSpreadsheet();
        const sheet = ss.getSheetByName(tableResult.sheetName);

        if (!sheet) {
          throw new Error('Sheet not found: ' + tableResult.sheetName);
        }

        // Получаем диапазон с данными
        const numRows = structuredData.rows.length + 1; // +1 для заголовков
        const numCols = structuredData.headers.length;
        const dataRange = sheet.getRange(1, 1, numRows, numCols);

        console.log('[EMERGENCY] Data range:', dataRange.getA1Notation());

        // ПРОСТЕЙШИЙ ГРАФИК БЕЗ ВСЯКИХ ОПЦИЙ
        const chart = sheet.newChart()
          .setChartType(Charts.ChartType.PIE)
          .addRange(dataRange)
          .setPosition(2, 4, 0, 0)  // Строка 2, колонка 4
          .setOption('title', 'Круговая диаграмма')
          .setOption('width', 600)
          .setOption('height', 400)
          .build();

        console.log('[EMERGENCY] Chart built, inserting...');
        sheet.insertChart(chart);
        console.log('[EMERGENCY] Chart inserted!');

        // Проверяем что график появился
        const charts = sheet.getCharts();
        console.log('[EMERGENCY] Total charts on sheet:', charts.length);

        if (charts.length === 0) {
          throw new Error('Chart was not created!');
        }

        return {
          success: true,
          table: tableResult,
          chart: { success: true, message: 'Chart created' },
          message: `✅ Таблица и график созданы! Графиков на листе: ${charts.length}`
        };

      } catch (chartError) {
        console.error('[EMERGENCY] Chart creation error:', chartError);
        return {
          success: false,
          table: tableResult,
          chart: { success: false, error: chartError.toString() },
          message: `❌ Таблица создана, но график не удалось создать: ${chartError.toString()}`
        };
      }
    }

    // Если график не нужен
    return {
      success: true,
      table: tableResult,
      chart: null,
      message: tableResult.message
    };

  } catch (error) {
    console.error('[EMERGENCY] CRITICAL ERROR:', error);
    return {
      success: false,
      error: error.toString(),
      message: 'Ошибка: ' + error.toString()
    };
  }
}

// ТЕСТОВАЯ ФУНКЦИЯ - ЗАПУСТИ ЕЁ ВРУЧНУЮ В APPS SCRIPT
function TEST_EMERGENCY_CHART() {
  const testData = {
    headers: ["Товар", "Продажи"],
    rows: [
      ["Товар 1", 100],
      ["Товар 2", 200],
      ["Товар 3", 150],
      ["Товар 4", 300],
      ["Товар 5", 250]
    ],
    table_title: "Тест экстренного исправления",
    chart_recommended: "pie"
  };

  console.log('=== RUNNING EMERGENCY TEST ===');
  const result = createTableAndChart(testData);
  console.log('Result:', JSON.stringify(result));

  if (result.success) {
    SpreadsheetApp.getUi().alert('✅ УСПЕХ!\n\nГрафик создан!');
  } else {
    SpreadsheetApp.getUi().alert('❌ ОШИБКА!\n\n' + result.message);
  }

  return result;
}