# -*- coding: utf-8 -*-
# Simplify format - remove "Строка" completely, use simple numbering

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the format rules with simpler version
old_format = '''КРИТИЧНО - ФОРМАТ explanation:
- ПЕРВАЯ СТРОКА = ПРЯМОЙ ОТВЕТ на вопрос
- "Строка N:" означает НОМЕР СТРОКИ в таблице (Row N), НЕ название колонки!
- ПРАВИЛЬНО: "Строка 5: Рюкзак, 12 шт, 4999 руб"
- НЕПРАВИЛЬНО: "СтрокаПродукт Рюкзак" - ЭТО ОШИБКА!
- Формат: f"Строка {idx+2}: {row['Продукт']}, {row['Количество']} шт, {row['Цена']} руб"
- ВСЕ данные одной записи на ОДНОЙ строке!
- НЕ используй = или кавычки в выводе'''

new_format = '''КРИТИЧНО - ФОРМАТ explanation:
- ПЕРВАЯ СТРОКА = ПРЯМОЙ ОТВЕТ на вопрос
- Используй ПРОСТУЮ НУМЕРАЦИЮ для списков: "1.", "2.", "3."
- НЕ используй слово "Строка" - просто номер и точка!
- Формат записи: f"{i}. {row['Продукт']}, {row['Количество']} шт, {row['Цена']} руб"
- ВСЕ данные одной записи на ОДНОЙ строке!
- НЕ используй = или кавычки в выводе
- НЕ разбивай одну запись на несколько строк!'''

content = content.replace(old_format, new_format)

# Fix the example
old_example = '''ПРИМЕР ПРАВИЛЬНОГО ФОРМАТА:
explanation = "Корректная выручка - когда выручка > 0 и равна цена * количество.\\n\\n"
explanation += "Всего корректных: 101 из 200\\n\\n"
explanation += "Примеры корректных записей:\\n"
for idx, row in correct_rows.head(3).iterrows():
    explanation += f"Строка {idx+2}: {row['Продукт']}, {row['Количество']} шт, {row['Цена']} руб\\n"
# Результат: "Строка 5: Рюкзак, 12 шт, 4999 руб"'''

new_example = '''ПРИМЕР ПРАВИЛЬНОГО ФОРМАТА:
explanation = "Корректная выручка - когда выручка > 0 и равна цена * количество.\\n\\n"
explanation += "Всего корректных: 101 из 200\\n\\n"
explanation += "Примеры:\\n"
for i, (idx, row) in enumerate(correct_rows.head(3).iterrows(), 1):
    explanation += f"{i}. {row['Продукт']}, {row['Количество']} шт, {row['Цена']} руб\\n"
# Результат:
# "1. Рюкзак, 12 шт, 4999 руб"
# "2. Кружка, 5 шт, 500 руб"'''

content = content.replace(old_example, new_example)

# Fix anomaly example too
old_anomaly = '''5. Для АНАЛИЗА АНОМАЛИЙ (проверь данные, найди ошибки, что не так):
# КРИТИЧНО: Каждая запись на ОДНОЙ строке! БЕЗ знаков равно!
explanation = "Найдены аномалии:\\n\\n"
explanation += "1. Отрицательные значения (5 записей):\\n"
for idx, row in negative_rows.head(3).iterrows():
    explanation += f"Строка {idx+2}: {row['Товар']}, количество {row['Количество']}\\n"
explanation += "\\n2. Пустые значения (12 записей):\\n"
for idx, row in empty_rows.head(3).iterrows():
    explanation += f"Строка {idx+2}: {row['Товар']}, пустое поле {col}\\n"
explanation += f"\\nИтого проблем: {total_issues}"'''

new_anomaly = '''5. Для АНАЛИЗА АНОМАЛИЙ (проверь данные, найди ошибки, что не так):
# Используй простую нумерацию! Каждая запись на ОДНОЙ строке!
explanation = "Найдены аномалии:\\n\\n"
explanation += "Отрицательные значения (5 записей):\\n"
for i, (idx, row) in enumerate(negative_rows.head(3).iterrows(), 1):
    explanation += f"  {i}. {row['Товар']}, количество {row['Количество']}\\n"
explanation += "\\nПустые значения (12 записей):\\n"
for i, (idx, row) in enumerate(empty_rows.head(3).iterrows(), 1):
    explanation += f"  {i}. {row['Товар']}, пустое поле {col}\\n"
explanation += f"\\nИтого проблем: {total_issues}"'''

content = content.replace(old_anomaly, new_anomaly)

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Simplified format - removed Строка, using simple numbering')
