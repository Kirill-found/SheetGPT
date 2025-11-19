"""
Query classifier для отправки только релевантных функций
Цель: Ускорить response time с 4.3s до <3s
"""

from typing import List, Dict
import re


class QueryClassifier:
    """
    Классифицирует запрос пользователя и возвращает релевантные категории функций

    Вместо отправки 100 функций → отправляем 10-30 релевантных
    """

    def __init__(self):
        # Паттерны для каждой категории (русские + английские)
        self.patterns = {
            "math": [
                r'\b(сумм|средн|медиан|процентил|дисперс|корреляц|взвешен)',
                r'\b(sum|average|avg|median|percentile|variance|correlation|weighted)',
                r'\b(итог|всего|общ)',
                r'\b(total)',
            ],
            "filter": [
                r'\b(фильтр|найд|покаж|где|только|выбер|отбор)',
                r'\b(filter|find|show|where|select)',
                r'\b(топ|лучш|худш|больш|меньш|равн)',
                r'\b(top|best|worst|bottom|greater|less|equal)',
                r'\b(уникальн|дубликат|пуст)',
                r'\b(unique|duplicate|empty)',
            ],
            "group": [
                r'\b(группиров|сгруппир|сводн|агрегац)',
                r'\b(group|pivot|aggregate)',
                r'\b(по.*менеджер|по.*продукт|по.*категор|по.*город)',
                r'\b(by\s+\w+)',
            ],
            "sort": [
                r'\b(сортир|ранжир|упорядоч)',
                r'\b(sort|rank|order)',
            ],
            "text": [
                r'\b(текст|строк|поиск|найд.*слов|содерж)',
                r'\b(text|string|search|find.*word|contains)',
                r'\b(конкатенац|объедин|разделит)',
                r'\b(concat|join|split)',
            ],
            "date": [
                r'\b(дат|день|месяц|год|период)',
                r'\b(date|day|month|year|period)',
                r'\b(январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)',
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)',
            ],
            "action": [
                r'\b(подсвет|выдел|создай|добав|удали|измени)',
                r'\b(highlight|create|add|delete|modify|update)',
                r'\b(график|диаграмм|chart)',
                r'\b(таблиц)',
                r'\b(table)',
            ],
            "insight": [
                r'\b(тренд|аномал|рекоменд|анализ|сравн)',
                r'\b(trend|anomaly|recommend|analyz|compare|insight)',
                r'\b(что.*измен|как.*развив|почему)',
                r'\b(what.*change|how.*evolv|why)',
            ],
        }

        # Дефолтные категории если ничего не подошло
        self.default_categories = ["math", "filter", "group"]

    def classify(self, query: str) -> List[str]:
        """
        Классифицирует запрос и возвращает список релевантных категорий

        Returns:
            ["math", "filter"] - только релевантные категории
        """
        if not query:
            return self.default_categories

        query_lower = query.lower()
        matched_categories = set()

        # Проверяем каждую категорию
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    matched_categories.add(category)
                    break  # Одно совпадение достаточно для категории

        # Если ничего не подошло - возвращаем default
        if not matched_categories:
            return self.default_categories

        return list(matched_categories)

    def get_category_functions(self, category: str) -> List[str]:
        """
        Возвращает список функций для данной категории
        """
        function_map = {
            "math": [
                "calculate_sum",
                "calculate_average",
                "calculate_median",
                "calculate_percentile",
                "calculate_std_dev",
                "calculate_variance",
                "calculate_correlation",
                "calculate_weighted_average",
            ],
            "filter": [
                "filter_rows",
                "filter_by_date",
                "filter_top_n",
                "filter_bottom_n",
                "filter_unique",
                "filter_duplicates",
                "filter_contains",
                "filter_not_contains",
                "filter_empty",
                "filter_not_empty",
                "filter_between",
                "filter_greater_than",
                "filter_less_than",
                "filter_equals",
                "filter_not_equals",
                "filter_starts_with",
                "filter_ends_with",
                "filter_by_multiple_conditions",
                "filter_by_month",
                "filter_by_year",
            ],
            "group": [
                "group_by_column",
                "group_by_multiple_columns",
                "create_pivot_table",
                "aggregate_sum",
                "aggregate_average",
                "aggregate_count",
                "aggregate_min",
                "aggregate_max",
                "aggregate_count_unique",
                "group_and_sort",
                "group_and_filter",
                "create_summary_table",
                "create_cross_tab",
                "calculate_running_total",
                "calculate_cumulative_percentage",
                "group_by_time_period",
                "group_by_date_range",
                "group_by_category",
                "group_by_numeric_range",
                "group_by_text_pattern",
                "aggregate_multiple_columns",
                "create_hierarchical_summary",
            ],
            "sort": [
                "sort_by_column",
                "sort_by_multiple_columns",
                "rank_values",
                "percentile_rank",
                "dense_rank",
                "row_number",
                "ntile",
                "sort_and_filter",
                "sort_by_custom_order",
                "sort_by_date",
                "sort_by_frequency",
                "rank_by_multiple_criteria",
                "sort_with_ties",
                "rank_dense",
                "partition_and_rank",
            ],
            "text": [
                "find_text",
                "find_with_regex",
                "concatenate_columns",
                "split_text",
                "extract_numbers",
                "extract_dates",
                "replace_text",
                "format_text",
                "text_to_uppercase",
                "text_to_lowercase",
            ],
            "date": [
                "format_date",
                "extract_year",
                "extract_month",
                "extract_day",
                "calculate_date_difference",
                "add_days",
                "subtract_days",
                "filter_by_date_range",
                "group_by_month",
                "group_by_quarter",
            ],
            "action": [
                "highlight_rows",
                "create_new_table",
                "create_chart",
                "add_column",
                "delete_column",
                "rename_column",
                "move_column",
                "insert_row",
                "delete_row",
                "update_cell_values",
            ],
            "insight": [
                "analyze_trends",
                "find_anomalies",
                "suggest_actions",
                "generate_summary",
                "compare_periods",
            ],
        }

        return function_map.get(category, [])

    def get_relevant_functions(self, query: str) -> List[str]:
        """
        Возвращает список релевантных функций для запроса

        Вместо 100 функций → 10-30 релевантных
        """
        categories = self.classify(query)

        relevant_functions = []
        for category in categories:
            relevant_functions.extend(self.get_category_functions(category))

        # Убираем дубликаты (некоторые функции могут быть в нескольких категориях)
        return list(set(relevant_functions))

    def get_stats(self, query: str) -> Dict:
        """
        Возвращает статистику для отладки
        """
        categories = self.classify(query)
        relevant_functions = self.get_relevant_functions(query)

        return {
            "query": query,
            "categories": categories,
            "num_categories": len(categories),
            "num_functions": len(relevant_functions),
            "functions": relevant_functions,
            "reduction": f"{len(relevant_functions)}/100 ({len(relevant_functions)/100*100:.0f}%)"
        }


# Примеры использования
if __name__ == "__main__":
    classifier = QueryClassifier()

    # Тест 1: Math query
    test_queries = [
        "Какая сумма продаж?",
        "Топ 5 менеджеров по продажам",
        "Группировка по городам с суммой",
        "Найди все заказы со словом срочно",
        "Какой тренд продаж за последние 3 месяца?",
        "Подсвети строки где сумма больше 100000",
    ]

    print("🧪 ТЕСТИРОВАНИЕ КЛАССИФИКАТОРА\n")
    print("=" * 80)

    for query in test_queries:
        stats = classifier.get_stats(query)
        print(f"\n📝 Query: {query}")
        print(f"   Categories: {stats['categories']}")
        print(f"   Functions: {stats['num_functions']}/100 ({stats['reduction']})")

    print("\n" + "=" * 80)
    print("\n🎯 СРЕДНЯЯ РЕДУКЦИЯ:")

    total_reduction = 0
    for query in test_queries:
        relevant = classifier.get_relevant_functions(query)
        reduction = len(relevant) / 100
        total_reduction += reduction

    avg_reduction = total_reduction / len(test_queries)
    print(f"   {avg_reduction*100:.0f}% функций отправляется вместо 100%")
    print(f"   Ожидаемое ускорение: {1/avg_reduction:.1f}x")
    print(f"   Tokens saved: ~{(1-avg_reduction)*100:.0f}%")

    print("\n✅ Классификатор готов!")
