// УЛУЧШЕННЫЕ ФУНКЦИИ ВЫДЕЛЕНИЯ для Code.gs v6.5.0
// Замените существующие функции на эти версии

/**
 * УНИВЕРСАЛЬНАЯ функция выделения строк/ячеек
 * Поддерживает различные режимы выделения
 */
function highlightRows(rowNumbers, color, options) {
  try {
    console.log('=== HIGHLIGHT ROWS v6.5.0 START ===');
    console.log('Row numbers:', rowNumbers);
    console.log('Color:', color || '#FFFF00');
    console.log('Options:', options);

    // Значения по умолчанию
    const highlightColor = color || '#FFFF00'; // Жёлтый по умолчанию
    const opts = options || {};

    const sheet = SpreadsheetApp.getActiveSheet();
    const lastColumn = sheet.getLastColumn();
    const lastRow = sheet.getLastRow();

    // Валидация
    if (!rowNumbers || !Array.isArray(rowNumbers) || rowNumbers.length === 0) {
      console.warn('No rows to highlight');
      return {
        success: true,
        highlightedCount: 0,
        message: 'Нет строк для выделения'
      };
    }

    // Счетчики
    let highlightedCount = 0;
    const errors = [];

    // Выделяем каждую строку
    for (let rowNum of rowNumbers) {
      try {
        // Проверяем валидность номера строки
        if (rowNum < 1 || rowNum > lastRow) {
          console.warn(`Пропускаем строку ${rowNum} (вне диапазона 1-${lastRow})`);
          continue;
        }

        // Определяем диапазон для выделения
        let range;
        if (opts.columnsOnly && Array.isArray(opts.columnsOnly)) {
          // Выделяем только указанные колонки
          for (let col of opts.columnsOnly) {
            const cellRange = sheet.getRange(rowNum, col, 1, 1);
            cellRange.setBackground(highlightColor);
          }
        } else if (opts.startColumn && opts.endColumn) {
          // Выделяем диапазон колонок
          const colCount = opts.endColumn - opts.startColumn + 1;
          range = sheet.getRange(rowNum, opts.startColumn, 1, colCount);
          range.setBackground(highlightColor);
        } else {
          // Выделяем всю строку
          range = sheet.getRange(rowNum, 1, 1, lastColumn);
          range.setBackground(highlightColor);
        }

        // Дополнительное форматирование
        if (opts.bold && range) {
          range.setFontWeight('bold');
        }
        if (opts.fontColor && range) {
          range.setFontColor(opts.fontColor);
        }
        if (opts.border && range) {
          range.setBorder(true, true, true, true, false, false);
        }

        highlightedCount++;
        console.log(`Строка ${rowNum} выделена цветом ${highlightColor}`);

      } catch (rowError) {
        const errorMsg = `Ошибка выделения строки ${rowNum}: ${rowError.toString()}`;
        console.error(errorMsg);
        errors.push(errorMsg);
      }
    }

    console.log(`=== HIGHLIGHT SUCCESS: ${highlightedCount}/${rowNumbers.length} ===`);

    return {
      success: true,
      highlightedCount: highlightedCount,
      totalRequested: rowNumbers.length,
      errors: errors,
      message: `✅ Выделено ${highlightedCount} из ${rowNumbers.length} строк`
    };

  } catch (error) {
    console.error('HIGHLIGHT ROWS ERROR:', error.toString());
    return {
      success: false,
      error: error.toString(),
      message: '❌ Ошибка выделения: ' + error.toString()
    };
  }
}

/**
 * Выделение строк по условию (например, где значение > 1000)
 */
function highlightByCondition(columnIndex, condition, value, color) {
  try {
    console.log('=== HIGHLIGHT BY CONDITION ===');
    console.log(`Column: ${columnIndex}, Condition: ${condition}, Value: ${value}`);

    const sheet = SpreadsheetApp.getActiveSheet();
    const lastRow = sheet.getLastRow();
    const lastColumn = sheet.getLastColumn();
    const dataRange = sheet.getRange(2, 1, lastRow - 1, lastColumn); // Пропускаем заголовок
    const values = dataRange.getValues();

    const rowsToHighlight = [];
    const highlightColor = color || '#FFFF00';

    // Находим строки по условию
    for (let i = 0; i < values.length; i++) {
      const cellValue = values[i][columnIndex - 1]; // columnIndex начинается с 1
      let matches = false;

      switch (condition) {
        case '>':
          matches = cellValue > value;
          break;
        case '<':
          matches = cellValue < value;
          break;
        case '>=':
          matches = cellValue >= value;
          break;
        case '<=':
          matches = cellValue <= value;
          break;
        case '==':
        case '=':
          matches = cellValue == value;
          break;
        case '!=':
          matches = cellValue != value;
          break;
        case 'contains':
          matches = String(cellValue).toLowerCase().includes(String(value).toLowerCase());
          break;
        case 'starts':
          matches = String(cellValue).toLowerCase().startsWith(String(value).toLowerCase());
          break;
        case 'ends':
          matches = String(cellValue).toLowerCase().endsWith(String(value).toLowerCase());
          break;
        default:
          console.warn('Unknown condition:', condition);
      }

      if (matches) {
        rowsToHighlight.push(i + 2); // +2 потому что пропустили заголовок и индекс с 0
        console.log(`Row ${i + 2} matches condition: ${cellValue} ${condition} ${value}`);
      }
    }

    // Выделяем найденные строки
    if (rowsToHighlight.length > 0) {
      return highlightRows(rowsToHighlight, highlightColor);
    } else {
      return {
        success: true,
        highlightedCount: 0,
        message: 'Не найдено строк, соответствующих условию'
      };
    }

  } catch (error) {
    console.error('HIGHLIGHT BY CONDITION ERROR:', error.toString());
    return {
      success: false,
      error: error.toString(),
      message: 'Ошибка выделения по условию: ' + error.toString()
    };
  }
}

/**
 * Выделение топ N строк по значению в колонке
 */
function highlightTopN(columnIndex, topN, color, descending = true) {
  try {
    console.log('=== HIGHLIGHT TOP N ===');
    console.log(`Column: ${columnIndex}, Top N: ${topN}, Descending: ${descending}`);

    const sheet = SpreadsheetApp.getActiveSheet();
    const lastRow = sheet.getLastRow();
    const lastColumn = sheet.getLastColumn();

    // Получаем данные (пропускаем заголовок)
    const dataRange = sheet.getRange(2, 1, lastRow - 1, lastColumn);
    const values = dataRange.getValues();

    // Создаём массив с индексами и значениями
    const indexedValues = values.map((row, index) => ({
      rowNumber: index + 2, // +2 потому что пропустили заголовок и индекс с 0
      value: row[columnIndex - 1] // columnIndex начинается с 1
    }));

    // Сортируем
    indexedValues.sort((a, b) => {
      if (descending) {
        return b.value - a.value; // По убыванию
      } else {
        return a.value - b.value; // По возрастанию
      }
    });

    // Берём топ N
    const topRows = indexedValues.slice(0, topN).map(item => item.rowNumber);
    console.log('Top rows:', topRows);

    // Выделяем
    const highlightColor = color || '#90EE90'; // Светло-зелёный для топ значений
    return highlightRows(topRows, highlightColor);

  } catch (error) {
    console.error('HIGHLIGHT TOP N ERROR:', error.toString());
    return {
      success: false,
      error: error.toString(),
      message: 'Ошибка выделения топ строк: ' + error.toString()
    };
  }
}

/**
 * Сброс выделения (убирает цвет фона)
 */
function clearHighlighting(rowNumbers) {
  try {
    console.log('=== CLEAR HIGHLIGHTING ===');

    const sheet = SpreadsheetApp.getActiveSheet();
    const lastColumn = sheet.getLastColumn();
    const lastRow = sheet.getLastRow();

    if (!rowNumbers || rowNumbers.length === 0) {
      // Сбрасываем ВСЁ выделение
      console.log('Clearing all highlighting');
      const allRange = sheet.getRange(1, 1, lastRow, lastColumn);
      allRange.setBackground(null);

      // Восстанавливаем выделение заголовка
      const headerRange = sheet.getRange(1, 1, 1, lastColumn);
      headerRange.setBackground('#4285F4');

      return {
        success: true,
        message: 'Всё выделение сброшено'
      };
    } else {
      // Сбрасываем выделение конкретных строк
      let clearedCount = 0;
      for (let rowNum of rowNumbers) {
        if (rowNum > 1 && rowNum <= lastRow) { // Не трогаем заголовок
          const rowRange = sheet.getRange(rowNum, 1, 1, lastColumn);
          rowRange.setBackground(null);
          clearedCount++;
        }
      }

      return {
        success: true,
        clearedCount: clearedCount,
        message: `Выделение сброшено для ${clearedCount} строк`
      };
    }

  } catch (error) {
    console.error('CLEAR HIGHLIGHTING ERROR:', error.toString());
    return {
      success: false,
      error: error.toString(),
      message: 'Ошибка сброса выделения: ' + error.toString()
    };
  }
}

/**
 * ТЕСТОВАЯ функция - демонстрирует все возможности выделения
 */
function TEST_HIGHLIGHTING() {
  try {
    // Создаём тестовые данные
    const sheet = SpreadsheetApp.getActiveSpreadsheet().insertSheet('Тест выделения');

    // Заголовки
    const headers = ['Продукт', 'Продажи', 'Категория', 'Статус'];
    const data = [
      ['Продукт A', 1500, 'Электроника', 'Активен'],
      ['Продукт B', 2500, 'Одежда', 'Активен'],
      ['Продукт C', 500, 'Электроника', 'Неактивен'],
      ['Продукт D', 3000, 'Мебель', 'Активен'],
      ['Продукт E', 1200, 'Одежда', 'Активен'],
      ['Продукт F', 800, 'Электроника', 'Неактивен'],
      ['Продукт G', 4000, 'Мебель', 'Активен'],
      ['Продукт H', 600, 'Одежда', 'Неактивен'],
      ['Продукт I', 2200, 'Электроника', 'Активен'],
      ['Продукт J', 1800, 'Мебель', 'Активен']
    ];

    // Вставляем данные
    sheet.getRange(1, 1, 1, 4).setValues([headers]);
    sheet.getRange(2, 1, 10, 4).setValues(data);

    // Форматируем заголовок
    const headerRange = sheet.getRange(1, 1, 1, 4);
    headerRange
      .setFontWeight('bold')
      .setBackground('#4285F4')
      .setFontColor('#FFFFFF');

    // Тест 1: Выделяем топ 3 по продажам
    console.log('\n--- ТЕСТ 1: Топ 3 по продажам ---');
    SpreadsheetApp.getUi().alert('Тест 1: Выделяем топ 3 продукта по продажам (зелёным)');
    const result1 = highlightTopN(2, 3, '#90EE90'); // Колонка 2 - продажи
    console.log('Результат:', result1);

    Utilities.sleep(2000);

    // Тест 2: Выделяем продажи > 2000
    console.log('\n--- ТЕСТ 2: Продажи > 2000 ---');
    SpreadsheetApp.getUi().alert('Тест 2: Выделяем продукты с продажами > 2000 (жёлтым)');
    const result2 = highlightByCondition(2, '>', 2000, '#FFFF00');
    console.log('Результат:', result2);

    Utilities.sleep(2000);

    // Тест 3: Выделяем неактивные продукты
    console.log('\n--- ТЕСТ 3: Неактивные продукты ---');
    SpreadsheetApp.getUi().alert('Тест 3: Выделяем неактивные продукты (красным)');
    const result3 = highlightByCondition(4, '==', 'Неактивен', '#FFB6C1');
    console.log('Результат:', result3);

    Utilities.sleep(2000);

    // Тест 4: Сбрасываем выделение топ 3
    console.log('\n--- ТЕСТ 4: Сброс выделения ---');
    SpreadsheetApp.getUi().alert('Тест 4: Сбрасываем выделение топ 3 продуктов');
    const result4 = clearHighlighting([4, 7, 11]); // Строки с топ продажами
    console.log('Результат:', result4);

    // Финальное сообщение
    SpreadsheetApp.getUi().alert(
      '✅ ТЕСТЫ ЗАВЕРШЕНЫ!\n\n' +
      'Проверьте лист "Тест выделения":\n' +
      '- Жёлтым выделены продажи > 2000\n' +
      '- Красным выделены неактивные продукты\n' +
      '- Выделение топ 3 было сброшено'
    );

    return {
      success: true,
      message: 'Все тесты выделения выполнены'
    };

  } catch (error) {
    console.error('TEST ERROR:', error.toString());
    SpreadsheetApp.getUi().alert('❌ Ошибка теста: ' + error.toString());
    return {
      success: false,
      error: error.toString()
    };
  }
}