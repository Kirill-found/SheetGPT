# Fix: Call _finalize_chart_action when chart_pending is returned
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''            smart_result = await self._gpt_smart_action(query, column_names, df, history=history)
            if smart_result:
                elapsed = time.time() - start_time
                logger.info(f"[SmartGPT] Action: {smart_result.get('action_type')}")

                # GPT возвращает готовый ответ - просто добавляем метаданные
                smart_result.update({'''

new_code = '''            smart_result = await self._gpt_smart_action(query, column_names, df, history=history)
            if smart_result:
                elapsed = time.time() - start_time
                logger.info(f"[SmartGPT] Action: {smart_result.get('action_type')}")

                # Handle chart_pending: call _finalize_chart_action to create actual chart_spec
                if smart_result.get("action_type") == "chart_pending":
                    logger.info(f"[SmartGPT] chart_pending detected, finalizing chart...")
                    try:
                        finalized = await self._finalize_chart_action(smart_result, column_names, df)
                        smart_result = finalized
                        logger.info(f"[SmartGPT] Chart finalized: {finalized.get('chart_spec', {}).get('title', 'N/A')}")
                    except Exception as e:
                        logger.error(f"[SmartGPT] Chart finalization failed: {e}")
                        # Fallback to simple chart
                        smart_result = {
                            "action_type": "chart",
                            "chart_spec": {
                                "chart_type": smart_result.get("chart_type", "COLUMN"),
                                "title": "Диаграмма",
                                "x_column_index": 0,
                                "y_column_indices": [1],
                                "row_count": len(df)
                            },
                            "message": "Создаю диаграмму"
                        }

                # GPT возвращает готовый ответ - просто добавляем метаданные
                smart_result.update({'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added _finalize_chart_action call')
else:
    print('ERROR: Pattern not found')
