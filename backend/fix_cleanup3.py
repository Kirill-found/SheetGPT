# -*- coding: utf-8 -*-
# Add fix for СтрокаWord pattern

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_func = '''def clean_explanation_text(text: str) -> str:
    """Clean explanation text from weird formatting."""
    if not text:
        return text

    import re

    # Replace tabs
    text = text.replace('\\t', ' ')

    # Fix СтрокаN -> Строка N:
    text = re.sub(r'Строка(\\d+)', r'Строка \\1:', text)
    # Fix Строка N without colon
    text = re.sub(r'Строка (\\d+)(?!:)', r'Строка \\1:', text)
    # Fix double colons
    text = text.replace('::', ':')

    # Remove equals: Продукт='X' -> Продукт: X
    text = re.sub(r"(\\w+)='([^']+)'", r'\\1: \\2', text)
    text = re.sub(r'(\\w+)=([^,\\n\\s]+)', r'\\1: \\2', text)

    # Clean lines
    lines = text.split('\\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        while '  ' in line:
            line = line.replace('  ', ' ')
        cleaned.append(line)

    text = '\\n'.join(cleaned)
    while '\\n\\n\\n' in text:
        text = text.replace('\\n\\n\\n', '\\n\\n')

    return text.strip()'''

new_func = '''def clean_explanation_text(text: str) -> str:
    """Clean explanation text from weird formatting."""
    if not text:
        return text

    import re

    # Replace tabs
    text = text.replace('\\t', ' ')

    # Fix СтрокаN -> Строка N:
    text = re.sub(r'Строка(\\d+)', r'Строка \\1:', text)
    # Fix Строка N without colon
    text = re.sub(r'Строка (\\d+)(?!:)', r'Строка \\1:', text)
    # Fix double colons
    text = text.replace('::', ':')

    # Fix СтрокаWord (wrong format) -> just Word
    # Pattern: Строка followed by Cyrillic word (not number) = AI mistake
    text = re.sub(r'Строка([А-Яа-яЁё][А-Яа-яЁёA-Za-z0-9_]*)', r'\\1', text)

    # Remove equals: Продукт='X' -> Продукт: X
    text = re.sub(r"(\\w+)='([^']+)'", r'\\1: \\2', text)
    text = re.sub(r'(\\w+)=([^,\\n\\s]+)', r'\\1: \\2', text)

    # Clean lines
    lines = text.split('\\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        while '  ' in line:
            line = line.replace('  ', ' ')
        cleaned.append(line)

    text = '\\n'.join(cleaned)
    while '\\n\\n\\n' in text:
        text = text.replace('\\n\\n\\n', '\\n\\n')

    return text.strip()'''

content = content.replace(old_func, new_func)

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Added fix for СтрокаWord pattern')
