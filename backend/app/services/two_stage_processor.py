"""
Two-Stage AI Processor v8.0.0

Двухэтапная архитектура для надежной обработки запросов:

ЭТАП 1 - Understanding (GPT-4o-mini, ~200 tokens):
  - GPT получает: запрос + данные таблицы (без функций!)
  - GPT отвечает: что хочет пользователь? какие колонки нужны?
  - Результат: структурированное понимание намерения

ЭТАП 2 - Function Selection (GPT-4o, ~300 tokens):
  - GPT получает: понимание намерения + релевантные функции (10-15 шт)
  - GPT выбирает: конкретную функцию с параметрами
  - Результат: function call

Преимущества:
  - На этапе 1 GPT фокусируется ТОЛЬКО на понимании
  - На этапе 2 GPT получает минимум функций (уже отфильтрованных)
  - Общий расход токенов: ~500 vs ~2000 при старой архитектуре
  - Точность: выше за счет фокусировки на одной задаче
"""

import json
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
import pandas as pd
import os


class TwoStageProcessor:
    """
    v8.0.0: Двухэтапный процессор запросов

    Этап 1: Понимание запроса (без функций)
    Этап 2: Выбор функции (с понятым контекстом)
    """

    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.understanding_model = "gpt-4o-mini"  # Быстрый и дешевый для понимания
        self.function_model = "gpt-4o"  # Точный для выбора функции

    async def stage1_understand(
        self,
        query: str,
        df: pd.DataFrame,
        column_names: List[str]
    ) -> Dict[str, Any]:
        """
        ЭТАП 1: Понимание запроса

        GPT анализирует запрос и таблицу, НЕ видя функции.
        Возвращает структурированное понимание.
        """
        # Формируем описание данных
        data_description = self._describe_data(df, column_names)

        system_prompt = """Ты анализатор запросов к таблицам. Твоя задача - ПОНЯТЬ что хочет пользователь.

ВАЖНО: Ты НЕ выполняешь запрос, ты только ПОНИМАЕШЬ его.

КРИТИЧЕСКИЕ ПРАВИЛА ОПРЕДЕЛЕНИЯ action_type:

1. HIGHLIGHT (выделение строк цветом):
   - Слова: "выдели", "подсвети", "отметь", "highlight", "mark"
   - action_type = "highlight", output_type = "highlight"
   - Пример: "выдели строки где статус Ожидает" → highlight

2. TOP_N (получить лучшие/худшие N записей):
   - Слова: "топ", "top", "лучшие", "худшие", "первые N", "последние N"
   - action_type = "top_n", limit = число
   - Пример: "топ 3 менеджера по сумме" → top_n с limit=3

3. AGGREGATE (группировка с агрегацией):
   - Слова: "у каждого", "для каждого", "по группам", "сгруппируй"
   - action_type = "aggregate", group_by = колонка
   - Пример: "сколько у каждого менеджера" → aggregate

4. SORT (сортировка):
   - Слова: "сортируй", "от большего к меньшему", "по возрастанию"
   - action_type = "sort"

5. FILTER (фильтрация без выделения):
   - Слова: "покажи где", "найди где", "только"
   - action_type = "filter"

Проанализируй запрос и верни JSON:
{
    "action_type": "highlight/top_n/aggregate/sort/filter/transform/calculate",
    "target_columns": ["список колонок из таблицы которые нужны"],
    "conditions": [{"column": "колонка", "operator": "=/>/<=/contains/etc", "value": "значение"}],
    "aggregation": "тип агрегации если нужна (sum/count/avg/min/max/none)",
    "group_by": "колонка для группировки или null",
    "sort_by": {"column": "колонка", "direction": "asc/desc"} или null,
    "limit": число или null,
    "output_type": "table/single_value/list/highlight",
    "confidence": 0.0-1.0,
    "reasoning": "краткое объяснение почему так понял"
}

Отвечай ТОЛЬКО валидным JSON без markdown."""

        user_message = f"""ЗАПРОС ПОЛЬЗОВАТЕЛЯ:
{query}

ДАННЫЕ ТАБЛИЦЫ:
{data_description}

Проанализируй запрос и верни JSON с пониманием намерения."""

        try:
            response = await self.client.chat.completions.create(
                model=self.understanding_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            understanding = json.loads(response.choices[0].message.content)
            print(f"[STAGE 1 v8.0.0] Understanding: {understanding.get('action_type')} | Columns: {understanding.get('target_columns')}")
            print(f"[STAGE 1 v8.0.0] Conditions: {understanding.get('conditions')}")
            print(f"[STAGE 1 v8.0.0] Reasoning: {understanding.get('reasoning')}")

            return understanding

        except Exception as e:
            print(f"[STAGE 1 v8.0.0] Error: {e}")
            # Fallback понимание
            return {
                "action_type": "unknown",
                "target_columns": column_names[:3],
                "conditions": [],
                "aggregation": "none",
                "group_by": None,
                "sort_by": None,
                "limit": None,
                "output_type": "table",
                "confidence": 0.3,
                "reasoning": f"Ошибка анализа: {str(e)}"
            }

    def _describe_data(self, df: pd.DataFrame, column_names: List[str]) -> str:
        """Формирует описание данных для GPT"""
        lines = []
        lines.append(f"Всего строк: {len(df)}")
        lines.append(f"Колонки ({len(column_names)}):")

        for col in column_names:
            if col in df.columns:
                dtype = str(df[col].dtype)
                non_null = df[col].notna().sum()

                # Примеры значений
                sample_values = df[col].dropna().head(3).tolist()
                sample_str = ", ".join([str(v)[:30] for v in sample_values])

                # Для числовых - диапазон
                if df[col].dtype in ['int64', 'float64']:
                    min_val = df[col].min()
                    max_val = df[col].max()
                    lines.append(f"  - {col} ({dtype}): {non_null} значений, от {min_val} до {max_val}")
                else:
                    # Для текстовых - уникальные значения
                    unique_count = df[col].nunique()
                    lines.append(f"  - {col} ({dtype}): {unique_count} уникальных. Примеры: {sample_str}")

        # Первые 3 строки как пример
        lines.append("\nПример данных (первые 3 строки):")
        for i, row in df.head(3).iterrows():
            row_str = " | ".join([f"{col}={str(row[col])[:20]}" for col in column_names[:5]])
            lines.append(f"  {row_str}")

        return "\n".join(lines)

    def select_functions_for_intent(
        self,
        understanding: Dict[str, Any],
        all_functions: List[Dict]
    ) -> List[Dict]:
        """
        Выбирает релевантные функции на основе понятого намерения
        """
        action_type = understanding.get("action_type", "unknown")
        aggregation = understanding.get("aggregation", "none")
        output_type = understanding.get("output_type", "table")

        # Маппинг action_type → функции
        function_map = {
            "filter": [
                "filter_rows", "filter_between", "filter_in_list", "filter_not_in_list",
                "filter_null", "filter_not_null", "filter_regex", "filter_outliers"
            ],
            "top_n": [
                "filter_top_n", "filter_bottom_n"  # ТОЛЬКО эти для топ N!
            ],
            "aggregate": [
                "aggregate_by_group", "pivot_table"  # Группировка
            ],
            "sort": [
                "sort_data", "calculate_rank"
            ],
            "transform": [
                "case_when", "if_then_else", "fill_missing", "coalesce",
                "create_bins", "calculate_percentage"
            ],
            "highlight": [
                "highlight_rows"  # ТОЛЬКО highlight_rows для выделения!
            ],
            "search": [
                "search_rows", "filter_rows", "filter_regex"
            ],
            "calculate": [
                "calculate_sum", "calculate_average", "calculate_count",
                "calculate_min", "calculate_max", "calculate_std",
                "calculate_percentage", "calculate_ratio"
            ]
        }

        # Получаем базовые функции для action_type
        relevant_names = set(function_map.get(action_type, []))

        # Добавляем функции для агрегации если нужна
        if aggregation != "none":
            relevant_names.update([
                "aggregate_by_group", "pivot_table",
                f"calculate_{aggregation}" if aggregation in ["sum", "count", "avg", "min", "max"] else None
            ])
            relevant_names.discard(None)

        # Добавляем group_by функции если есть группировка
        if understanding.get("group_by"):
            relevant_names.update(["aggregate_by_group", "pivot_table", "top_n_per_group"])

        # Добавляем sort функции если есть сортировка
        if understanding.get("sort_by"):
            relevant_names.update(["sort_data", "calculate_rank"])

        # Добавляем limit функции если есть лимит
        if understanding.get("limit"):
            relevant_names.update(["filter_top_n", "filter_bottom_n"])

        # Для highlight всегда добавляем highlight_rows
        if output_type == "highlight":
            relevant_names.add("highlight_rows")

        # Фильтруем функции
        filtered = [f for f in all_functions if f["name"] in relevant_names]

        # Если ничего не нашли - возвращаем базовый набор
        if not filtered:
            base_functions = ["filter_rows", "calculate_sum", "aggregate_by_group", "sort_data", "highlight_rows"]
            filtered = [f for f in all_functions if f["name"] in base_functions]

        print(f"[STAGE 2 PREP v8.0.0] Selected {len(filtered)} functions for action_type={action_type}")

        return filtered

    async def stage2_select_function(
        self,
        query: str,
        understanding: Dict[str, Any],
        df: pd.DataFrame,
        column_names: List[str],
        relevant_functions: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        ЭТАП 2: Выбор функции

        GPT получает понимание намерения + релевантные функции.
        Возвращает function call.
        """
        system_prompt = f"""Ты выбираешь функцию для обработки данных в таблице.

ПОНИМАНИЕ ЗАПРОСА (от предыдущего анализа):
- Тип действия: {understanding.get('action_type')}
- Нужные колонки: {understanding.get('target_columns')}
- Условия: {understanding.get('conditions')}
- Агрегация: {understanding.get('aggregation')}
- Группировка: {understanding.get('group_by')}
- Сортировка: {understanding.get('sort_by')}
- Лимит: {understanding.get('limit')}
- Тип вывода: {understanding.get('output_type')}

ДОСТУПНЫЕ КОЛОНКИ ТАБЛИЦЫ:
{', '.join(column_names)}

ПРАВИЛА:
1. Используй ТОЧНЫЕ имена колонок из списка выше
2. Если тип вывода "highlight" - используй highlight_rows
3. Если есть группировка - используй aggregate_by_group
4. Если есть сортировка - используй sort_data
5. Если нужен топ/лучшие - используй filter_top_n
6. Для условий используй filter_rows

Выбери ОДНУ функцию и заполни её параметры."""

        user_message = f"Запрос: {query}"

        try:
            response = await self.client.chat.completions.create(
                model=self.function_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                functions=relevant_functions,
                function_call="auto",
                temperature=0.1
            )

            message = response.choices[0].message

            if message.function_call:
                print(f"[STAGE 2 v8.0.0] Selected function: {message.function_call.name}")
                print(f"[STAGE 2 v8.0.0] Arguments: {message.function_call.arguments}")
                return {
                    "name": message.function_call.name,
                    "arguments": json.loads(message.function_call.arguments)
                }
            else:
                print(f"[STAGE 2 v8.0.0] No function selected, GPT response: {message.content}")
                return None

        except Exception as e:
            print(f"[STAGE 2 v8.0.0] Error: {e}")
            return None

    async def process(
        self,
        query: str,
        df: pd.DataFrame,
        column_names: List[str],
        all_functions: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Полный двухэтапный процесс

        Returns:
            {"name": "function_name", "arguments": {...}, "understanding": {...}}
            или None при ошибке
        """
        print(f"\n{'='*60}")
        print(f"[TWO-STAGE v8.0.0] Processing: {query[:50]}...")
        print(f"{'='*60}")

        # ЭТАП 1: Понимание
        understanding = await self.stage1_understand(query, df, column_names)

        if understanding.get("confidence", 0) < 0.3:
            print(f"[TWO-STAGE v8.0.0] Low confidence understanding, may need clarification")

        # Выбираем релевантные функции
        relevant_functions = self.select_functions_for_intent(understanding, all_functions)

        # ЭТАП 2: Выбор функции
        function_call = await self.stage2_select_function(
            query, understanding, df, column_names, relevant_functions
        )

        if function_call:
            function_call["understanding"] = understanding
            print(f"[TWO-STAGE v8.0.0] Success! Function: {function_call['name']}")
            return function_call
        else:
            print(f"[TWO-STAGE v8.0.0] Failed to select function")
            return None


# Пример использования
if __name__ == "__main__":
    import asyncio

    async def test():
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        processor = TwoStageProcessor(client)

        # Тестовые данные
        df = pd.DataFrame({
            "Менеджер": ["Иванов", "Петров", "Сидоров", "Иванов", "Петров"],
            "Сумма": [10000, 15000, 8000, 12000, 9000],
            "Статус": ["Оплачен", "Ожидает", "Оплачен", "Отменен", "Оплачен"]
        })

        test_queries = [
            "Покажи топ 3 менеджера по сумме",
            "Выдели строки где статус Ожидает",
            "Сколько у каждого менеджера оплаченных заказов"
        ]

        for query in test_queries:
            print(f"\n\n{'#'*60}")
            print(f"ТЕСТ: {query}")
            print(f"{'#'*60}")

            # Здесь нужны реальные function definitions
            result = await processor.stage1_understand(query, df, df.columns.tolist())
            print(f"\nРезультат понимания: {json.dumps(result, ensure_ascii=False, indent=2)}")

    asyncio.run(test())
