# Add programmatic chart override to SmartGPT
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """                elif is_search_query:
                    logger.warning(f"[SmartGPT] ⚠️ OVERRIDE: search/filter query detected, using Python for accuracy")
                    return None  # Python is more accurate for filtering large datasets

            # If GPT decided analysis is needed, return None to use Python code
            if result.get("action_type") == "analysis":"""

new = """                elif is_search_query:
                    logger.warning(f"[SmartGPT] ⚠️ OVERRIDE: search/filter query detected, using Python for accuracy")
                    return None  # Python is more accurate for filtering large datasets

            # v11.2: OVERRIDE - chart queries should use chart action, not analysis
            # SmartGPT often returns action_type: null/analysis for chart requests
            chart_keywords = ['диаграмм', 'график', 'chart', 'гистограмм', 'круговая', 'круговую', 'круговой', 'кругов', 'pie']
            query_lower = query.lower()
            is_chart_query = any(kw in query_lower for kw in chart_keywords)

            if is_chart_query and result.get("action_type") in [None, "analysis"]:
                logger.warning(f"[SmartGPT] ⚠️ OVERRIDE: chart query detected but action_type={result.get('action_type')}, forcing chart action")
                # Determine chart type from query
                chart_type = 'COLUMN'  # Default
                for type_keyword, type_value in self.CHART_TYPES.items():
                    if type_keyword in query_lower:
                        chart_type = type_value
                        break
                return {
                    "action_type": "chart_pending",
                    "chart_type": chart_type,
                    "query": query,
                    "column_names": column_names,
                    "df_len": len(df),
                    "needs_gpt_selection": True
                }

            # If GPT decided analysis is needed, return None to use Python code
            if result.get("action_type") == "analysis":"""

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added chart override')
else:
    print('ERROR: Pattern not found')
