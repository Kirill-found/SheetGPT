# Force Python analysis for search/filter queries even in FULL mode
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """            # v11.1.1: OVERRIDE - in SAMPLE mode, highlight is FORBIDDEN
            # GPT sometimes ignores instructions, so we enforce programmatically
            if data_mode == "sample" and result.get("action_type") == "highlight":
                logger.warning(f"[SmartGPT] ⚠️ OVERRIDE: highlight forbidden in SAMPLE mode! Switching to Python analysis")
                return None  # Will trigger Python code analysis with ALL data"""

new = """            # v11.1.2: OVERRIDE - highlight for search/filter queries should ALWAYS use Python
            # GPT makes mistakes when visually parsing large tables for filtering
            if result.get("action_type") == "highlight":
                search_keywords = ['найди', 'найти', 'поиск', 'где', 'какие', 'какой', 'какая', 'который', 'которые']
                query_lower = query.lower()
                is_search_query = any(kw in query_lower for kw in search_keywords)

                if data_mode == "sample":
                    logger.warning(f"[SmartGPT] ⚠️ OVERRIDE: highlight forbidden in SAMPLE mode! Switching to Python analysis")
                    return None
                elif is_search_query:
                    logger.warning(f"[SmartGPT] ⚠️ OVERRIDE: search/filter query detected, using Python for accuracy")
                    return None  # Python is more accurate for filtering large datasets"""

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added search query override for Python analysis')
else:
    print('ERROR: Pattern not found')
