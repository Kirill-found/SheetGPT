/**
 * Debug script to find correct Google Sheets DOM selectors
 *
 * ИНСТРУКЦИЯ:
 * 1. Откройте Google Sheets таблицу с данными
 * 2. Откройте DevTools (F12)
 * 3. Скопируйте весь этот код
 * 4. Вставьте в Console и нажмите Enter
 * 5. Скопируйте результаты и отправьте мне
 */

console.log('='.repeat(80));
console.log('🔍 АНАЛИЗ DOM СТРУКТУРЫ GOOGLE SHEETS');
console.log('='.repeat(80));

// 1. Проверяем различные селекторы для строк
const rowSelectors = [
  '.grid-row',
  'tr.row',
  '[role="row"]',
  '[role="rowgroup"] [role="row"]',
  '.waffle tbody tr',
  'table.waffle tr',
  'tbody tr',
  'tr',
  '[data-row]',
  '.ritz .grid-row',
  '.ritz [role="row"]'
];

console.log('\n📋 ПОИСК СТРОК:');
rowSelectors.forEach(selector => {
  const elements = document.querySelectorAll(selector);
  if (elements.length > 0) {
    console.log(`✅ "${selector}" → найдено ${elements.length} элементов`);

    // Показываем первую строку для примера
    const firstRow = elements[0];
    console.log(`   Первая строка:`, firstRow);
    console.log(`   Класс:`, firstRow.className);
    console.log(`   Атрибуты:`, Array.from(firstRow.attributes).map(a => `${a.name}="${a.value}"`).join(', '));
  } else {
    console.log(`❌ "${selector}" → не найдено`);
  }
});

// 2. Проверяем селекторы для ячеек
console.log('\n📋 ПОИСК ЯЧЕЕК:');
const cellSelectors = [
  '[role="gridcell"]',
  '.cell',
  'td',
  '[role="row"] > *',
  '.s0, .s1, .s2, .s3, .s4, .s5',
  '[data-col]'
];

cellSelectors.forEach(selector => {
  const elements = document.querySelectorAll(selector);
  if (elements.length > 0) {
    console.log(`✅ "${selector}" → найдено ${elements.length} элементов`);
    const firstCell = elements[0];
    console.log(`   Первая ячейка:`, firstCell);
    console.log(`   Текст:`, firstCell.textContent);
    console.log(`   Класс:`, firstCell.className);
  } else {
    console.log(`❌ "${selector}" → не найдено`);
  }
});

// 3. Ищем контейнер таблицы
console.log('\n📋 ПОИСК КОНТЕЙНЕРА ТАБЛИЦЫ:');
const containerSelectors = [
  '.grid-container',
  '.waffle',
  '[role="grid"]',
  'table',
  '.ritz',
  '#docs-editor'
];

containerSelectors.forEach(selector => {
  const element = document.querySelector(selector);
  if (element) {
    console.log(`✅ "${selector}" → найден`);
    console.log(`   Элемент:`, element);
    console.log(`   Класс:`, element.className);
  } else {
    console.log(`❌ "${selector}" → не найден`);
  }
});

// 4. Показываем структуру первой строки с данными
console.log('\n📋 СТРУКТУРА ПЕРВОЙ СТРОКИ:');
const possibleRows = document.querySelectorAll('[role="row"], tr, .grid-row');
if (possibleRows.length > 0) {
  const firstRow = possibleRows[0];
  console.log('Первая строка:', firstRow);
  console.log('HTML:', firstRow.outerHTML.substring(0, 500) + '...');

  const cells = firstRow.querySelectorAll('*');
  console.log(`Найдено ${cells.length} дочерних элементов`);
  cells.forEach((cell, i) => {
    if (i < 5) { // Показываем первые 5 ячеек
      console.log(`  Ячейка ${i}:`, {
        tag: cell.tagName,
        class: cell.className,
        text: cell.textContent.substring(0, 50),
        role: cell.getAttribute('role')
      });
    }
  });
}

// 5. Пробуем прочитать данные разными способами
console.log('\n📋 ПОПЫТКА ЧТЕНИЯ ДАННЫХ:');

// Способ 1: canvas-based sheets
const canvasElements = document.querySelectorAll('canvas');
console.log(`Найдено ${canvasElements.length} canvas элементов`);

// Способ 2: поиск по ARIA
const grid = document.querySelector('[role="grid"]');
if (grid) {
  console.log('✅ Найден элемент с role="grid"');
  console.log('   Структура:', grid.outerHTML.substring(0, 500));
}

console.log('\n' + '='.repeat(80));
console.log('✅ АНАЛИЗ ЗАВЕРШЁН. Скопируйте результаты и отправьте разработчику.');
console.log('='.repeat(80));
