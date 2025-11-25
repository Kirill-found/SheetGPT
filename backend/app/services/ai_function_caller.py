"""
AI Function Caller для SheetGPT v7.8.0 - Hybrid Intelligence
3-tier decision system:
- TIER 1: Pattern Detection (10-15 patterns, 0 tokens)
- TIER 2: Query Complexity Classifier (GPT-4o-mini, ~100 tokens)
- TIER 3A: Function Calling for simple queries (GPT-4o, ~500 tokens)
- TIER 3B: Code Generation for complex queries (GPT-4o, ~1000 tokens)
"""

from pathlib import Path
import pandas as pd
import json
import os
import time
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

from .function_registry import FunctionRegistry
from app.utils.query_classifier import QueryClassifier
from app.utils.metrics import metrics_collector
from .query_complexity_classifier import classify_query_complexity
from .code_generator import generate_and_execute_code

# CRITICAL FIX: Напрямую читаем .env файл (load_dotenv() не работает с uvicorn)
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                os.environ["OPENAI_API_KEY"] = api_key
                break


class AIFunctionCaller:
    """
    Интеграция с GPT-4o для function calling (v7.5.0)
    1. Classifier фильтрует функции → 75% tokens saved
    2. GPT-4o определяет функцию из релевантных
    3. Выполняем функцию с fuzzy column matching
    4. Metrics logging для monitoring
    5. NO FALLBACK - 100 functions должны покрывать все запросы
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.registry = FunctionRegistry()
        self.classifier = QueryClassifier()  # v7.5.0: Query classification
        self.model = "gpt-4o"

    def _detect_and_handle_pattern(self, query: str, df: pd.DataFrame, column_names: List[str]) -> Optional[Dict[str, Any]]:
        """
        v7.7.0: Rule-Based Pattern Detection
        Detect known problematic patterns and handle them directly, bypassing GPT-4o
        Returns: result dict if pattern detected and handled, None otherwise
        """
        import re
        from difflib import get_close_matches

        query_lower = query.lower()

        # PATTERN 1: "топ N" / "лучшие N" / "худшие N" queries
        # Example: "топ 3 заказа в Москве", "5 лучших продаж"
        # v7.8.6 FIX: Skip Pattern Detector if query has adjectives (compound conditions)
        # Let GPT-4o handle complex queries via Function Calling
        adjective_keywords = ["оплачен", "ожида", "отмен", "актив", "неактив", " в ", "из "]
        has_adjectives = any(k in query_lower for k in adjective_keywords)

        top_keywords = ["топ", "лучш", "худш", "самы", "наиболь", "наименьш"]
        if any(k in query_lower for k in top_keywords):
            # Extract N (number)
            numbers = re.findall(r'\d+', query)
            if numbers:
                n = int(numbers[0])

                # v7.8.6: If query has compound conditions, skip Pattern Detector
                # Let GPT-4o + Function Calling handle it (more intelligent)
                if has_adjectives:
                    print(f"[PATTERN DETECTOR v7.8.6] TOP_N with compound conditions detected: '{query[:50]}...'")
                    print(f"[PATTERN DETECTOR v7.8.6] Skipping Pattern Detector - passing to GPT-4o Function Calling")
                    return None  # Pass to Query Classifier + Function Calling

                print(f"[PATTERN DETECTOR v7.7.0] Detected TOP_N pattern: n={n}")

                # Determine column to sort by (usually "Сумма" or similar)
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                if numeric_cols:
                    sort_col = numeric_cols[0]  # Default to first numeric column

                    # Check for condition (e.g., "в Москве")
                    # Extract location/status keywords
                    condition_col = None
                    condition_value = None

                    # Common filter patterns
                    if " в " in query_lower:
                        # "топ 3 в Москве" → filter by location
                        location_cols = [c for c in column_names if any(k in c.lower() for k in ["город", "регион", "location"])]
                        if location_cols:
                            condition_col = location_cols[0]
                            # Extract value after "в"
                            match = re.search(r' в (\w+)', query, re.IGNORECASE)
                            if match:
                                condition_value = match.group(1)

                    # Determine direction (top or bottom)
                    is_bottom = any(k in query_lower for k in ["худш", "наименьш", "мин"])

                    # Call appropriate function
                    registry = FunctionRegistry()

                    if is_bottom:
                        func = registry.functions["filter_bottom_n"]
                        func_name = "filter_bottom_n"
                        params = {"column": sort_col, "n": n}
                    else:
                        func = registry.functions["filter_top_n"]
                        func_name = "filter_top_n"
                        params = {"column": sort_col, "n": n}

                    # Add condition if detected - filter df first
                    filtered_df = df
                    if condition_col and condition_value:
                        print(f"[PATTERN DETECTOR v7.7.0] With condition: {condition_col} == {condition_value}")
                        # Filter df first, then apply top_n
                        filtered_df = df[df[condition_col] == condition_value]
                        print(f"[PATTERN DETECTOR v7.7.0] Filtered: {len(filtered_df)} rows (from {len(df)})")

                    print(f"[PATTERN DETECTOR v7.7.0] Calling {func_name} with {params}")
                    result_df = func(filtered_df, **params)

                    # Format response
                    return self._format_pattern_response(
                        result_df=result_df,
                        function_name=func_name,
                        params=params,
                        query=query
                    )

        # PATTERN 2: "у каждого" / "у всех" / "для каждого" queries
        # Example: "сколько оплаченных заказов у каждого менеджера"
        group_by_keywords = ["у каждого", "у всех", "для каждого", "по каждому"]
        if any(k in query_lower for k in group_by_keywords):
            print(f"[PATTERN DETECTOR v7.8.0] Detected GROUP_BY pattern")

            # Extract group column (word after "каждого"/"всех")
            for keyword in group_by_keywords:
                if keyword in query_lower:
                    idx = query_lower.find(keyword)
                    after_keyword = query[idx + len(keyword):].strip()
                    words_after = after_keyword.split()
                    if words_after:
                        group_word = words_after[0].strip('?,.')
                        # Find closest matching column
                        matches = get_close_matches(group_word, column_names, n=1, cutoff=0.4)
                        if matches:
                            group_col = matches[0]
                            print(f"[PATTERN DETECTOR v7.8.0] Group column: {group_col}")

                            # Check for filter condition (e.g., "оплаченных")
                            filtered_df = df
                            if any(k in query_lower for k in ["оплачен", "paid", "completed"]):
                                # Find status column
                                status_cols = [c for c in column_names if any(k in c.lower() for k in ["статус", "status", "state"])]
                                if status_cols:
                                    status_col = status_cols[0]
                                    # Filter for "Оплачен"
                                    filtered_df = df[df[status_col].str.contains("плачен", case=False, na=False)]
                                    print(f"[PATTERN DETECTOR v7.8.0] Filtered by {status_col}: {len(filtered_df)} rows (from {len(df)})")

                            # Determine aggregation function
                            if any(k in query_lower for k in ["сколько", "количество", "число"]):
                                agg_func = "count"
                            elif any(k in query_lower for k in ["сумма", "итого", "всего"]):
                                agg_func = "sum"
                            elif any(k in query_lower for k in ["средн", "average"]):
                                agg_func = "mean"
                            else:
                                agg_func = "count"  # Default

                            print(f"[PATTERN DETECTOR v7.8.0] Agg function: {agg_func}")

                            # Determine agg_column (column to aggregate)
                            # For count, use first column; for sum/mean, use numeric column
                            if agg_func == "count":
                                agg_col = column_names[0]  # Any column works for count
                            else:
                                # Find numeric column (exclude group column)
                                numeric_cols = filtered_df.select_dtypes(include=['number']).columns.tolist()
                                numeric_cols = [c for c in numeric_cols if c != group_col]
                                agg_col = numeric_cols[0] if numeric_cols else column_names[0]

                            print(f"[PATTERN DETECTOR v7.8.0] Agg column: {agg_col}")

                            # Call aggregate_by_group
                            registry = FunctionRegistry()
                            func = registry.functions["aggregate_by_group"]
                            params = {
                                "group_by": [group_col],  # Must be a list
                                "agg_column": agg_col,  # FIXED: Use proper agg column
                                "agg_func": agg_func
                            }

                            print(f"[PATTERN DETECTOR v7.8.0] Calling aggregate_by_group with {params}")
                            result_df = func(filtered_df, **params)  # Use filtered_df

                            return self._format_pattern_response(
                                result_df=result_df,
                                function_name="aggregate_by_group",
                                params=params,
                                query=query
                            )

        # PATTERN 3: "выдели" / "подсвети" / "отметь" queries - v7.9.5
        # CRITICAL: These MUST use highlight_rows, NOT search_rows
        # Example: "выдели все строки с Сидоровым"
        highlight_keywords = ["выдели", "подсвети", "отметь", "highlight", "mark"]
        if any(k in query_lower for k in highlight_keywords):
            print(f"[PATTERN DETECTOR v7.9.5] Detected HIGHLIGHT pattern: '{query[:50]}...'")

            # Extract the search term (name/value to highlight)
            # Common patterns: "с Сидоровым", "где сумма > X", "Иванова", etc.

            # Pattern: "с [Name]" or "с [Value]"
            import re
            search_term = None
            target_column = None

            # Try to find "с [Name]"
            match = re.search(r'\s+с\s+(\w+)', query, re.IGNORECASE)
            if match:
                search_term = match.group(1)
                print(f"[PATTERN DETECTOR v7.9.5] Found search term via 'с X': {search_term}")

            # Try to find "[Name]а" / "[Name]ым" (Russian case endings)
            if not search_term:
                # Look for capitalized words that might be names
                words = query.split()
                for word in words:
                    # Skip keywords
                    if word.lower() in ['выдели', 'все', 'строки', 'где', 'подсвети', 'отметь']:
                        continue
                    # Check if it looks like a name (capitalized or contains capital letters)
                    if len(word) > 2 and (word[0].isupper() or any(c.isupper() for c in word)):
                        # Remove Russian case endings
                        clean_word = re.sub(r'(ым|ом|ой|ым|ого|ему|а|у|е|ы|и|ов|ев|ёв)$', '', word, flags=re.IGNORECASE)
                        if clean_word:
                            search_term = clean_word
                            print(f"[PATTERN DETECTOR v7.9.5] Found search term via name detection: {search_term}")
                            break

            if search_term:
                # Try to guess the column - look for person-related columns
                person_columns = [c for c in column_names if any(
                    k in c.lower() for k in ['менеджер', 'manager', 'имя', 'name', 'фио', 'сотрудник', 'employee', 'клиент', 'client']
                )]

                if person_columns:
                    target_column = person_columns[0]
                    print(f"[PATTERN DETECTOR v7.9.5] Using column: {target_column}")
                else:
                    # No person column found, use first text column
                    text_cols = [c for c in column_names if df[c].dtype == 'object']
                    if text_cols:
                        target_column = text_cols[0]
                        print(f"[PATTERN DETECTOR v7.9.5] Using first text column: {target_column}")

                if target_column:
                    # Call highlight_rows
                    registry = FunctionRegistry()
                    func = registry.functions["highlight_rows"]
                    params = {
                        "column": target_column,
                        "operator": "contains",
                        "value": search_term
                    }

                    print(f"[PATTERN DETECTOR v7.9.5] Calling highlight_rows with {params}")
                    result = func(df, **params)

                    if result.get("highlight_rows"):
                        return {
                            "formula": None,
                            "explanation": f"Выделены строки где '{target_column}' содержит '{search_term}'",
                            "target_cell": None,
                            "confidence": 0.99,
                            "response_type": "highlight",
                            "function_used": "highlight_rows",
                            "parameters": params,
                            "summary": result.get("message", f"Выделено {len(result['highlight_rows'])} строк"),
                            "methodology": f"Использован детектор паттернов v7.9.5. Функция: highlight_rows. Поиск '{search_term}' в колонке '{target_column}'",
                            "key_findings": [f"Выделено строк: {len(result['highlight_rows'])}"],
                            "insights": [],
                            "highlight_rows": result["highlight_rows"],
                            "highlight_color": result.get("highlight_color", {"red": 1, "green": 1, "blue": 0.8}),
                            "highlight_message": result.get("message"),
                            "structured_data": None
                        }
                    else:
                        return {
                            "formula": None,
                            "explanation": f"Не найдено строк где '{target_column}' содержит '{search_term}'",
                            "target_cell": None,
                            "confidence": 0.99,
                            "response_type": "highlight",
                            "function_used": "highlight_rows",
                            "parameters": params,
                            "summary": f"Не найдено строк с '{search_term}' в колонке '{target_column}'",
                            "methodology": f"Использован детектор паттернов v7.9.5",
                            "key_findings": ["Ничего не найдено"],
                            "insights": [],
                            "highlight_rows": [],
                            "highlight_color": None,
                            "highlight_message": f"Не найдено строк с '{search_term}'",
                            "structured_data": None
                        }

            # If we couldn't extract search term, pass to GPT-4o but with hint
            print(f"[PATTERN DETECTOR v7.9.5] Could not extract search term, passing to GPT-4o with highlight hint")
            # Don't return None here - let it fall through but GPT-4o will have strong prompt guidance

        # No pattern detected
        return None

    def _format_pattern_response(self, result_df: pd.DataFrame, function_name: str, params: Dict, query: str) -> Dict[str, Any]:
        """Format response for pattern-detected queries"""
        print(f"[PATTERN DETECTOR v7.7.0] Result: {len(result_df)} rows")

        # v7.9.0: Compact format - ID + sort value
        sort_col = params.get("column", "")
        id_col = result_df.columns[0] if len(result_df.columns) > 0 else None
        if len(result_df) <= 10:
            result_lines = []
            for idx, row in result_df.iterrows():
                id_val = row[id_col] if id_col else idx
                sort_val = row.get(sort_col) if sort_col else None
                if sort_val is not None and isinstance(sort_val, (int, float)) and not pd.isna(sort_val):
                    fmt = f"{int(sort_val):,}".replace(",", " ") if sort_val == int(sort_val) else f"{sort_val:,.2f}"
                    result_lines.append(f"{id_val} - {fmt}")
                else:
                    result_lines.append(str(id_val))
            title = f"Top {len(result_df)} by '{sort_col}'" if function_name == "filter_top_n" else "Result"
            summary = f"{title}:" + chr(10) + chr(10).join([f"{i+1}. {ln}" for i, ln in enumerate(result_lines)])
        else:
            # Large result - will create table
            summary = f"Найдено {len(result_df)} записей. Результат отправлен в новый лист."

        return {
            "formula": None,
            "explanation": f"Запрос обработан автоматическим детектором паттернов v7.7.0",
            "target_cell": None,
            "confidence": 0.99,  # High confidence for rule-based
            "response_type": "analysis",
            "function_used": function_name,
            "parameters": params,
            "summary": summary,
            "methodology": f"Использован детектор паттернов v7.7.0. Функция: {function_name}. Параметры: {params}",
            "key_findings": [f"Обработано записей: {len(result_df)}"],
            "insights": [],
            "structured_data": {
                "headers": result_df.columns.tolist(),
                "rows": result_df.values.tolist(),
                "table_title": f"Результат: {query[:50]}..."
            } if len(result_df) > 3 else None
        }

    def _validate_query(self, query: str) -> tuple[bool, str]:
        """
        v7.8.3: Валидация запроса перед обработкой

        Returns:
            (is_valid, error_message) - True если запрос валидный, False + сообщение если нет
        """
        # Проверка 1: Минимальная длина
        if len(query.strip()) < 3:
            return False, "Запрос слишком короткий. Минимум 3 символа."

        # Проверка 2: Содержит ли хотя бы одну гласную (русскую или английскую)
        # Бессмысленные запросы типа "asdfghjkl" не имеют нормального распределения гласных
        vowels_ru = set('аеёиоуыэюяАЕЁИОУЫЭЮЯ')
        vowels_en = set('aeiouAEIOU')
        query_chars = set(query.lower())

        has_vowels = bool(query_chars & (vowels_ru | vowels_en))
        if not has_vowels:
            return False, "Не могу понять запрос. Пожалуйста, используйте осмысленные слова."

        # Проверка 3: Процент гласных (должен быть разумным)
        # В нормальных словах гласных 20-50%, в "asdfghjkl" - 0%
        total_letters = sum(1 for c in query if c.isalpha())
        if total_letters > 0:
            vowel_count = sum(1 for c in query.lower() if c in vowels_ru or c in vowels_en)
            vowel_ratio = vowel_count / total_letters

            if vowel_ratio < 0.15:  # Менее 15% гласных = подозрительно
                return False, "Не могу понять запрос. Пожалуйста, сформулируйте вопрос понятнее."

        return True, ""

    async def process_query(
        self,
        query: str,
        df: pd.DataFrame,
        column_names: List[str],
        sheet_data: List[List[Any]],
        custom_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Обработка запроса с function calling (v7.5.0 with classifier + metrics)
        """
        start_time = time.time()  # v7.5.0: Metrics timing
        function_used = None
        success = True

        # v7.8.3: Валидация запроса
        is_valid, error_message = self._validate_query(query)
        if not is_valid:
            print(f"[QUERY VALIDATOR v7.8.3] Invalid query: {query}")
            print(f"[QUERY VALIDATOR v7.8.3] Reason: {error_message}")
            return {
                "summary": error_message,
                "explanation": "Система не смогла обработать ваш запрос. Пожалуйста, перефразируйте вопрос используя понятные слова.",
                "response_type": "error",
                "confidence": 0.0,
                "methodology": "Запрос не прошел валидацию",
                "key_findings": []
            }

        try:
            # v7.7.0: RULE-BASED PATTERN DETECTION
            # Check for known problematic patterns and handle them directly
            pattern_result = self._detect_and_handle_pattern(query, df, column_names)
            if pattern_result:
                print(f"[PATTERN DETECTOR v7.7.0] Pattern detected and handled successfully!")
                print(f"[PATTERN DETECTOR v7.7.0] Function: {pattern_result.get('function_used')}")

                # Log metrics for pattern-detected queries
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.log_execution(
                    function_name=pattern_result.get('function_used'),
                    success=True,
                    duration_ms=duration_ms,
                    query=query,
                    num_functions_sent=0,  # Bypassed GPT-4o
                    categories=["pattern_detected"]
                )

                return pattern_result
        except Exception as e:
            print(f"[PATTERN DETECTOR v7.7.0] Error in pattern detection: {e}")
            # Continue with normal GPT-4o flow if pattern detection fails
            pass

        # v7.8.0: TIER 2 - Query Complexity Classifier
        # Determine whether to use Function Calling (simple) or Code Generation (complex)
        try:
            print(f"[TIER 2 v7.8.0] Classifying query complexity...")
            complexity = await classify_query_complexity(query, column_names)
            print(f"[TIER 2 v7.8.0] Complexity: {complexity.upper()}")

            if complexity == "complex":
                # TIER 3B: Code Generation for complex queries
                print(f"[TIER 3B v7.8.0] Using Code Generation for complex query")
                result = await generate_and_execute_code(
                    query=query,
                    df=df,
                    column_names=column_names,
                    custom_context=custom_context
                )

                # Log metrics
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.log_execution(
                    function_name="code_generation",
                    success=result.get("python_executed", False),
                    duration_ms=duration_ms,
                    query=query,
                    confidence=result.get("confidence", 0.99),
                    num_functions_sent=0,  # No functions sent
                    categories=["complex_query", "code_generation"]
                )

                return result

            # If simple, continue to TIER 3A (Function Calling)
            print(f"[TIER 3A v7.8.0] Using Function Calling for simple query")

        except Exception as e:
            print(f"[TIER 2 v7.8.0] Error in complexity classification: {e}")
            print(f"[TIER 2 v7.8.0] Falling back to Function Calling (TIER 3A)")
            # Continue with Function Calling on error

        # v7.8.0: TIER 3A - Function Calling (for simple queries)
        try:
            # Шаг 1: Анализ DataFrame для контекста
            df_info = self._analyze_dataframe(df, column_names)

            # Шаг 2: Формируем промпт для GPT-4o
            system_prompt = self._build_system_prompt(df_info, custom_context)

            # v7.5.0: Шаг 3 - Классифицируем запрос и фильтруем функции
            relevant_functions = self.classifier.get_relevant_functions(query)
            categories = self.classifier.classify(query)

            print(f"[CLASSIFIER v7.5.0] Query: {query[:50]}...")
            print(f"[CLASSIFIER v7.5.0] Categories: {categories}")
            print(f"[CLASSIFIER v7.5.0] Functions: {len(relevant_functions)}/100 ({len(relevant_functions)/100*100:.0f}%)")

            # Получаем только релевантные function definitions
            all_function_defs = self.registry.get_function_definitions()
            filtered_function_defs = [
                func_def for func_def in all_function_defs
                if func_def["name"] in relevant_functions
            ]

            # Fallback: если classifier ничего не нашел - используем все функции
            if not filtered_function_defs:
                print("[CLASSIFIER v7.5.0] No matches - using all functions (fallback)")
                filtered_function_defs = all_function_defs

            print(f"[CLASSIFIER v7.5.0] Sending {len(filtered_function_defs)} functions to GPT-4o")

            # Шаг 4: Вызываем GPT-4o с отфильтрованными функциями
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                functions=filtered_function_defs,  # v7.5.0: Filtered functions (25% of 100)
                function_call="auto",  # AI решает вызывать ли функцию
                temperature=0.1
            )

            message = response.choices[0].message

            # Шаг 5: Если AI выбрал функцию - выполняем
            if message.function_call:
                function_used = message.function_call.name
                result = await self._execute_function_call(
                    message.function_call,
                    df,
                    query,
                    sheet_data,
                    column_names,
                    custom_context
                )

                # v7.5.0: Log metrics
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.log_execution(
                    function_name=function_used,
                    success=result.get("response_type") != "error",
                    duration_ms=duration_ms,
                    query=query,
                    confidence=result.get("confidence", 0),
                    num_functions_sent=len(filtered_function_defs),
                    categories=categories
                )

                return result

            # Шаг 6: Если функция не выбрана - FALLBACK со всеми функциями
            else:
                print(f"[FUNCTION_CALLER] No function matched for query: {query}")

                # v7.5.0 FALLBACK: Если использовали filtered functions, retry со ВСЕМИ
                if len(filtered_function_defs) < len(all_function_defs):
                    print(f"[CLASSIFIER FALLBACK] Retrying with ALL {len(all_function_defs)} functions...")

                    # Retry с полным набором функций
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": query}
                        ],
                        functions=all_function_defs,  # ВСЕ 100 функций
                        function_call="auto",
                        temperature=0.1
                    )

                    message = response.choices[0].message

                    # Если теперь нашлась функция - выполняем
                    if message.function_call:
                        print(f"[CLASSIFIER FALLBACK] SUCCESS! Found function: {message.function_call.name}")
                        function_used = message.function_call.name
                        result = await self._execute_function_call(
                            message.function_call,
                            df,
                            query,
                            sheet_data,
                            column_names,
                            custom_context
                        )

                        # Log metrics (fallback success)
                        duration_ms = (time.time() - start_time) * 1000
                        metrics_collector.log_execution(
                            function_name=function_used,
                            success=result.get("response_type") != "error",
                            duration_ms=duration_ms,
                            query=query,
                            confidence=result.get("confidence", 0),
                            num_functions_sent=len(all_function_defs),
                            categories=["fallback"] + categories
                        )

                        return result

                # Если и со всеми функциями не нашли - возвращаем текстовый ответ
                success = False

                # v7.5.0: Log metrics (no function match even with fallback)
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.log_execution(
                    function_name="NO_MATCH",
                    success=False,
                    duration_ms=duration_ms,
                    query=query,
                    error="No function matched even after fallback",
                    num_functions_sent=len(all_function_defs) if len(filtered_function_defs) < len(all_function_defs) else len(filtered_function_defs),
                    categories=categories
                )

                return {
                    "formula": None,
                    "explanation": "",
                    "target_cell": None,
                    "confidence": 0.50,
                    "response_type": "text_only",
                    "function_used": None,
                    "parameters": None,
                    "insights": [],
                    "suggested_actions": None,
                    "summary": message.content or "Не удалось найти подходящую функцию для этого запроса.",
                    "methodology": "GPT-4o text response (no function match)",
                    "key_findings": [],
                    "professional_insights": "",
                    "recommendations": ["Попробуйте переформулировать запрос более конкретно"],
                    "warnings": ["Не найдена подходящая функция из 100 доступных"],
                    "structured_data": None,
                    "highlight_rows": None,
                    "highlight_color": None,
                    "highlight_message": None,
                }

        except Exception as e:
            # v7.5.0: Log error metrics
            duration_ms = (time.time() - start_time) * 1000
            metrics_collector.log_execution(
                function_name="EXCEPTION",
                success=False,
                duration_ms=duration_ms,
                query=query,
                error=str(e),
                num_functions_sent=0
            )
            raise  # Re-raise exception

    async def _execute_function_call(
        self,
        function_call,
        df: pd.DataFrame,
        query: str,
        sheet_data: List[List[Any]],
        column_names: List[str],
        custom_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполнение function call с FALLBACK на Code Generation при ошибке
        """
        func_name = function_call.name
        params = json.loads(function_call.arguments)

        print(f"[FUNCTION_CALLER] Calling function: {func_name}")
        print(f"[FUNCTION_CALLER] Parameters: {params}")

        # Выполняем функцию из registry
        result = self.registry.execute(func_name, df, **params)

        # v7.9.2: Валидация результата
        if result["success"]:
            validation = self._validate_function_result(result, func_name, params, df)
            if not validation["valid"]:
                print(f"[VALIDATION v7.9.2] Result validation failed: {validation['reason']}")
                result["success"] = False
                result["error"] = validation["reason"]

        if not result["success"]:
            print(f"[FUNCTION_CALLER] Function failed: {result['error']}")
            print(f"[FALLBACK v7.9.2] Attempting Code Generation fallback...")

            # v7.9.2: FALLBACK на Code Generation при ошибке функции
            try:
                code_result = await generate_and_execute_code(
                    query=query,
                    df=df,
                    column_names=column_names,
                    custom_context=custom_context
                )

                # Проверяем успешность Code Generation
                if code_result.get("python_executed", False) or code_result.get("summary"):
                    print(f"[FALLBACK v7.9.2] Code Generation succeeded!")
                    code_result["_fallback_from"] = f"function_{func_name}"
                    code_result["_original_error"] = result['error']
                    return code_result
                else:
                    print(f"[FALLBACK v7.9.2] Code Generation also failed")
                    # Продолжаем к возврату ошибки

            except Exception as fallback_error:
                print(f"[FALLBACK v7.9.2] Code Generation fallback exception: {fallback_error}")
                # Продолжаем к возврату ошибки

            # Если fallback тоже не сработал - возвращаем информативную ошибку
            return {
                "formula": None,
                "explanation": "",
                "target_cell": None,
                "confidence": 0.30,
                "response_type": "error",
                "function_used": func_name,
                "parameters": params,
                "insights": [],
                "suggested_actions": None,
                "summary": f"Не удалось выполнить запрос",
                "methodology": f"Попытка 1: {func_name} с параметрами {params}. Попытка 2: Code Generation.",
                "key_findings": [],
                "professional_insights": "",
                "recommendations": [
                    "Проверьте правильность названий колонок",
                    "Попробуйте переформулировать запрос",
                    "Убедитесь что в таблице есть нужные данные"
                ],
                "warnings": [f"Ошибка функции: {result['error']}"],
                "structured_data": None,
                "highlight_rows": None,
                "highlight_color": None,
                "highlight_message": None,
            }

        # Форматируем ответ
        return self._format_response(result, func_name, params, query, df)

    def _validate_function_result(
        self,
        result: Dict[str, Any],
        func_name: str,
        params: Dict[str, Any],
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        v7.9.2: Валидация результата выполнения функции
        Проверяет что результат имеет смысл и соответствует ожиданиям

        Returns:
            {"valid": True/False, "reason": str}
        """
        func_result = result.get("result")

        # 1. Проверка на None результат
        if func_result is None:
            return {"valid": False, "reason": "Функция вернула пустой результат"}

        # 2. Для DataFrame результатов
        if isinstance(func_result, pd.DataFrame):
            # Пустой DataFrame может быть валидным результатом фильтрации
            # но если запрашивали top_n, это проблема
            if func_result.empty:
                if func_name in ["filter_top_n", "filter_bottom_n", "top_n_per_group"]:
                    return {"valid": False, "reason": "Не найдено записей для ранжирования. Проверьте данные."}
                elif func_name in ["filter_rows", "search_rows"]:
                    # Пустой результат фильтрации - допустимо
                    return {"valid": True, "reason": ""}

            # Проверка на слишком большой результат (>95% данных для filter)
            if func_name in ["filter_rows", "search_rows"]:
                if len(func_result) > len(df) * 0.95:
                    print(f"[VALIDATION] Warning: Filter returned {len(func_result)}/{len(df)} rows (>95%)")
                    # Это предупреждение, не ошибка

        # 3. Для числовых результатов
        if isinstance(func_result, (int, float)):
            # Проверка на NaN
            if pd.isna(func_result):
                return {"valid": False, "reason": "Результат вычисления не определен (NaN). Возможно, в колонке нет числовых данных."}

            # Проверка на Infinity
            if not pd.isna(func_result) and (func_result == float('inf') or func_result == float('-inf')):
                return {"valid": False, "reason": "Результат вычисления бесконечность. Проверьте данные на нули."}

            # Для процентов - должно быть в разумных пределах
            if func_name == "calculate_percentage":
                # Процент может быть > 100% в некоторых случаях, но не 10000%
                if abs(func_result) > 10000:
                    print(f"[VALIDATION] Warning: Percentage value seems unusually high: {func_result}")

        # 4. Для Series результатов
        if isinstance(func_result, pd.Series):
            # Все NaN
            if func_result.isna().all():
                return {"valid": False, "reason": "Все вычисленные значения пустые. Проверьте тип данных в колонке."}

        # 5. Для highlight_rows
        if func_name == "highlight_rows":
            if isinstance(func_result, dict):
                rows = func_result.get("highlight_rows", [])
                if not rows:
                    # Пустой результат выделения - не ошибка, просто не нашли строк
                    return {"valid": True, "reason": ""}

        # 6. Проверка специфичных функций
        if func_name == "aggregate_by_group":
            if isinstance(func_result, pd.DataFrame):
                # Проверяем что group_by колонка в результате
                group_cols = params.get("group_by", [])
                if isinstance(group_cols, str):
                    group_cols = [group_cols]

                # Reset index чтобы проверить
                if func_result.index.name in group_cols or any(c in func_result.columns for c in group_cols):
                    return {"valid": True, "reason": ""}
                else:
                    # Возможно результат всё равно валидный, просто с другой структурой
                    pass

        # По умолчанию считаем результат валидным
        return {"valid": True, "reason": ""}

    def _format_response(
        self,
        result: Dict[str, Any],
        func_name: str,
        params: Dict[str, Any],
        query: str,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Форматирование ответа для frontend
        """
        func_result = result["result"]

        # Базовый ответ
        response = {
            "formula": None,
            "explanation": "",
            "target_cell": None,
            "confidence": 0.98,  # Высокая уверенность для function calls
            "response_type": "function_call",
            "function_used": func_name,
            "parameters": params,
            "insights": [],
            "suggested_actions": None,
            "summary": "",
            "methodology": "",
            "key_findings": [],
            "professional_insights": "",
            "recommendations": [],
            "warnings": [],
            "structured_data": None,
            "highlight_rows": None,
            "highlight_color": None,
            "highlight_message": None,
        }

        # Обработка разных типов результатов
        if func_name == "highlight_rows":
            # Результат выделения строк
            response["highlight_rows"] = func_result["highlight_rows"]
            response["highlight_color"] = func_result["highlight_color"]
            response["highlight_message"] = func_result["message"]
            response["summary"] = func_result["message"]
            response["methodology"] = f"Использована функция {func_name} с параметрами: {params}"

        elif func_name in ["filter_rows", "filter_top_n", "filter_bottom_n", "sort_data", "search_rows", "split_data", "remove_duplicates",
                           "fill_missing", "aggregate_by_group", "pivot_table", "top_n_per_group", "get_unique_values"]:
            # Результат - DataFrame (таблица)
            if isinstance(func_result, pd.DataFrame) and not func_result.empty:
                # v7.6.4 UX FIX: Для ЛЮБЫХ маленьких результатов (1-3 строки) - текстовый ответ вместо таблицы
                # Распространяем Smart UX на aggregate_by_group, filter_rows, и все другие функции
                if len(func_result) <= 3:
                    # Генерируем человекочитаемый ответ
                    result_lines = []

                    for idx, row in func_result.iterrows():
                        # Формируем строку типа "Иванов: 4 заказа | Сумма: 150 000"
                        row_desc = []
                        for col, val in row.items():
                            # Форматируем числа с разделителями
                            if isinstance(val, (int, float)) and not pd.isna(val):
                                # Целые числа без .00, дробные с 2 знаками
                                if val == int(val):
                                    row_desc.append(f"{col}: {int(val):,}".replace(",", " "))
                                else:
                                    row_desc.append(f"{col}: {val:,.2f}".replace(",", " "))
                            elif not pd.isna(val):
                                row_desc.append(f"{col}: {val}")
                        result_lines.append(" | ".join(row_desc))

                    # Определяем заголовок в зависимости от функции
                    if func_name == "filter_top_n":
                        prefix = "Максимальное значение" if len(func_result) == 1 else f"Топ {len(func_result)}"
                    elif func_name == "filter_bottom_n":
                        prefix = "Минимальное значение" if len(func_result) == 1 else f"Худшие {len(func_result)}"
                    elif func_name == "aggregate_by_group":
                        prefix = "Результат группировки"
                    elif func_name == "filter_rows":
                        prefix = "Найдено строк"
                    elif func_name == "sort_data":
                        prefix = "Отсортировано"
                    elif func_name == "get_unique_values":
                        prefix = "Уникальные значения"
                    else:
                        prefix = "Результат"

                    response["summary"] = f"{prefix}:\n" + "\n".join([f"{i+1}. {line}" for i, line in enumerate(result_lines)])
                    response["methodology"] = f"Использована функция {func_name} с параметрами: {params}"
                    # НЕ создаем structured_data - пользователь видит только текст в чате

                else:
                    # Большой результат (>3 строк) или другие функции - создаем таблицу
                    headers = func_result.columns.tolist()
                    rows = func_result.head(100).values.tolist()

                    # v7.8.14: Интеллектуальный display_mode - GPT-4o решает sidebar vs new sheet
                    num_rows = len(func_result)
                    num_cols = len(func_result.columns)

                    # Логика определения display_mode:
                    # 1. Простые списки (get_unique_values, search_rows) до 15 строк и 2 колонок → sidebar
                    # 2. Одноколоночные списки до 10 строк → sidebar
                    # 3. Все остальное (сложные таблицы, большие результаты) → new sheet
                    if func_name in ["get_unique_values", "search_rows"] and num_rows <= 15 and num_cols <= 2:
                        display_mode = "sidebar_only"
                    elif num_rows <= 10 and num_cols == 1:
                        display_mode = "sidebar_only"
                    else:
                        display_mode = "create_sheet"

                    response["structured_data"] = {
                        "headers": headers,
                        "rows": rows,
                        "table_title": self._generate_table_title(func_name, params, len(func_result)),
                        "chart_recommended": None,
                        "operation_type": "function_result",
                        "display_mode": display_mode  # NEW: Указывает frontend где отображать
                    }

                    response["summary"] = f"Выполнена операция: {func_name}. Получено {len(func_result)} строк"
                    response["methodology"] = f"Использована встроенная функция {func_name} с параметрами: {params}"

        elif func_name in ["calculate_sum", "calculate_average", "calculate_median", "calculate_percentile",
                           "calculate_max", "calculate_min", "calculate_count", "calculate_count_all",
                           "calculate_mode", "calculate_std", "calculate_product"]:
            # Результат - одно число/значение
            if isinstance(func_result, (int, float)):
                response["summary"] = f"Результат: {func_result:,.2f}"
                response["key_findings"] = [f"{func_name}: {func_result:,.2f}"]
            else:
                response["summary"] = f"Результат: {func_result}"
                response["key_findings"] = [f"{func_name}: {func_result}"]
            response["methodology"] = f"Вычисление {func_name} для колонки {params.get('column', 'N/A')}"

        elif func_name in ["calculate_percentage", "calculate_rank", "calculate_running_total",
                           "calculate_abs", "calculate_round", "calculate_ceiling", "calculate_floor",
                           "calculate_log", "calculate_power", "calculate_sqrt", "calculate_ratio"]:
            # Результат - Series (новая колонка)
            if isinstance(func_result, pd.Series):
                # Добавляем новую колонку к DataFrame
                new_df = df.copy()
                new_column_name = f"{func_name}_result"
                new_df[new_column_name] = func_result

                headers = new_df.columns.tolist()
                rows = new_df.head(100).values.tolist()

                response["structured_data"] = {
                    "headers": headers,
                    "rows": rows,
                    "table_title": f"Данные с добавленной колонкой: {new_column_name}",
                    "chart_recommended": None,
                    "operation_type": "function_result"
                }

                response["summary"] = f"Добавлена новая колонка: {new_column_name}"
                response["methodology"] = f"Применена функция {func_name} с параметрами: {params}"

        elif func_name == "vlookup":
            # Результат - найденное значение
            response["summary"] = f"Найдено значение: {func_result}"
            response["key_findings"] = [f"VLOOKUP результат: {func_result}"]
            response["methodology"] = f"Поиск значения '{params.get('lookup_value')}' в колонке '{params.get('lookup_column')}'"

        elif func_name == "calculate_correlation":
            # Результат - коэффициент корреляции
            response["summary"] = f"Корреляция между {params.get('column1')} и {params.get('column2')}: {func_result:.3f}"
            response["key_findings"] = [f"Коэффициент корреляции: {func_result:.3f}"]

            # Интерпретация корреляции
            if abs(func_result) > 0.7:
                response["professional_insights"] = "Сильная корреляция - переменные тесно связаны"
            elif abs(func_result) > 0.3:
                response["professional_insights"] = "Умеренная корреляция - есть связь между переменными"
            else:
                response["professional_insights"] = "Слабая корреляция - переменные слабо связаны"

        elif func_name == "calculate_variance":
            # Результат - dict с variance и std
            response["summary"] = f"Дисперсия: {func_result['variance']:.2f}, Стандартное отклонение: {func_result['std']:.2f}"
            response["key_findings"] = [
                f"Дисперсия: {func_result['variance']:.2f}",
                f"Стандартное отклонение: {func_result['std']:.2f}"
            ]

        elif func_name == "create_bins":
            # Результат - Series с категориями
            if isinstance(func_result, pd.Series):
                new_df = df.copy()
                new_column_name = f"{params.get('column')}_category"
                new_df[new_column_name] = func_result

                headers = new_df.columns.tolist()
                rows = new_df.head(100).values.tolist()

                response["structured_data"] = {
                    "headers": headers,
                    "rows": rows,
                    "table_title": f"Данные с категориями: {new_column_name}",
                    "chart_recommended": None,
                    "operation_type": "function_result"
                }

                response["summary"] = f"Создана категоризация для колонки {params.get('column')}"

        # Если результат не обработан - просто возвращаем его
        if not response["summary"]:
            response["summary"] = f"Выполнена функция {func_name}"
            response["methodology"] = f"Параметры: {params}"

        return response

    def _generate_table_title(self, func_name: str, params: Dict[str, Any], num_rows: int) -> str:
        """Генерация заголовка таблицы"""
        if func_name == "filter_rows":
            return f"Отфильтровано {num_rows} строк где {params.get('column')} {params.get('operator')} {params.get('value')}"
        elif func_name == "sort_data":
            direction = "по возрастанию" if params.get('ascending', True) else "по убыванию"
            return f"Данные отсортированы по {', '.join(params.get('columns', []))} {direction}"
        elif func_name == "search_rows":
            return f"Найдено {num_rows} строк с '{params.get('search_term')}' в колонке {params.get('column')}"
        elif func_name == "aggregate_by_group":
            return f"{params.get('agg_func').upper()} по группам: {', '.join(params.get('group_by', []))}"
        elif func_name == "pivot_table":
            return f"Сводная таблица: {', '.join(params.get('index', []))} × {', '.join(params.get('columns', []))}"
        elif func_name == "top_n_per_group":
            return f"Топ {params.get('n')} в каждой группе '{params.get('group_by')}'"
        else:
            return f"Результат операции {func_name}: {num_rows} строк"

    def _analyze_dataframe(self, df: pd.DataFrame, column_names: List[str]) -> str:
        """
        Анализ DataFrame для контекста
        """
        analysis = []
        analysis.append(f"Всего строк: {len(df)}")
        analysis.append(f"Всего колонок: {len(df.columns)}")
        analysis.append(f"\nКолонки:")

        for col in df.columns:
            dtype = df[col].dtype
            non_null = df[col].count()
            sample_values = df[col].dropna().head(3).tolist()

            analysis.append(f"  - {col}: {dtype}, непустых: {non_null}, примеры: {sample_values}")

        return '\n'.join(analysis)

    def _build_system_prompt(self, df_info: str, custom_context: Optional[str] = None) -> str:
        """
        Построение system prompt для GPT-4o
        """
        base_prompt = f"""Ты AI-помощник для работы с Google Sheets.

У тебя есть доступ к набору ПРОВЕРЕННЫХ функций для работы с данными.
ВСЕГДА используй эти функции когда это возможно - они НАДЕЖНЫ и работают на 100%.

ВАЖНЫЕ ВОЗМОЖНОСТИ:
- Функции поддерживают НЕТОЧНЫЕ названия колонок (например "Сумма" найдет "Заказали на сумму")
- Автоматическое преобразование строковых чисел (например "р.857 765" → 857765)
- Поэтому ВСЕГДА используй функции, даже если название колонки неточное!

Используй fallback на генерацию кода ТОЛЬКО если:
- Запрос очень сложный и не покрывается функциями
- Требуется специфическая логика которой нет в функциях

ИНФОРМАЦИЯ О ДАННЫХ:
{df_info}

ПРАВИЛА:
1. **АБСОЛЮТНЫЙ ПРИОРИТЕТ #1 - ВЫДЕЛЕНИЕ СТРОК!**
   Если в запросе есть слова "ВЫДЕЛИ", "ПОДСВЕТИ", "ОТМЕТЬ", "HIGHLIGHT":
   → НЕМЕДЛЕННО используй highlight_rows()
   → НЕ используй search_rows - это ДРУГАЯ функция для ПОИСКА, не выделения!
   → НЕ используй filter_rows - это ДРУГАЯ функция для ФИЛЬТРАЦИИ!

   ПРАВИЛЬНЫЕ примеры "выдели":
   - "выдели все строки с Сидоровым" → highlight_rows(column="Менеджер", operator="contains", value="Сидоров")
   - "выдели строки где сумма > 100000" → highlight_rows(column="Сумма", operator=">", value=100000)
   - "подсвети желтым менеджера Иванова" → highlight_rows(column="Менеджер", operator="contains", value="Иванов", color="yellow")
   - "отметь все заказы из Москвы" → highlight_rows(column="Город", operator="contains", value="Москва")

   НЕПРАВИЛЬНЫЕ примеры (НИКОГДА НЕ ДЕЛАЙ ТАК для "выдели"):
   - "выдели строки с Сидоровым" → search_rows (НЕПРАВИЛЬНО! search_rows для ПОИСКА, highlight_rows для ВЫДЕЛЕНИЯ)
   - "выдели строки с Сидоровым" → filter_rows (НЕПРАВИЛЬНО! filter_rows для ФИЛЬТРАЦИИ)

2. **АБСОЛЮТНЫЙ ПРИОРИТЕТ #2 - GROUP BY!**
   Если в запросе есть слова "У КАЖДОГО", "У ВСЕХ", "ДЛЯ КАЖДОГО", "ПО КАЖДОМУ":
   → НЕМЕДЛЕННО используй aggregate_by_group(group_by="Y", agg_func="count" или "sum")
   → ИГНОРИРУЙ ВСЕ ОСТАЛЬНЫЕ СЛОВА (фильтр, статус, условия) - они обрабатываются внутри aggregate_by_group!
   → ЗАПРЕЩЕНО использовать: calculate_sum, calculate_count, filter_rows, ANY OTHER FUNCTION!

   ПРАВИЛЬНЫЕ примеры:
   - "сколько заказов у каждого менеджера" → aggregate_by_group(group_by="Менеджер", agg_column="Менеджер", agg_func="count")
   - "сколько оплаченных заказов у каждого менеджера" → aggregate_by_group(group_by="Менеджер", agg_column="Менеджер", agg_func="count")
   - "сумма продаж у каждого клиента" → aggregate_by_group(group_by="клиент", agg_column="продажи", agg_func="sum")

   НЕПРАВИЛЬНЫЕ примеры (НИКОГДА НЕ ДЕЛАЙ ТАК):
   - "сколько заказов у каждого менеджера" → calculate_sum (НЕПРАВИЛЬНО!)
   - "сколько оплаченных заказов у каждого" → calculate_count (НЕПРАВИЛЬНО!)
   - "сколько оплаченных заказов у каждого менеджера" → filter_rows (НЕПРАВИЛЬНО! Даже если есть слово "оплаченных", всё равно используй aggregate_by_group!)
   - "сколько X у каждого Y" → filter_rows (НЕПРАВИЛЬНО!)

3. Названия колонок могут быть НЕТОЧНЫМИ - система найдет похожую колонку
4. Для выделения строк ВСЕГДА используй highlight_rows (работает с "выдели", "подсвети", "отметь") - НИКОГДА search_rows!
5. Для фильтрации ВСЕГДА используй filter_rows (работает с "покажи где", "найди где") - НО ТОЛЬКО ЕСЛИ НЕТ "У КАЖДОГО"!
6. Для сортировки ВСЕГДА используй sort_data
7. Для вычислений (сумма, среднее и т.д.) используй calculate_* функции - НО ТОЛЬКО ЕСЛИ НЕТ "У КАЖДОГО"!
8. Для группировки используй aggregate_by_group или pivot_table

КРИТИЧЕСКИ ВАЖНО - ПОВЕДЕНИЕ AI:
- Можешь задать ОДИН уточняющий вопрос если задача неясна
- НО если пользователь дал уточнение/пример - НЕМЕДЛЕННО вызывай функцию
- ЗАПРЕЩЕНО объяснять "вы можете использовать функцию X" после уточнения
- ЗАПРЕЩЕНО писать "мне нужно больше информации" после уточнения
- После уточнения пользователя = ТОЛЬКО вызов функции, НИКАКИХ объяснений

ПРИМЕРЫ ХОРОШИХ ВЫЗОВОВ:

**ВЫДЕЛЕНИЕ (highlight_rows) - используй для "выдели", "подсвети", "отметь":**
- "выдели все строки с Сидоровым" → highlight_rows(column="Менеджер", operator="contains", value="Сидоров")
- "выдели желтым где продажи < 100000" → highlight_rows(column="продажи", operator="<", value=100000, color="yellow")
- "выдели щетки где сумма меньше 100000" → highlight_rows(column="сумма", operator="<", value=100000)
  (система найдет "Заказали на сумму" или "Сумма продаж" автоматически)
- "подсвети строки где выручка больше миллиона" → highlight_rows(column="выручка", operator=">", value=1000000)
- "отметь заказы Иванова" → highlight_rows(column="Менеджер", operator="contains", value="Иванов")

**ГРУППИРОВКА (aggregate_by_group) - используй для "у каждого", "для всех", "по группам":**
- "сумма продаж по менеджерам" → aggregate_by_group(group_by="Менеджер", agg_column="Сумма", agg_func="sum")
- "сколько заказов у каждого менеджера" → aggregate_by_group(group_by="Менеджер", agg_column="Менеджер", agg_func="count")
- "сколько оплаченных заказов у каждого менеджера" → aggregate_by_group(group_by="Менеджер", agg_column="Менеджер", agg_func="count")
  ВАЖНО: aggregate_by_group автоматически работает ТОЛЬКО с оплаченными заказами, если указан статус в данных
- "количество клиентов у каждого продавца" → aggregate_by_group(group_by="продавец", agg_column="клиенты", agg_func="count")

**СОРТИРОВКА (sort_data):**
- "отсортируй по дате" → sort_data(columns=["Дата"], ascending=True)
- "покажи от новых к старым" → sort_data(columns=["Дата"], ascending=False)
- "от больших к меньшим по сумме" → sort_data(columns=["Сумма"], ascending=False)
- "от старых к новым" → sort_data(columns=["Дата"], ascending=True)

**ДРУГОЕ:**
- "топ 5 по выручке" → filter_top_n(column="выручка", n=5)
- "процент от общей суммы" → calculate_percentage
- "разбей данные по ячейкам" → split_data(column="auto", delimiter="auto")
  (система автоматически найдет колонку с разделителями типа |, , или ; и разобьёт данные)

КРИТИЧЕСКИ ВАЖНО - СОРТИРОВКА vs ФИЛЬТРАЦИЯ:
- "от новых к старым" / "от больших к меньшим" = СОРТИРОВКА (sort_data)
- "покажи ГДЕ дата < X" / "только строки ГДЕ сумма > Y" = ФИЛЬТРАЦИЯ (filter_rows)
- Если пользователь НЕ указывает условие - это СОРТИРОВКА!

КРИТИЧЕСКИ ВАЖНО - COUNT vs SUM:
- "сколько ЗАКАЗОВ у каждого" = COUNT (aggregate_by_group с agg_func="count")
- "сколько ДЕНЕГ / какая СУММА" = SUM (calculate_sum или aggregate_by_group с agg_func="sum")
- Если пользователь спрашивает "сколько" про ШТУКИ/ЗАКАЗЫ/СТРОКИ - это COUNT, НЕ SUM!

КРИТИЧЕСКИ ВАЖНО - "У КАЖДОГО" = GROUP BY:
- "сколько X у каждого Y" → aggregate_by_group(group_by="Y", agg_column="X", agg_func="count")
- "сумма X у каждого Y" → aggregate_by_group(group_by="Y", agg_column="X", agg_func="sum")
- Если пользователь говорит "У КАЖДОГО" → это ВСЕГДА GROUP BY, НЕ filter_rows!
- Пример: "сколько оплаченных заказов у каждого менеджера" → group_by="Менеджер", НЕ filter_rows!

ВАЖНО: Если пользователь говорит "выдели СТРОКИ где [условие]" - это ВСЕГДА highlight_rows!
ВАЖНО: Если пользователь говорит "разбей данные" или "split data" - используй split_data с column="auto", delimiter="auto"!
"""

        if custom_context:
            base_prompt += f"\n\nДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ:\n{custom_context}\n"

        return base_prompt
