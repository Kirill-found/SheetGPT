# Fix: ALWAYS use chart_pending for chart queries to ensure proper row filtering
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''            # v11.2: OVERRIDE - chart queries should use chart action, not analysis
            # SmartGPT often returns action_type: null/analysis for chart requests
            chart_keywords = ['диаграмм', 'график', 'chart', 'гистограмм', 'круговая', 'круговую', 'круговой', 'кругов', 'pie']
            query_lower = query.lower()
            is_chart_query = any(kw in query_lower for kw in chart_keywords)

            if is_chart_query and result.get("action_type") in [None, "analysis"]:
                logger.warning(f"[SmartGPT] ⚠️ OVERRIDE: chart query detected but action_type={result.get('action_type')}, forcing chart action")'''

new_code = '''            # v11.3: OVERRIDE - ALWAYS use chart_pending for chart queries
            # This ensures _finalize_chart_action is called for proper row filtering and data transposition
            # SmartGPT's direct chart response doesn't support row_filter/aggregated_data
            chart_keywords = ['диаграмм', 'график', 'chart', 'гистограмм', 'круговая', 'круговую', 'круговой', 'кругов', 'pie']
            query_lower = query.lower()
            is_chart_query = any(kw in query_lower for kw in chart_keywords)

            if is_chart_query:
                logger.warning(f"[SmartGPT] ⚠️ OVERRIDE: chart query detected (action_type={result.get('action_type')}), forcing chart_pending for proper filtering")'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Chart override now ALWAYS uses chart_pending')
else:
    print('ERROR: Pattern not found')
