# -*- coding: utf-8 -*-
# Fix the metricMatch regex in sidebar.js to handle labels with colons

with open('C:/Projects/SheetGPT/chrome-extension/src/sidebar.js', 'r', encoding='utf-8') as f:
    content = f.read()

old = """    const metricMatch = line.match(/^([^:]+?):\\s*(.+)$/);
    if (metricMatch) {
      const label = metricMatch[1].trim();
      const value = metricMatch[2].trim();
      if (value && !/^(Рейтинг|Вывод|Итог|Анализ)$/i.test(label)) {
        // Fix concatenated words like "Ивановчек" -> "ср. чек"
        const fixedValue = value.replace(/(\\d)чек/gi, '$1 чек').replace(/срчек/gi, 'ср. чек').replace(/(\\d)руб/gi, '$1 руб');
        dataRows.push({ label, value: fixedValue });
      }
      continue;
    }"""

new = """    // v9.4: Use greedy match (.+) to handle labels with colons like "Веб: камера"
    // Match up to the LAST colon followed by a value (number/text)
    const metricMatch = line.match(/^(.+):\\s*(\\d[\\d\\s,.]*(?:руб|₽|%|шт)?\\.?|.+)$/i);
    if (metricMatch) {
      let label = metricMatch[1].trim();
      const value = metricMatch[2].trim();
      // Clean up any extra colons in label (from malformed data)
      label = label.replace(/:\\s*$/, '').trim();
      if (value && !/^(Рейтинг|Вывод|Итог|Анализ)$/i.test(label)) {
        // Fix concatenated words like "Ивановчек" -> "ср. чек"
        const fixedValue = value.replace(/(\\d)чек/gi, '$1 чек').replace(/срчек/gi, 'ср. чек').replace(/(\\d)руб/gi, '$1 руб');
        dataRows.push({ label, value: fixedValue });
      }
      continue;
    }"""

if old in content:
    content = content.replace(old, new)
    with open('C:/Projects/SheetGPT/chrome-extension/src/sidebar.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: Fixed metricMatch regex')
else:
    print('NOT FOUND - searching...')
    idx = content.find('metricMatch = line.match')
    print(f'Found at index: {idx}')
    if idx > 0:
        print(repr(content[idx:idx+200]))
