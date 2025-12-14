# Add data transposition for single-row charts (e.g., "за декабрь по категориям")
file_path = 'C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and update the row filter section to add transposition logic
old_code = '''                    if len(filtered_df) > 0:
                        df = filtered_df
                        logger.info(f"[SimpleGPT] Chart row filter applied: {filter_val}, {len(df)} rows")
        else:'''

new_code = '''                    if len(filtered_df) > 0:
                        df = filtered_df
                        logger.info(f"[SimpleGPT] Chart row filter applied: {filter_val}, {len(df)} rows")

                        # If we filtered to a single row, transpose data for "по категориям" view
                        # This makes column names become X-axis labels
                        if len(df) == 1 and len(y_indices) > 1:
                            logger.info(f"[SimpleGPT] Single row detected, creating transposed chart data")
                            y_col_names = [column_names[i] for i in y_indices if i < len(column_names)]
                            row_data = df.iloc[0]

                            # Create transposed aggregated_data
                            rows = []
                            for i, y_idx in enumerate(y_indices):
                                if y_idx < len(df.columns):
                                    cat_name = column_names[y_idx]
                                    try:
                                        val = float(row_data.iloc[y_idx])
                                    except:
                                        val = 0
                                    rows.append([cat_name, val])

                            if rows:
                                aggregated_data = {
                                    "headers": ["Категория", "Значение"],
                                    "rows": rows,
                                    "aggregation_type": "single_row"
                                }
                                needs_aggregation = True  # Force use of aggregated data
                                logger.info(f"[SimpleGPT] Transposed data: {rows}")
        else:'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added single-row chart transposition')
else:
    print('ERROR: Pattern not found')
    # Debug
    idx = content.find('Chart row filter applied')
    if idx >= 0:
        print(f'Found log at index {idx}')
        print(repr(content[idx:idx+200]))
