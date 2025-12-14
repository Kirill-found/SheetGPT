# Add more PIE chart keywords
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = "'кругов': 'PIE', 'pie': 'PIE', 'пирог': 'PIE', 'долей': 'PIE', 'процент': 'PIE', 'долями': 'PIE', 'доли': 'PIE',"

new = "'кругов': 'PIE', 'круговую': 'PIE', 'круговая': 'PIE', 'круговой': 'PIE', 'pie': 'PIE', 'пирог': 'PIE', 'долей': 'PIE', 'процент': 'PIE', 'долями': 'PIE', 'доли': 'PIE',"

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added PIE chart keywords')
else:
    print('ERROR: Pattern not found')
