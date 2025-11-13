// ЗАМЕНИ createTableAndChart НА ЭТУ ВЕРСИЮ (строка ~997 в Code.gs)

function createTableAndChart(structuredData) {
  try {
    // ВАЖНЫЕ ЛОГИ ДЛЯ ДИАГНОСТИКИ
    console.log('[CHART] createTableAndChart called');
    console.log('[CHART] chart_recommended:', structuredData.chart_recommended);
    console.log('[CHART] headers:', structuredData.headers);
    console.log('[CHART] rows count:', structuredData.rows.length);

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
      if (!chartResult.success) {
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
    return {
      success: false,
      error: error.toString(),
      message: 'Ошибка создания таблицы и графика: ' + error.toString()
    };
  }
}