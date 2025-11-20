/**
 * SheetGPT Custom Functions v2.0.0
 * Одна универсальная функция - AI сам определяет формат ответа!
 *
 * @author SheetGPT
 * @version 2.0.0
 */

// Backend API URL
const API_URL_FUNCTIONS = 'https://sheetgpt-production.up.railway.app';

/**
 * GPT - Универсальная AI функция (автоматически определяет формат ответа)
 *
 * @param {string} query Ваш вопрос или запрос к AI
 * @param {range} [dataRange] Диапазон данных для анализа (опционально)
 * @return {string|number|array} Ответ от AI (текст, число, список или таблица)
 * @customfunction
 *
 * @example
 * // Текстовый ответ
 * =GPT("Кто лучший менеджер?", A1:C10)
 *
 * // Число
 * =GPT("Какая сумма продаж?", A1:C10)
 *
 * // Список (вертикальный)
 * =GPT("Топ 5 продуктов", A1:C10)
 *
 * // Таблица
 * =GPT("Группировка по менеджерам с суммой", A1:C10)
 */
function GPT(query, dataRange) {
  if (!query) {
    return "Ошибка: укажите запрос";
  }

  try {
    // Получаем данные из диапазона если указан
    let sheetData = [];
    let columnNames = [];

    if (dataRange) {
      // dataRange уже содержит значения ячеек (массив), не нужно вызывать getRange()
      const values = Array.isArray(dataRange) ? dataRange : [[dataRange]];
      if (values.length > 0) {
        columnNames = values[0];
        sheetData = values.slice(1);
      }
    } else {
      // Используем данные текущего листа
      const sheet = SpreadsheetApp.getActiveSheet();
      const lastRow = sheet.getLastRow();
      const lastCol = sheet.getLastColumn();

      if (lastRow > 1 && lastCol > 0) {
        const allData = sheet.getRange(1, 1, lastRow, lastCol).getValues();
        columnNames = allData[0];
        sheetData = allData.slice(1);
      }
    }

    // Вызываем API
    const response = UrlFetchApp.fetch(`${API_URL_FUNCTIONS}/api/v1/formula`, {
      method: 'POST',
      contentType: 'application/json',
      muteHttpExceptions: true,
      payload: JSON.stringify({
        query: query,
        column_names: columnNames,
        sheet_data: sheetData
      })
    });

    const result = JSON.parse(response.getContentText());

    // ========================================
    // 🎯 УМНОЕ ОПРЕДЕЛЕНИЕ ФОРМАТА ОТВЕТА
    // ========================================

    // 1️⃣ ТАБЛИЦА: Если backend вернул structured_data с headers и rows
    if (result.structured_data) {
      const data = result.structured_data;

      // Формат: {headers: [...], rows: [[...]]}
      if (data.headers && data.rows && data.rows.length > 0) {
        // Проверяем: это таблица (>1 колонки) или список (1 колонка)?
        if (data.headers.length > 1) {
          // Таблица - возвращаем с заголовками
          return [data.headers, ...data.rows];
        } else {
          // Список - возвращаем только значения без заголовка
          return data.rows;
        }
      }

      // Формат: {columns: [...], data: [...]}
      if (data.columns && data.data) {
        const headers = data.columns.map(col => col.name || col);
        const rows = data.data.map(row => {
          return data.columns.map(col => {
            const colName = col.name || col;
            return row[colName] !== undefined ? row[colName] : '';
          });
        });

        if (headers.length > 1) {
          return [headers, ...rows];
        } else {
          return rows;
        }
      }
    }

    // 2️⃣ СПИСОК: Если есть key_findings (инсайты) как список
    if (result.key_findings && result.key_findings.length > 1) {
      // Вертикальный список
      return result.key_findings.map(item => [item]);
    }

    // 3️⃣ ЧИСЛО: Если запрос про сумму/среднее/количество
    const summary = result.summary || result.explanation || '';
    const isNumericQuery = query.match(/(сумм|средн|количеств|итог|всего|макс|мин|процент|скольк)/i);

    if (isNumericQuery && summary) {
      // Ищем число в ответе (поддержка форматов: 123,456.78 или 123456)
      const numberMatch = summary.match(/[\d,]+\.?\d*/);
      if (numberMatch) {
        const numStr = numberMatch[0].replace(/,/g, '');
        const num = parseFloat(numStr);
        if (!isNaN(num)) {
          return num;
        }
      }
    }

    // 4️⃣ ТЕКСТ: По умолчанию возвращаем текстовый ответ
    if (result.summary) {
      return result.summary;
    } else if (result.explanation) {
      return result.explanation;
    } else if (result.answer) {
      return result.answer;
    } else {
      return "AI обработал запрос успешно";
    }

  } catch (error) {
    return `Ошибка: ${error.message}`;
  }
}

/**
 * GPT_DEBUG - Показывает сырой ответ от API (для отладки)
 *
 * @param {string} query Ваш вопрос
 * @param {range} [dataRange] Диапазон данных (опционально)
 * @return {string} JSON ответ от API
 * @customfunction
 */
function GPT_DEBUG(query, dataRange) {
  if (!query) {
    return "Ошибка: укажите запрос";
  }

  try {
    let sheetData = [];
    let columnNames = [];

    if (dataRange) {
      // dataRange уже содержит значения ячеек (массив), не нужно вызывать getRange()
      const values = Array.isArray(dataRange) ? dataRange : [[dataRange]];
      if (values.length > 0) {
        columnNames = values[0];
        sheetData = values.slice(1);
      }
    }

    const response = UrlFetchApp.fetch(`${API_URL_FUNCTIONS}/api/v1/formula`, {
      method: 'POST',
      contentType: 'application/json',
      muteHttpExceptions: true,
      payload: JSON.stringify({
        query: query,
        column_names: columnNames,
        sheet_data: sheetData
      })
    });

    const result = JSON.parse(response.getContentText());

    // Возвращаем красиво отформатированный JSON
    return JSON.stringify(result, null, 2);

  } catch (error) {
    return `Ошибка: ${error.message}`;
  }
}
