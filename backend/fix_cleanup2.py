# -*- coding: utf-8 -*-
# Simpler approach - just find the function start and end

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the function
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'def clean_explanation_text(text: str) -> str:' in line:
        start_idx = i
    if start_idx is not None and i > start_idx:
        # Find end - next function or class definition
        if line.startswith('def ') or line.startswith('class '):
            end_idx = i
            break

if start_idx is not None and end_idx is not None:
    # New function
    new_func_lines = [
        'def clean_explanation_text(text: str) -> str:\n',
        '    """Clean explanation text from weird formatting."""\n',
        '    if not text:\n',
        '        return text\n',
        '\n',
        '    import re\n',
        '\n',
        '    # Replace tabs\n',
        "    text = text.replace('\\t', ' ')\n",
        '\n',
        '    # Fix СтрокаN -> Строка N:\n',
        "    text = re.sub(r'Строка(\\d+)', r'Строка \\1:', text)\n",
        '    # Fix Строка N without colon\n',
        "    text = re.sub(r'Строка (\\d+)(?!:)', r'Строка \\1:', text)\n",
        '    # Fix double colons\n',
        "    text = text.replace('::', ':')\n",
        '\n',
        "    # Remove equals: Продукт='X' -> Продукт: X\n",
        '    text = re.sub(r"(\\w+)=\'([^\']+)\'", r\'\\1: \\2\', text)\n',
        "    text = re.sub(r'(\\w+)=([^,\\n\\s]+)', r'\\1: \\2', text)\n",
        '\n',
        '    # Clean lines\n',
        "    lines = text.split('\\n')\n",
        '    cleaned = []\n',
        '    for line in lines:\n',
        '        line = line.strip()\n',
        "        while '  ' in line:\n",
        "            line = line.replace('  ', ' ')\n",
        '        cleaned.append(line)\n',
        '\n',
        "    text = '\\n'.join(cleaned)\n",
        "    while '\\n\\n\\n' in text:\n",
        "        text = text.replace('\\n\\n\\n', '\\n\\n')\n",
        '\n',
        '    return text.strip()\n',
        '\n',
    ]

    # Replace
    new_lines = lines[:start_idx] + new_func_lines + lines[end_idx:]

    with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f'Updated function (lines {start_idx}-{end_idx})')
else:
    print(f'Function not found: start={start_idx}, end={end_idx}')
