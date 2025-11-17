"""
AI Function Caller для SheetGPT v7.0.0
Интеграция с GPT-4o через function calling
"""

import pandas as pd
import json
import os
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

from .function_registry import FunctionRegistry
from .ai_code_executor import AICodeExecutor


class AIFunctionCaller:
    """
    Интеграция с GPT-4o для function calling
    1. GPT-4o определяет функцию и параметры
    2. Выполняем проверенную функцию из registry
    3. Если функция не найдена - fallback на code generation
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.registry = FunctionRegistry()
        self.code_executor = AICodeExecutor()  # Fallback для сложных запросов
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
        Обработка запроса с function calling
        """

        # Шаг 1: Анализ DataFrame для контекста
        df_info = self._analyze_dataframe(df, column_names)

        # Шаг 2: Формируем промпт для GPT-4o
        system_prompt = self._build_system_prompt(df_info, custom_context)

        # Шаг 3: Вызываем GPT-4o с function calling
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                functions=self.registry.get_function_definitions(),
                function_call="auto",  # AI решает вызывать ли функцию
                temperature=0.1
            )

            message = response.choices[0].message

            # Шаг 4: Если AI выбрал функцию - выполняем
            if message.function_call:
                return await self._execute_function_call(
                    message.function_call,
                    df,
                    query,
                    sheet_data,
                    column_names
                )

            # Шаг 5: Если функция не выбрана - fallback на code generation
            else:
                print(f"[FUNCTION_CALLER] No function matched, falling back to code executor")
                return await self.code_executor.process_query(
                    query=query,
                    column_names=column_names,
                    sheet_data=sheet_data,
                    custom_context=custom_context
                )

        except Exception as e:
            print(f"[FUNCTION_CALLER] Error: {e}")
            # Fallback на code executor при ошибке
            return await self.code_executor.process_query(
                query=query,
                column_names=column_names,
                sheet_data=sheet_data,
                custom_context=custom_context
            )

    async def _execute_function_call(
        self,
        function_call,
        df: pd.DataFrame,
        query: str,
        sheet_data: List[List[Any]],
        column_names: List[str]
    ) -> Dict[str, Any]:
        """
        Выполнение function call
        """
        func_name = function_call.name
        params = json.loads(function_call.arguments)

        print(f"[FUNCTION_CALLER] Calling function: {func_name}")
        print(f"[FUNCTION_CALLER] Parameters: {params}")

        # Выполняем функцию из registry
        result = self.registry.execute(func_name, df, **params)

        if not result["success"]:
            print(f"[FUNCTION_CALLER] Function failed: {result['error']}")
            # Fallback на code executor
            return await self.code_executor.process_query(
                query=query,
                column_names=column_names,
                sheet_data=sheet_data
            )

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

        elif func_name in ["calculate_sum", "calculate_average", "calculate_median", "calculate_percentile"]:
            # Результат - одно число
            response["summary"] = f"Результат: {func_result:,.2f}"
            response["key_findings"] = [f"{func_name}: {func_result:,.2f}"]
            response["methodology"] = f"Вычисление {func_name} для колонки {params.get('column')}"

        elif func_name in ["calculate_percentage", "calculate_rank", "calculate_running_total"]:
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

Используй fallback на генерацию кода ТОЛЬКО если:
- Запрос очень сложный и не покрывается функциями
- Требуется специфическая логика которой нет в функциях

ИНФОРМАЦИЯ О ДАННЫХ:
{df_info}

ПРАВИЛА:
1. Внимательно читай названия колонок - используй ТОЧНЫЕ имена
2. Для выделения строк ВСЕГДА используй highlight_rows
3. Для фильтрации ВСЕГДА используй filter_rows
4. Для сортировки ВСЕГДА используй sort_data
5. Для вычислений (сумма, среднее и т.д.) используй calculate_* функции
6. Для группировки используй aggregate_by_group или pivot_table

ПРИМЕРЫ ХОРОШИХ ВЫЗОВОВ:
- "выдели желтым где продажи < 100000" → highlight_rows
- "сумма продаж по менеджерам" → aggregate_by_group
- "отсортируй по дате" → sort_data
- "топ 5 по выручке" → sort_data или top_n_per_group
- "процент от общей суммы" → calculate_percentage
"""

        if custom_context:
            base_prompt += f"\n\nДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ:\n{custom_context}\n"

        return base_prompt
