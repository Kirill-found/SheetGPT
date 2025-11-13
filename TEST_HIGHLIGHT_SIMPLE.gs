// ПРОСТОЙ ТЕСТ ВЫДЕЛЕНИЯ - скопируй в Apps Script и запусти

function SIMPLE_HIGHLIGHT_TEST() {
  try {
    // Получаем активный лист
    const sheet = SpreadsheetApp.getActiveSheet();

    // Выделяем строки 2, 4, 7 жёлтым цветом
    const result = highlightRows([2, 4, 7], '#FFFF00');

    console.log('Result:', JSON.stringify(result));

    // Показываем результат
    if (result.success) {
      SpreadsheetApp.getUi().alert(
        '✅ УСПЕХ!\n\n' +
        result.message + '\n\n' +
        'Проверьте строки 2, 4 и 7 - они должны быть жёлтыми!'
      );
    } else {
      SpreadsheetApp.getUi().alert('❌ Ошибка: ' + result.message);
    }

    return result;

  } catch (error) {
    SpreadsheetApp.getUi().alert('❌ ОШИБКА: ' + error.toString());
    return { success: false, error: error.toString() };
  }
}

// Тест выделения топ N
function TEST_TOP_HIGHLIGHT() {
  try {
    // Выделяем топ 3 строки по колонке 2 (обычно продажи)
    const result = highlightTopN(2, 3, '#90EE90');

    console.log('Top N result:', JSON.stringify(result));

    SpreadsheetApp.getUi().alert(
      result.success ?
      '✅ Выделены топ 3 строки зелёным!' :
      '❌ Ошибка: ' + result.message
    );

    return result;

  } catch (error) {
    SpreadsheetApp.getUi().alert('❌ ОШИБКА: ' + error.toString());
    return { success: false, error: error.toString() };
  }
}

// Тест выделения по условию
function TEST_CONDITION_HIGHLIGHT() {
  try {
    // Выделяем строки где значение в колонке 2 > 1000
    const result = highlightByCondition(2, '>', 1000, '#FFFF00');

    console.log('Condition result:', JSON.stringify(result));

    SpreadsheetApp.getUi().alert(
      result.success ?
      '✅ Выделены строки где продажи > 1000!' :
      '❌ Ошибка: ' + result.message
    );

    return result;

  } catch (error) {
    SpreadsheetApp.getUi().alert('❌ ОШИБКА: ' + error.toString());
    return { success: false, error: error.toString() };
  }
}