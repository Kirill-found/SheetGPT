# -*- coding: utf-8 -*-
"""Integrate aggregation pre-calculation into analyze method"""

file_path = "app/services/clean_analyst.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already integrated
if "PRE_CALCULATED_RESULT" in content:
    print("Already integrated!")
    exit(0)

# Find and replace the user_prompt section to add pre-calculation
old_code = '''        # Формируем запрос
        user_prompt = f"""{context_text}{history_text}
{data_text}
{reference_text}

ВОПРОС: {query}

Проанализируй данные и ответь в JSON формате. Покажи рассуждения, методологию и примеры расчётов."""'''

new_code = '''        # v12.0: Pre-calculate aggregations in pandas (GPT is bad at math!)
        pre_calc_text = ""
        python_executed = False

        aggregation_type = self._detect_aggregation_query(query)
        if aggregation_type:
            logger.info(f"[CleanAnalyst] Detected aggregation query: {aggregation_type}")
            agg_result = self._calculate_aggregation(df, column_names, query)
            if agg_result:
                python_executed = True
                # Format pre-calculated results for GPT
                groups_text = "\\n".join([
                    f"  - {g['name']}: {g['formatted']} руб"
                    for g in agg_result['groups']
                ])
                pre_calc_text = f"""

=== PRE_CALCULATED_RESULT (pandas, ТОЧНЫЕ ЧИСЛА!) ===
Группировка по: {agg_result['group_column']}
Суммирование: {agg_result['sum_column']}{agg_result['filter']}
Количество строк: {agg_result['total_rows']}

РЕЗУЛЬТАТЫ (ИСПОЛЬЗУЙ ЭТИ ЧИСЛА!):
{groups_text}

ИТОГО: {agg_result['grand_total_formatted']} руб

ВАЖНО: Числа выше посчитаны Python/pandas - они ТОЧНЫЕ!
НЕ пересчитывай их, просто используй в ответе!
==============================================
"""
                logger.info(f"[CleanAnalyst] Pre-calculated: {len(agg_result['groups'])} groups, total: {agg_result['grand_total']}")

        # Формируем запрос
        user_prompt = f"""{context_text}{history_text}
{data_text}
{reference_text}
{pre_calc_text}

ВОПРОС: {query}

Проанализируй данные и ответь в JSON формате. Покажи рассуждения, методологию и примеры расчётов."""'''

if old_code in content:
    content = content.replace(old_code, new_code)

    # Also update python_executed in transform_to_frontend_format
    old_python = '"python_executed": False  # GPT сам всё считает'
    new_python = '"python_executed": gpt_response.get("_python_executed", False)'
    content = content.replace(old_python, new_python)

    # Add _python_executed to the result dict in analyze method
    old_return = '''            return {
                "success": True,
                "gpt_response": result,
                "processing_time": f"{elapsed:.2f}s"
            }'''
    new_return = '''            # Pass python_executed flag to frontend
            result["_python_executed"] = python_executed

            return {
                "success": True,
                "gpt_response": result,
                "processing_time": f"{elapsed:.2f}s"
            }'''
    content = content.replace(old_return, new_return)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Integrated aggregation pre-calculation")
else:
    print("ERROR: Pattern not found")
    # Debug
    if "# Формируем запрос" in content:
        print("Found comment")
    if 'ВОПРОС: {query}' in content:
        print("Found query placeholder")
