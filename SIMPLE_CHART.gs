// ПРОСТАЯ РАБОЧАЯ ВЕРСИЯ - замени createTableAndChart на эту

function createTableAndChart(structuredData) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();

    // 1. Создаем новый лист
    const sheetName = 'Тест ' + new Date().getTime();
    const sheet = ss.insertSheet(sheetName);

    // 2. Вставляем данные
    const headers = structuredData.headers || ['Название', 'Значение'];
    const rows = structuredData.rows || [];

    // Вставляем заголовки
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

    // Вставляем строки
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    }

    // 3. Создаем график
    const dataRange = sheet.getRange(1, 1, rows.length + 1, headers.length);

    const chart = sheet.newChart()
      .setChartType(Charts.ChartType.PIE)
      .addRange(dataRange)
      .setPosition(2, 4, 0, 0)  // Справа от таблицы
      .setOption('title', 'Круговая диаграмма')
      .setOption('width', 600)
      .setOption('height', 400)
      .build();

    sheet.insertChart(chart);

    return {
      success: true,
      message: 'Таблица и график созданы в листе: ' + sheetName
    };

  } catch (e) {
    return {
      success: false,
      error: e.toString(),
      message: 'ОШИБКА: ' + e.toString()
    };
  }
}
