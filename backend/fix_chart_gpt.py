# -*- coding: utf-8 -*-
# Add GPT-powered chart column detection

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the _detect_chart_action method and replace it with GPT-powered version
old_method_start = '''    def _detect_chart_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой создания диаграммы.
        Анализирует данные и определяет лучшие колонки для осей.
        """
        query_lower = query.lower()

        # Check for chart keywords
        is_chart_query = any(kw in query_lower for kw in self.CHART_KEYWORDS)
        if not is_chart_query:
            return None

        logger.info(f"[SimpleGPT] Chart action detected: {query}")

        # Determine chart type
        chart_type = 'COLUMN'  # Default
        for type_keyword, type_value in self.CHART_TYPES.items():
            if type_keyword in query_lower:
                chart_type = type_value
                logger.info(f"[SimpleGPT] Chart type detected: {type_value}")
                break

        # Analyze columns to find best X and Y axes
        numeric_cols = []
        categorical_cols = []
        date_cols = []

        for idx, col in enumerate(column_names):
            if idx >= len(df.columns):
                continue
            col_data = df.iloc[:, idx]

            # Check if column is numeric
            try:
                numeric_data = pd.to_numeric(col_data, errors='coerce')
                non_null_ratio = numeric_data.notna().sum() / len(numeric_data) if len(numeric_data) > 0 else 0
                if non_null_ratio > 0.5:
                    numeric_cols.append({'name': col, 'index': idx})
                    continue
            except:
                pass

            # Check if column is date-like
            col_lower = col.lower()
            if any(d in col_lower for d in ['дата', 'date', 'месяц', 'month', 'год', 'year', 'день', 'day', 'период', 'time']):
                date_cols.append({'name': col, 'index': idx})
                continue

            # Otherwise it's categorical
            categorical_cols.append({'name': col, 'index': idx})

        logger.info(f"[SimpleGPT] Column analysis: numeric={[c['name'] for c in numeric_cols]}, "
                   f"categorical={[c['name'] for c in categorical_cols]}, date={[c['name'] for c in date_cols]}")

        # Find columns mentioned in query
        mentioned_cols = []
        for idx, col in enumerate(column_names):
            col_lower = col.lower()
            # Check if column name or any significant word from it is in query
            if col_lower in query_lower or col in query:
                mentioned_cols.append({'name': col, 'index': idx})
            else:
                # Check for partial match
                for word in col_lower.split():
                    if len(word) > 2 and word in query_lower:
                        mentioned_cols.append({'name': col, 'index': idx})
                        break

        logger.info(f"[SimpleGPT] Columns mentioned in query: {[c['name'] for c in mentioned_cols]}")

        # Determine X and Y axes
        x_column = None
        y_columns = []

        # Priority for X axis: mentioned categorical > date > first categorical
        # If user explicitly mentions a categorical column, use it
        for cat in categorical_cols:
            if cat in mentioned_cols:
                x_column = cat
                logger.info(f"[SimpleGPT] Using mentioned categorical column for X axis: {cat['name']}")
                break

        # If no mentioned categorical, use date column for time series
        if not x_column and date_cols:
            x_column = date_cols[0]
            logger.info(f"[SimpleGPT] Using date column for X axis: {x_column['name']}")

        # Fallback to first categorical
        if not x_column and categorical_cols:
            x_column = categorical_cols[0]
            logger.info(f"[SimpleGPT] Using first categorical column for X axis: {x_column['name']}")

        # Y axis: mentioned numeric columns, or all numeric if none mentioned
        for num in numeric_cols:
            if num in mentioned_cols:
                y_columns.append(num)

        if not y_columns and numeric_cols:
            # Take first 1-3 numeric columns
            y_columns = numeric_cols[:3]

        # For PIE charts, we need exactly one Y column and one X column
        if chart_type == 'PIE' and y_columns:
            y_columns = [y_columns[0]]

        # Generate title from query or columns
        title = ""
        if y_columns and x_column:
            y_names = ", ".join([c['name'] for c in y_columns])
            title = f"{y_names} по {x_column['name']}"
        elif y_columns:
            title = ", ".join([c['name'] for c in y_columns])

        # Build chart spec
        chart_spec = {
            "chart_type": chart_type,
            "title": title,
            "x_column_index": x_column['index'] if x_column else 0,
            "x_column_name": x_column['name'] if x_column else column_names[0],
            "y_column_indices": [c['index'] for c in y_columns] if y_columns else [1] if len(column_names) > 1 else [0],
            "y_column_names": [c['name'] for c in y_columns] if y_columns else [column_names[1] if len(column_names) > 1 else column_names[0]],
            "row_count": len(df),
            "col_count": len(column_names)
        }

        chart_type_names = {
            'LINE': 'линейный график',
            'BAR': 'горизонтальную гистограмму',
            'COLUMN': 'столбчатую диаграмму',
            'PIE': 'круговую диаграмму',
            'AREA': 'диаграмму с областями',
            'SCATTER': 'точечную диаграмму',
            'COMBO': 'комбинированный график'
        }

        message = f"Создаю {chart_type_names.get(chart_type, 'диаграмму')}: {title}"

        return {
            "action_type": "chart",
            "chart_spec": chart_spec,
            "message": message
        }'''

new_method = '''    async def _gpt_select_chart_columns(self, query: str, column_names: List[str], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Использует GPT для умного выбора колонок диаграммы на основе запроса пользователя.
        """
        # Analyze column types
        column_info = []
        for idx, col in enumerate(column_names):
            if idx >= len(df.columns):
                continue
            col_data = df.iloc[:, idx]

            # Determine type
            col_type = "text"
            try:
                numeric_data = pd.to_numeric(col_data, errors='coerce')
                non_null_ratio = numeric_data.notna().sum() / len(numeric_data) if len(numeric_data) > 0 else 0
                if non_null_ratio > 0.5:
                    col_type = "number"
            except:
                pass

            # Check for date
            col_lower = col.lower()
            if any(d in col_lower for d in ['дата', 'date', 'месяц', 'month', 'год', 'year']):
                col_type = "date"

            # Get sample values
            samples = col_data.dropna().head(3).tolist()
            column_info.append(f"{idx}. {col} ({col_type}): {samples}")

        columns_desc = "\\n".join(column_info)

        prompt = f"""Пользователь хочет создать диаграмму.
Запрос: "{query}"

Доступные колонки:
{columns_desc}

Выбери ТОЧНО те колонки, которые пользователь упомянул или имел в виду.

Ответь ТОЛЬКО в формате JSON:
{{"x_column": <индекс колонки для оси X (категории/даты)>, "y_columns": [<индексы колонок для оси Y (числовые значения)>], "title": "<заголовок диаграммы>"}}

Правила:
- X ось: категориальная или дата колонка (то, ПО ЧЕМУ группируем)
- Y ось: числовые колонки (то, ЧТО измеряем)
- Если пользователь написал "по категории и выручке" - X=категория, Y=выручка
- Если колонка не упомянута явно - НЕ добавляй её
- title должен отражать запрос пользователя"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()
            # Extract JSON from response
            import json
            if "```" in result_text:
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            result = json.loads(result_text)
            logger.info(f"[SimpleGPT] GPT chart selection: {result}")
            return result
        except Exception as e:
            logger.error(f"[SimpleGPT] GPT chart selection failed: {e}")
            return None

    def _detect_chart_action(self, query: str, column_names: List[str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Определяет, является ли запрос командой создания диаграммы.
        Использует GPT для умного выбора колонок.
        """
        query_lower = query.lower()

        # Check for chart keywords
        is_chart_query = any(kw in query_lower for kw in self.CHART_KEYWORDS)
        if not is_chart_query:
            return None

        logger.info(f"[SimpleGPT] Chart action detected: {query}")

        # Determine chart type
        chart_type = 'COLUMN'  # Default
        for type_keyword, type_value in self.CHART_TYPES.items():
            if type_keyword in query_lower:
                chart_type = type_value
                logger.info(f"[SimpleGPT] Chart type detected: {type_value}")
                break

        # Mark that we need GPT selection (will be done in async process method)
        return {
            "action_type": "chart_pending",
            "chart_type": chart_type,
            "query": query,
            "column_names": column_names,
            "df_len": len(df),
            "needs_gpt_selection": True
        }

    async def _finalize_chart_action(self, pending_action: Dict[str, Any], column_names: List[str], df: pd.DataFrame) -> Dict[str, Any]:
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
        }

        chart_type_names = {
            'LINE': 'линейный график',
            'BAR': 'горизонтальную гистограмму',
            'COLUMN': 'столбчатую диаграмму',
            'PIE': 'круговую диаграмму',
            'AREA': 'диаграмму с областями',
            'SCATTER': 'точечную диаграмму',
            'COMBO': 'комбинированный график'
        }

        message = f"Создаю {chart_type_names.get(chart_type, 'диаграмму')}: {title}"

        return {
            "action_type": "chart",
            "chart_spec": chart_spec,
            "message": message
        }'''

content = content.replace(old_method_start, new_method)

with open('C:/Projects/SheetGPT/backend/app/services/simple_gpt_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Added GPT-powered chart column detection')
