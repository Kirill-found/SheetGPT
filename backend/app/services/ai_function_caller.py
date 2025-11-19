"""
AI Function Caller для SheetGPT v7.5.0
Интеграция с GPT-4o через function calling + improvements:
- Query classifier для отправки только релевантных функций (75% tokens saved)
- Metrics logging для monitoring
- Improved error handling
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
                    column_names
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

            # Шаг 6: Если функция не выбрана - возвращаем текстовый ответ
            else:
                print(f"[FUNCTION_CALLER] No function matched for query: {query}")
                success = False

                # v7.5.0: Log metrics (no function match)
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.log_execution(
                    function_name="NO_MATCH",
                    success=False,
                    duration_ms=duration_ms,
                    query=query,
                    error="No function matched",
                    num_functions_sent=len(filtered_function_defs),
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
        column_names: List[str]
    ) -> Dict[str, Any]:
        """
        Выполнение function call (NO FALLBACK)
        """
        func_name = function_call.name
        params = json.loads(function_call.arguments)

        print(f"[FUNCTION_CALLER] Calling function: {func_name}")
        print(f"[FUNCTION_CALLER] Parameters: {params}")

        # Выполняем функцию из registry
        result = self.registry.execute(func_name, df, **params)

        if not result["success"]:
            print(f"[FUNCTION_CALLER] Function failed: {result['error']}")
            # NO FALLBACK - возвращаем ошибку
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
                "summary": f"Ошибка выполнения функции {func_name}",
                "methodology": f"Попытка вызова {func_name} с параметрами {params}",
                "key_findings": [],
                "professional_insights": "",
                "recommendations": ["Проверьте правильность названий колонок и параметров"],
                "warnings": [f"Ошибка: {result['error']}"],
                "structured_data": None,
                "highlight_rows": None,
                "highlight_color": None,
                "highlight_message": None,
            }

        # Форматируем ответ
        return self._format_response(result, func_name, params, query, df)

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

        elif func_name in ["filter_rows", "sort_data", "search_rows", "split_data", "remove_duplicates",
                           "fill_missing", "aggregate_by_group", "pivot_table", "top_n_per_group"]:
            # Результат - DataFrame (таблица)
            if isinstance(func_result, pd.DataFrame) and not func_result.empty:
                headers = func_result.columns.tolist()
                rows = func_result.head(100).values.tolist()

                response["structured_data"] = {
                    "headers": headers,
                    "rows": rows,
                    "table_title": self._generate_table_title(func_name, params, len(func_result)),
                    "chart_recommended": None,
                    "operation_type": "function_result"
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
1. Названия колонок могут быть НЕТОЧНЫМИ - система найдет похожую колонку
2. Для выделения строк ВСЕГДА используй highlight_rows (работает с "выдели", "подсвети", "отметь")
3. Для фильтрации ВСЕГДА используй filter_rows (работает с "покажи где", "найди где")
4. Для сортировки ВСЕГДА используй sort_data
5. Для вычислений (сумма, среднее и т.д.) используй calculate_* функции
6. Для группировки используй aggregate_by_group или pivot_table

ПРИМЕРЫ ХОРОШИХ ВЫЗОВОВ:
- "выдели желтым где продажи < 100000" → highlight_rows(column="продажи", operator="<", value=100000, color="yellow")
- "выдели щетки где сумма меньше 100000" → highlight_rows(column="сумма", operator="<", value=100000)
  (система найдет "Заказали на сумму" или "Сумма продаж" автоматически)
- "подсвети строки где выручка больше миллиона" → highlight_rows(column="выручка", operator=">", value=1000000)
- "сумма продаж по менеджерам" → aggregate_by_group
- "отсортируй по дате" → sort_data
- "топ 5 по выручке" → sort_data или top_n_per_group
- "процент от общей суммы" → calculate_percentage

ВАЖНО: Если пользователь говорит "выдели СТРОКИ где [условие]" - это ВСЕГДА highlight_rows!
"""

        if custom_context:
            base_prompt += f"\n\nДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ:\n{custom_context}\n"

        return base_prompt
