# -*- coding: utf-8 -*-
# Add programmatic check for profitability queries - don't rely on GPT

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add check right after the CSV split detection in _gpt_smart_action
old = """        # v11.4: CSV split detection - check BEFORE GPT call
        # "разбей данные по ячейкам" should split in current sheet, not create new
        csv_split_result = self._detect_csv_split_action(query, column_names, df)
        if csv_split_result:
            logger.info(f"[SmartGPT] CSV split detected, returning direct action")
            csv_split_result['success'] = True
            csv_split_result['result_type'] = 'action'
            return csv_split_result

        # v11.1.3: Rewrite short follow-up queries to be explicit"""

new = """        # v11.4: CSV split detection - check BEFORE GPT call
        # "разбей данные по ячейкам" should split in current sheet, not create new
        csv_split_result = self._detect_csv_split_action(query, column_names, df)
        if csv_split_result:
            logger.info(f"[SmartGPT] CSV split detected, returning direct action")
            csv_split_result['success'] = True
            csv_split_result['result_type'] = 'action'
            return csv_split_result

        # v11.5: ANTI-HALLUCINATION - check for profitability queries WITHOUT cost data
        query_lower = query.lower()
        profitability_keywords = ['прибыл', 'прибыльн', 'выгодн', 'маржа', 'марж', 'рентабельн', 'наценк', 'себестоим']
        is_profitability_query = any(kw in query_lower for kw in profitability_keywords)

        if is_profitability_query:
            # Check if there's a cost/purchase price column
            cost_keywords = ['себестоим', 'закуп', 'cost', 'purchase', 'входн', 'оптов']
            has_cost_column = any(
                any(kw in col.lower() for kw in cost_keywords)
                for col in column_names
            )

            if not has_cost_column:
                logger.warning(f"[SmartGPT] Profitability query detected but NO COST COLUMN found!")
                return {
                    'action_type': 'chat',
                    'message': 'Для расчёта прибыльности/маржи нужны данные о себестоимости (закупочной цене). В таблице такой колонки нет. Могу показать товар с максимальной выручкой или средним чеком - это вам подойдёт?',
                    'success': True,
                    'result_type': 'chat'
                }
            else:
                logger.info(f"[SmartGPT] Profitability query - cost column found: {[c for c in column_names if any(kw in c.lower() for kw in cost_keywords)]}")

        # v11.1.3: Rewrite short follow-up queries to be explicit"""

if old in content:
    content = content.replace(old, new)
    with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: Added programmatic profitability check')
else:
    print('NOT FOUND')
