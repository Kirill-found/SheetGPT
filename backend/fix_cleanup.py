# -*- coding: utf-8 -*-
import re

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the function and replace it entirely
pattern = r'def clean_explanation_text\(text: str\) -> str:.*?return text\.strip\(\)'

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

# Use DOTALL to match across newlines
new_content = re.sub(pattern, new_func, content, flags=re.DOTALL)

if new_content != content:
    with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Updated clean_explanation_text')
else:
    print('Pattern not found')
