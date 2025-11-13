// DEBUG VERSION - заменить функцию createTableAndChart на эту

function createTableAndChart(structuredData) {
  console.log('[DEBUG] createTableAndChart called');
  console.log('[DEBUG] structuredData:', JSON.stringify(structuredData));

  try {
    // Проверка входных данных
    if (!structuredData) {
      console.log('[DEBUG] ERROR: structuredData is null/undefined');
      return {
        success: false,
        error: 'structuredData is null',
        message: 'DEBUG: Данные не переданы'
      };
    }

    if (!structuredData.headers || !structuredData.rows) {
      console.log('[DEBUG] ERROR: Missing headers or rows');
      return {
        success: false,
        error: 'Missing headers or rows',
        message: 'DEBUG: Отсутствуют headers или rows'
      };
    }

    console.log('[DEBUG] Data validation OK');
    console.log('[DEBUG] Calling createTableInSheet...');

    // Создаем таблицу
    const tableResult = createTableInSheet(structuredData);

    console.log('[DEBUG] createTableInSheet returned:', JSON.stringify(tableResult));

    if (!tableResult.success) {
      console.log('[DEBUG] Table creation failed');
      return tableResult;
    }

    console.log('[DEBUG] Table created successfully');
    console.log('[DEBUG] chart_recommended:', structuredData.chart_recommended);

    // Если рекомендован график
    if (structuredData.chart_recommended) {
      console.log('[DEBUG] Creating chart...');
      console.log('[DEBUG] Chart params:', {
        sheetName: tableResult.sheetName,
        dataRange: tableResult.dataRange,
        chartType: structuredData.chart_recommended,
        title: structuredData.table_title
      });

      const chartResult = createChartFromTable(
        tableResult.sheetName,
        tableResult.dataRange,
        structuredData.chart_recommended,
        structuredData.table_title || 'График анализа'
      );

      console.log('[DEBUG] Chart created:', JSON.stringify(chartResult));

      return {
        success: true,
        table: tableResult,
        chart: chartResult,
        message: `DEBUG SUCCESS: Таблица и график "${tableResult.sheetName}" созданы!`
      };
    }

    console.log('[DEBUG] No chart recommended, returning table only');

    return {
      success: true,
      table: tableResult,
      chart: null,
      message: 'DEBUG: ' + tableResult.message
    };

  } catch (error) {
    console.log('[DEBUG] EXCEPTION:', error.toString());
    console.log('[DEBUG] Stack:', error.stack);

    return {
      success: false,
      error: error.toString(),
      message: 'DEBUG ERROR: ' + error.toString()
    };
  }
}
