// ЗАМЕНИ processQuery ФУНКЦИЮ НА ЭТУ (строки 262-360):

function processQuery(query) {
  try {
    const sheetData = getSheetData();
    const history = getConversationHistory();

    if (!query || query === 'undefined' || typeof query === 'undefined') {
      throw new Error('Запрос пустой. Пожалуйста, введите вопрос.');
    }

    // 🔥🔥🔥 ПРИНУДИТЕЛЬНОЕ РЕШЕНИЕ - ВСЕГДА БЕЗ ЗАГОЛОВКОВ! 🔥🔥🔥
    const numColumns = sheetData.data[0] ? sheetData.data[0].length : 5;
    const columnNames = [];
    for (let i = 0; i < numColumns; i++) {
      columnNames.push(`Колонка ${String.fromCharCode(65 + i)}`);  // A, B, C, D, E
    }
    const dataToSend = sheetData.data.slice(0, 10);  // Берём ВСЕ 10 строк БЕЗ пропусков!

    console.log('🔥 FORCE MODE: NO HEADERS!');
    console.log('Columns:', columnNames);
    console.log('Data rows:', dataToSend.length);
    console.log('First row:', dataToSend[0]);

    const payload = {
      query: query,
      column_names: columnNames,
      sheet_data: dataToSend,
      history: history
    };

    // Показать что отправляем (раскомментируй для отладки):
    // SpreadsheetApp.getUi().alert('ОТПРАВЛЯЕМ',
    //   `Колонки: ${columnNames.join(', ')}\nСтрок: ${dataToSend.length}`,
    //   SpreadsheetApp.getUi().ButtonSet.OK);

    const options = {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(API_URL + '/api/v1/formula', options);
    const result = JSON.parse(response.getContentText());

    if (response.getResponseCode() === 200) {
      const historyItem = {
        query: query,
        actions: result.insights || []
      };
      history.push(historyItem);
      saveConversationHistory(history);

      return {
        formula: result.formula || null,
        explanation: result.explanation || '',
        target_cell: result.target_cell || null,
        confidence: result.confidence || 0,
        response_type: result.response_type || 'formula',
        insights: result.insights || [],
        suggested_actions: result.suggested_actions || null,
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