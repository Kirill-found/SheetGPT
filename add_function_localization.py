import re

# Read the file
with open('backend/app/services/ai_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the location to insert (after line 124)
insertion_point = '''        # Удаляем множественные пробелы
        while "  " in formula:
            formula = formula.replace("  ", "")

        # ЛОКАЛИЗАЦИЯ: Заменяем запятые на точки с запятой для русской версии Google Sheets'''

localization_code = '''        # Удаляем множественные пробелы
        while "  " in formula:
            formula = formula.replace("  ", "")

        # ЛОКАЛИЗАЦИЯ ФУНКЦИЙ: Заменяем английские названия на русские
        # Это нужно делать ДО замены запятых на точки с запятой
        import re

        # Словарь английских → русских названий функций
        function_map = {
            'IF': 'ЕСЛИ',
            'ISBLANK': 'ЕПУСТО',
            'ISNUMBER': 'ЕЧИСЛО',
            'ISTEXT': 'ЕТЕКСТ',
            'ISERROR': 'ЕОШИБКА',
            'ISNA': 'ЕНД',
            'MATCH': 'ПОИСКПОЗ',
            'INDEX': 'ИНДЕКС',
            'VLOOKUP': 'ВПР',
            'HLOOKUP': 'ГПР',
            'COUNTIF': 'СЧЁТЕСЛИ',
            'COUNTIFS': 'СЧЁТЕСЛИМН',
            'SUMIF': 'СУММЕСЛИ',
            'SUMIFS': 'СУММЕСЛИМН',
            'AVERAGEIF': 'СРЗНАЧЕСЛИ',
            'AVERAGEIFS': 'СРЗНАЧЕСЛИМН',
            'FALSE': 'ЛОЖЬ',
            'TRUE': 'ИСТИНА',
            'AND': 'И',
            'OR': 'ИЛИ',
            'NOT': 'НЕ',
            'LEFT': 'ЛЕВСИМВ',
            'RIGHT': 'ПРАВСИМВ',
            'MID': 'ПСТР',
            'LEN': 'ДЛСТР',
            'TRIM': 'СЖПРОБЕЛЫ',
            'UPPER': 'ПРОПИСН',
            'LOWER': 'СТРОЧН',
            'CONCATENATE': 'СЦЕПИТЬ',
        }

        # Заменяем каждую функцию с использованием word boundaries
        for eng, rus in function_map.items():
            pattern = r'\\b{}(?=\\()'.format(eng)
            formula = re.sub(pattern, rus, formula, flags=re.IGNORECASE)

        # ЛОКАЛИЗАЦИЯ: Заменяем запятые на точки с запятой для русской версии Google Sheets'''

# Replace
if insertion_point in content:
    content = content.replace(insertion_point, localization_code)
    print('OK: Localization code added!')
else:
    print('ERROR: Insertion point not found')
    exit(1)

# Write back
with open('backend/app/services/ai_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('File updated successfully!')
