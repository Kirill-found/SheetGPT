// ТЕСТОВАЯ ФУНКЦИЯ - скопируй в Apps Script и запусти вручную

function TEST_createChart() {
  // Тестовые данные
  const testData = {
    "headers": ["Товар", "Продажи"],
    "rows": [
      ["Товар 1", 1000],
      ["Товар 2", 2000],
      ["Товар 3", 1500],
      ["Товар 4", 3000],
      ["Товар 5", 2500]
    ],
    "table_title": "Тест диаграммы",
    "chart_recommended": "pie"
  };

  Logger.log('=== STARTING TEST ===');
  Logger.log('Test data: ' + JSON.stringify(testData));

  try {
    // Вызываем функцию
    const result = createTableAndChart(testData);

    Logger.log('=== RESULT ===');
    Logger.log('Success: ' + result.success);
    Logger.log('Message: ' + result.message);
    if (result.error) {
      Logger.log('ERROR: ' + result.error);
    }

    // Показываем результат в UI
    if (result.success) {
      SpreadsheetApp.getUi().alert('✅ УСПЕХ!\n\n' + result.message);
    } else {
      SpreadsheetApp.getUi().alert('❌ ОШИБКА!\n\n' + (result.message || result.error));
    }

    return result;

  } catch (error) {
    Logger.log('=== EXCEPTION ===');
    Logger.log(error.toString());
    Logger.log(error.stack);

    SpreadsheetApp.getUi().alert('❌ КРИТИЧЕСКАЯ ОШИБКА!\n\n' + error.toString());
    throw error;
  }
}

// Чтобы посмотреть логи:
// 1. В Apps Script выбери функцию TEST_createChart
// 2. Нажми Run (▶️)
// 3. После выполнения нажми View → Executions (или Ctrl+Enter)
