# Add Russian function name translation to formulas
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''                # Fix formula_template: replace single quotes with double quotes
                # Google Sheets requires double quotes for text in formulas
                if smart_result.get("formula_template"):
                    formula = smart_result["formula_template"]
                    # Replace single quotes with double quotes (but not escaped ones)
                    # Pattern: ='text' -> ="text"
                    import re
                    # Replace single quotes around text values
                    formula = re.sub(r"='([^']*)'", r'="\\1"', formula)
                    formula = re.sub(r"= '([^']*)'", r'= "\\1"', formula)
                    # Also handle cases like ,'text' or ;'text'
                    formula = re.sub(r"([,;])\\s*'([^']*)'", r'\\1"\\2"', formula)
                    smart_result["formula_template"] = formula
                    logger.info(f"[SmartGPT] Fixed formula quotes: {formula}")'''

new_code = '''                # Fix formula_template: replace single quotes with double quotes
                # and translate English function names to Russian
                if smart_result.get("formula_template"):
                    formula = smart_result["formula_template"]
                    import re

                    # 1. Replace single quotes with double quotes
                    formula = re.sub(r"='([^']*)'", r'="\\1"', formula)
                    formula = re.sub(r"= '([^']*)'", r'= "\\1"', formula)
                    formula = re.sub(r"([,;(])\\s*'([^']*)'", r'\\1"\\2"', formula)

                    # 2. Translate English function names to Russian (for Russian locale)
                    func_translations = {
                        'IF': 'ЕСЛИ', 'SUM': 'СУММ', 'SUMIF': 'СУММЕСЛИ', 'SUMIFS': 'СУММЕСЛИМН',
                        'COUNTIF': 'СЧЁТЕСЛИ', 'COUNTIFS': 'СЧЁТЕСЛИМН', 'COUNT': 'СЧЁТ',
                        'COUNTA': 'СЧЁТЗ', 'COUNTBLANK': 'СЧИТАТЬПУСТОТЫ',
                        'VLOOKUP': 'ВПР', 'HLOOKUP': 'ГПР', 'INDEX': 'ИНДЕКС', 'MATCH': 'ПОИСКПОЗ',
                        'AVERAGE': 'СРЗНАЧ', 'AVERAGEIF': 'СРЗНАЧЕСЛИ', 'AVERAGEIFS': 'СРЗНАЧЕСЛИМН',
                        'MAX': 'МАКС', 'MIN': 'МИН', 'MAXIFS': 'МАКСЕСЛИ', 'MINIFS': 'МИНЕСЛИ',
                        'AND': 'И', 'OR': 'ИЛИ', 'NOT': 'НЕ', 'TRUE': 'ИСТИНА', 'FALSE': 'ЛОЖЬ',
                        'IFERROR': 'ЕСЛИОШИБКА', 'IFNA': 'ЕСНД', 'IFS': 'ЕСЛИМН',
                        'CONCATENATE': 'СЦЕПИТЬ', 'CONCAT': 'СЦЕП', 'TEXTJOIN': 'ОБЪЕДИНИТЬ',
                        'LEFT': 'ЛЕВСИМВ', 'RIGHT': 'ПРАВСИМВ', 'MID': 'ПСТР',
                        'LEN': 'ДЛСТР', 'TRIM': 'СЖПРОБЕЛЫ', 'CLEAN': 'ПЕЧСИМВ',
                        'UPPER': 'ПРОПИСН', 'LOWER': 'СТРОЧН', 'PROPER': 'ПРОПНАЧ',
                        'ROUND': 'ОКРУГЛ', 'ROUNDUP': 'ОКРУГЛВВЕРХ', 'ROUNDDOWN': 'ОКРУГЛВНИЗ',
                        'CEILING': 'ОКРВВЕРХ', 'FLOOR': 'ОКРВНИЗ', 'INT': 'ЦЕЛОЕ',
                        'ABS': 'ABS', 'SQRT': 'КОРЕНЬ', 'POWER': 'СТЕПЕНЬ', 'MOD': 'ОСТАТ',
                        'TODAY': 'СЕГОДНЯ', 'NOW': 'ТДАТА', 'DATE': 'ДАТА',
                        'YEAR': 'ГОД', 'MONTH': 'МЕСЯЦ', 'DAY': 'ДЕНЬ',
                        'WEEKDAY': 'ДЕНЬНЕД', 'WEEKNUM': 'НОМНЕДЕЛИ',
                        'HOUR': 'ЧАС', 'MINUTE': 'МИНУТЫ', 'SECOND': 'СЕКУНДЫ',
                        'TEXT': 'ТЕКСТ', 'VALUE': 'ЗНАЧЕН', 'NUMBERVALUE': 'ЧЗНАЧ',
                        'ISBLANK': 'ЕПУСТО', 'ISERROR': 'ЕОШИБКА', 'ISNA': 'ЕНД',
                        'ISNUMBER': 'ЕЧИСЛО', 'ISTEXT': 'ЕТЕКСТ', 'ISLOGICAL': 'ЕЛОГИЧ',
                        'ROW': 'СТРОКА', 'COLUMN': 'СТОЛБЕЦ', 'ROWS': 'ЧСТРОК', 'COLUMNS': 'ЧИСЛСТОЛБ',
                        'INDIRECT': 'ДВССЫЛ', 'ADDRESS': 'АДРЕС', 'OFFSET': 'СМЕЩ',
                        'LOOKUP': 'ПРОСМОТР', 'CHOOSE': 'ВЫБОР', 'SWITCH': 'ПЕРЕКЛЮЧ',
                        'FILTER': 'ФИЛЬТР', 'SORT': 'СОРТ', 'UNIQUE': 'УНИК',
                        'FIND': 'НАЙТИ', 'SEARCH': 'ПОИСК', 'REPLACE': 'ЗАМЕНИТЬ', 'SUBSTITUTE': 'ПОДСТАВИТЬ'
                    }

                    # Replace function names (case-insensitive, only before '(')
                    for eng, rus in func_translations.items():
                        pattern = rf'\\b{eng}\\s*\\('
                        formula = re.sub(pattern, f'{rus}(', formula, flags=re.IGNORECASE)

                    smart_result["formula_template"] = formula
                    logger.info(f"[SmartGPT] Fixed formula (Russian): {formula}")'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added Russian function translation')
else:
    print('ERROR: Pattern not found')
    # Try to find what's there
    idx = content.find('Fix formula_template')
    if idx >= 0:
        print(f'Found at {idx}')
        print(repr(content[idx:idx+500]))
