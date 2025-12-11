# -*- coding: utf-8 -*-
# Fix the SYSTEM_PROMPT examples

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Remove equals signs from anomaly examples
old1 = '''    explanation += f"   Строка {idx+2}: {row['Товар']}, Кол-во={row['Количество']}\\n"'''
new1 = '''    explanation += f"Строка {idx+2}: {row['Товар']}, количество {row['Количество']}\\n"'''

old2 = '''    explanation += f"   Строка {idx+2}: {row['Товар']}, пусто в '{col}'\\n"'''
new2 = '''    explanation += f"Строка {idx+2}: {row['Товар']}, пустое поле {col}\\n"'''

# Fix comment
old3 = '''# КРИТИЧНО: ВСЕГДА показывай КОНКРЕТНЫЕ примеры с номерами строк!'''
new3 = '''# КРИТИЧНО: Каждая запись на ОДНОЙ строке! БЕЗ знаков равно!'''

content = content.replace(old1, new1)
content = content.replace(old2, new2)
content = content.replace(old3, new3)

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed prompt examples')
