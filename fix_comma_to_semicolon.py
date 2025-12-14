# Add comma to semicolon replacement for Russian locale
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''                    # Replace function names (case-insensitive, only before '(')
                    for eng, rus in func_translations.items():
                        pattern = rf'\\b{eng}\\s*\\('
                        formula = re.sub(pattern, f'{rus}(', formula, flags=re.IGNORECASE)

                    smart_result["formula_template"] = formula
                    logger.info(f"[SmartGPT] Fixed formula (Russian): {formula}")'''

new_code = '''                    # Replace function names (case-insensitive, only before '(')
                    for eng, rus in func_translations.items():
                        pattern = rf'\\b{eng}\\s*\\('
                        formula = re.sub(pattern, f'{rus}(', formula, flags=re.IGNORECASE)

                    # 3. Replace commas with semicolons (Russian locale uses ; as argument separator)
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

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added comma to semicolon replacement')
else:
    print('ERROR: Pattern not found')
