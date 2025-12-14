# Pass the filtered row's original index to frontend
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Track the original row index when filtering
old_filter = '''                    if len(filtered_df) > 0:
                        df = filtered_df
                        logger.info(f"[SimpleGPT] Chart row filter applied: {filter_val}, {len(df)} rows")'''

new_filter = '''                    if len(filtered_df) > 0:
                        # Get the original row indices before replacing df
                        filtered_row_indices = filtered_df.index.tolist()
                        df = filtered_df
                        logger.info(f"[SimpleGPT] Chart row filter applied: {filter_val}, {len(df)} rows, indices: {filtered_row_indices}")'''

if old_filter in content:
    content = content.replace(old_filter, new_filter)
    print('SUCCESS: Added filtered_row_indices tracking')
else:
    print('ERROR: Filter pattern not found')

# 2. Pass start_row_index in chart_spec
old_spec = '''        chart_spec = {
            "chart_type": chart_type,
            "title": title,
            "x_column_index": x_idx,'''

new_spec = '''        # Determine start row for chart (use filtered row index if available)
        start_row_index = 0
        if 'filtered_row_indices' in locals() and filtered_row_indices:
            start_row_index = filtered_row_indices[0]  # Use first filtered row
            logger.info(f"[SimpleGPT] Chart will start from row index: {start_row_index}")

        chart_spec = {
            "chart_type": chart_type,
            "title": title,
            "x_column_index": x_idx,
            "start_row_index": start_row_index,'''

if old_spec in content:
    content = content.replace(old_spec, new_spec)
    print('SUCCESS: Added start_row_index to chart_spec')
else:
    print('ERROR: chart_spec pattern not found')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
