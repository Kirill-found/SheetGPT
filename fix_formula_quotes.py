# Fix formula quotes and optionally translate to Russian function names
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add formula fixing after smart_result is returned
old_code = '''                # Handle chart_pending: call _finalize_chart_action to create actual chart_spec
                if smart_result.get("action_type") == "chart_pending":'''

new_code = '''                # Fix formula_template: replace single quotes with double quotes
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
                    formula = re.sub(r"([,;])\s*'([^']*)'", r'\\1"\\2"', formula)
                    smart_result["formula_template"] = formula
                    logger.info(f"[SmartGPT] Fixed formula quotes: {formula}")

                # Handle chart_pending: call _finalize_chart_action to create actual chart_spec
                if smart_result.get("action_type") == "chart_pending":'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added formula quote fixing')
else:
    print('ERROR: Pattern not found')
