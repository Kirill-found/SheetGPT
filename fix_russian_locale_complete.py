# Complete Russian locale syntax fixes
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''                    # 3. Replace commas with semicolons (Russian locale uses ; as argument separator)
                    # But only inside formulas, not inside quoted strings
                    # Simple approach: replace , with ; but preserve text in quotes
                    def replace_commas_outside_quotes(f):
                        result = []
                        in_quotes = False
                        for char in f:
                            if char == '"':
                                in_quotes = not in_quotes
                            if char == ',' and not in_quotes:
                                result.append(';')
                            else:
                                result.append(char)
                        return ''.join(result)

                    formula = replace_commas_outside_quotes(formula)

                    smart_result["formula_template"] = formula
                    logger.info(f"[SmartGPT] Fixed formula (Russian): {formula}")'''

new_code = '''                    # 3. Replace commas with semicolons (Russian locale uses ; as argument separator)
                    # But only inside formulas, not inside quoted strings
                    def replace_commas_outside_quotes(f):
                        result = []
                        in_quotes = False
                        for char in f:
                            if char == '"':
                                in_quotes = not in_quotes
                            if char == ',' and not in_quotes:
                                result.append(';')
                            else:
                                result.append(char)
                        return ''.join(result)

                    formula = replace_commas_outside_quotes(formula)

                    # 4. Replace decimal point with comma for numbers (e.g., 3.14 -> 3,14)
                    # But only for actual numbers, not cell references like A1.B1
                    # Pattern: digit.digit -> digit,digit
                    formula = re.sub(r'(\\d)\\.(\\d)', r'\\1,\\2', formula)

                    # 5. Replace TRUE/FALSE literals with ИСТИНА/ЛОЖЬ
                    # (when used as values, not as function calls - those are already handled)
                    formula = re.sub(r'\\bTRUE\\b(?!\\s*\\()', 'ИСТИНА', formula, flags=re.IGNORECASE)
                    formula = re.sub(r'\\bFALSE\\b(?!\\s*\\()', 'ЛОЖЬ', formula, flags=re.IGNORECASE)

                    smart_result["formula_template"] = formula
                    logger.info(f"[SmartGPT] Fixed formula (Russian): {formula}")'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added decimal and boolean fixes')
else:
    print('ERROR: Pattern not found')
