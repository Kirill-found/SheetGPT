# -*- coding: utf-8 -*-
# Fix clean_explanation_text to not add colons when line already has one

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """    # Remove equals: Продукт='X' -> Продукт: X
    text = re.sub(r"(\\w+)='([^']+)'", r'\\1: \\2', text)
    text = re.sub(r'(\\w+)=([^,\\n\\s]+)', r'\\1: \\2', text)"""

new = """    # Remove equals: Продукт='X' -> Продукт: X
    # But NOT if the line already has a colon (to avoid "Веб: камера: 426" issues)
    lines_fixed = []
    for line in text.split('\\n'):
        if ':' not in line:
            # Only replace = with : if no colon exists in the line
            line = re.sub(r"(\\w+)='([^']+)'", r'\\1: \\2', line)
            line = re.sub(r'(\\w+)=([^,\\n\\s]+)', r'\\1: \\2', line)
        lines_fixed.append(line)
    text = '\\n'.join(lines_fixed)"""

if old in content:
    content = content.replace(old, new)
    with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: Fixed clean_explanation_text')
else:
    print('NOT FOUND')
