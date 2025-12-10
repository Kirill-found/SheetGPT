# -*- coding: utf-8 -*-
# Update chart action processing to use GPT finalization

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_chart_process = '''            # Check for chart action (needs df for column analysis)
            chart_action = self._detect_chart_action(query, column_names, df)
            if chart_action:
                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Chart action detected: {chart_action}")
                chart_result = {
                    "success": True,
                    "action_type": "chart",
                    "result_type": "action",
                    "chart_spec": chart_action["chart_spec"],
                    "summary": chart_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }
                logger.info(f"[SimpleGPT] Returning chart result with keys: {list(chart_result.keys())}")
                logger.info(f"[SimpleGPT] chart_result['chart_spec']: {chart_result.get('chart_spec')}")
                return chart_result'''

new_chart_process = '''            # Check for chart action (needs df for column analysis)
            chart_action = self._detect_chart_action(query, column_names, df)
            if chart_action:
                # If pending, finalize with GPT
                if chart_action.get("needs_gpt_selection"):
                    logger.info(f"[SimpleGPT] Chart action needs GPT selection")
                    chart_action = await self._finalize_chart_action(chart_action, column_names, df)

                elapsed = time.time() - start_time
                logger.info(f"[SimpleGPT] Chart action detected: {chart_action}")
                chart_result = {
                    "success": True,
                    "action_type": "chart",
                    "result_type": "action",
                    "chart_spec": chart_action["chart_spec"],
                    "summary": chart_action["message"],
                    "processing_time": f"{elapsed:.2f}s",
                    "processor": "SimpleGPT v1.0 (direct action)"
                }
                logger.info(f"[SimpleGPT] Returning chart result with keys: {list(chart_result.keys())}")
                logger.info(f"[SimpleGPT] chart_result['chart_spec']: {chart_result.get('chart_spec')}")
                return chart_result'''

content = content.replace(old_chart_process, new_chart_process)

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated chart action processing')
