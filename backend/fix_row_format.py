# -*- coding: utf-8 -*-
# Fix the row format explanation

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the format section
old_format = '''КРИТИЧНО - ФОРМАТ explanation:
- ПЕРВАЯ СТРОКА = ПРЯМОЙ ОТВЕТ на вопрос
- Каждая запись на ОДНОЙ строке целиком!
- Формат: "Строка N: значение1, значение2, значение3"
- ВСЕГДА "Строка " + ПРОБЕЛ + номер + двоеточие + данные
- НИКОГДА не пиши "СтрокаПродукт" или "Строка5" - ВСЕГДА пробел!
- НЕ разбивай данные одной строки на несколько строк!
- НЕ используй = или ' - пиши просто значения через запятую
- Пустая строка только между разными категориями'''

new_format = '''КРИТИЧНО - ФОРМАТ explanation:
- ПЕРВАЯ СТРОКА = ПРЯМОЙ ОТВЕТ на вопрос
- "Строка N:" означает НОМЕР СТРОКИ в таблице (Row N), НЕ название колонки!
- ПРАВИЛЬНО: "Строка 5: Рюкзак, 12 шт, 4999 руб"
- НЕПРАВИЛЬНО: "СтрокаПродукт Рюкзак" - ЭТО ОШИБКА!
- Формат: f"Строка {idx+2}: {row['Продукт']}, {row['Количество']} шт, {row['Цена']} руб"
- ВСЕ данные одной записи на ОДНОЙ строке!
- НЕ используй = или кавычки в выводе'''

content = content.replace(old_format, new_format)

# Also fix the example format
old_example = '''ПРИМЕР ПРАВИЛЬНОГО ФОРМАТА:
explanation = "Корректная выручка - когда выручка > 0 и равна цена * количество.\\n\\n"
explanation += "Всего корректных: 101 из 200\\n\\n"
explanation += "Примеры:\\n"
explanation += "Строка 2: Рюкзак, 12 шт, 4999 руб, выручка 59988\\n"
explanation += "Строка 3: Пауэрбанк, 10 шт, 2500 руб, выручка 25000\\n"'''

new_example = '''ПРИМЕР ПРАВИЛЬНОГО ФОРМАТА:
explanation = "Корректная выручка - когда выручка > 0 и равна цена * количество.\\n\\n"
explanation += "Всего корректных: 101 из 200\\n\\n"
explanation += "Примеры корректных записей:\\n"
for idx, row in correct_rows.head(3).iterrows():
    explanation += f"Строка {idx+2}: {row['Продукт']}, {row['Количество']} шт, {row['Цена']} руб\\n"
# Результат: "Строка 5: Рюкзак, 12 шт, 4999 руб"'''

content = content.replace(old_example, new_example)

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed row format instructions')
