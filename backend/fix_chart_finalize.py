# -*- coding: utf-8 -*-
# Update _finalize_chart_action to handle aggregation

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_finalize = '''    async def _finalize_chart_action(self, pending_action: Dict[str, Any], column_names: List[str], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Завершает создание диаграммы с помощью GPT выбора колонок.
        """
        query = pending_action["query"]
        chart_type = pending_action["chart_type"]

        # Get GPT selection
        gpt_result = await self._gpt_select_chart_columns(query, column_names, df)

        if gpt_result:
            x_idx = gpt_result.get("x_column", 0)
            y_indices = gpt_result.get("y_columns", [1])
            title = gpt_result.get("title", "Диаграмма")
        else:
            # Fallback to simple logic
            x_idx = 0
            y_indices = [1] if len(column_names) > 1 else [0]
            title = "Диаграмма"

        # Validate indices
        x_idx = min(x_idx, len(column_names) - 1)
        y_indices = [min(i, len(column_names) - 1) for i in y_indices if i < len(column_names)]
        if not y_indices:
            y_indices = [1] if len(column_names) > 1 else [0]

        # For PIE charts, use only one Y column
        if chart_type == 'PIE':
            y_indices = y_indices[:1]

        chart_spec = {
            "chart_type": chart_type,
            "title": title,
            "x_column_index": x_idx,
            "x_column_name": column_names[x_idx] if x_idx < len(column_names) else column_names[0],
            "y_column_indices": y_indices,
            "y_column_names": [column_names[i] for i in y_indices if i < len(column_names)],
            "row_count": len(df),
            "col_count": len(column_names)
        }'''

new_finalize = '''    async def _finalize_chart_action(self, pending_action: Dict[str, Any], column_names: List[str], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Завершает создание диаграммы с помощью GPT выбора колонок.
        Поддерживает агрегацию данных для повторяющихся категорий.
        """
        query = pending_action["query"]
        chart_type = pending_action["chart_type"]

        # Get GPT selection
        gpt_result = await self._gpt_select_chart_columns(query, column_names, df)

        if gpt_result:
            x_idx = gpt_result.get("x_column", 0)
            y_indices = gpt_result.get("y_columns", [1])
            title = gpt_result.get("title", "Диаграмма")
            needs_aggregation = gpt_result.get("needs_aggregation", False)
            aggregation = gpt_result.get("aggregation", "sum")
        else:
            # Fallback to simple logic
            x_idx = 0
            y_indices = [1] if len(column_names) > 1 else [0]
            title = "Диаграмма"
            needs_aggregation = False
            aggregation = "sum"

        # Validate indices
        x_idx = min(x_idx, len(column_names) - 1)
        y_indices = [min(i, len(column_names) - 1) for i in y_indices if i < len(column_names)]
        if not y_indices:
            y_indices = [1] if len(column_names) > 1 else [0]

        # For PIE charts, use only one Y column
        if chart_type == 'PIE':
            y_indices = y_indices[:1]

        # Handle aggregation if needed
        aggregated_data = None
        if needs_aggregation and x_idx < len(df.columns):
            try:
                x_col_name = column_names[x_idx]
                y_col_names = [column_names[i] for i in y_indices if i < len(column_names)]

                # Create aggregation
                agg_df = df.copy()
                x_col = agg_df.iloc[:, x_idx]

                # Build aggregation dict
                agg_dict = {}
                for y_idx in y_indices:
                    if y_idx < len(df.columns):
                        y_col = df.columns[y_idx]
                        # Convert to numeric
                        agg_df[y_col] = pd.to_numeric(agg_df.iloc[:, y_idx], errors='coerce')
                        if aggregation == "mean":
                            agg_dict[y_col] = 'mean'
                        elif aggregation == "count":
                            agg_dict[y_col] = 'count'
                        else:
                            agg_dict[y_col] = 'sum'

                # Group and aggregate
                grouped = agg_df.groupby(agg_df.iloc[:, x_idx]).agg(agg_dict).reset_index()

                # Prepare data for frontend (list of lists with headers)
                headers = [x_col_name] + y_col_names
                rows = []
                for _, row in grouped.iterrows():
                    row_data = [row.iloc[0]]  # X value
                    for i, y_col in enumerate(y_col_names):
                        val = row.iloc[i + 1]
                        # Round numeric values
                        if pd.notna(val):
                            row_data.append(round(float(val), 2))
                        else:
                            row_data.append(0)
                    rows.append(row_data)

                aggregated_data = {
                    "headers": headers,
                    "rows": rows,
                    "aggregation_type": aggregation
                }

                logger.info(f"[SimpleGPT] Aggregated data: {len(rows)} groups from {len(df)} rows")

            except Exception as e:
                logger.error(f"[SimpleGPT] Aggregation failed: {e}")
                needs_aggregation = False

        chart_spec = {
            "chart_type": chart_type,
            "title": title,
            "x_column_index": x_idx,
            "x_column_name": column_names[x_idx] if x_idx < len(column_names) else column_names[0],
            "y_column_indices": y_indices,
            "y_column_names": [column_names[i] for i in y_indices if i < len(column_names)],
            "row_count": len(df),
            "col_count": len(column_names),
            "needs_aggregation": needs_aggregation,
            "aggregated_data": aggregated_data
        }'''

content = content.replace(old_finalize, new_finalize)

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated _finalize_chart_action with aggregation support')
