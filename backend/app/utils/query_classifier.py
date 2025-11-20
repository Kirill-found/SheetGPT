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
                r'\b(сколько|количество|число)',  # ADD: pattern for COUNT queries
                r'\b(count|how many)',  # ADD: English pattern for COUNT
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
                r'\b(от\s+нов.*\s+к\s+стар|от\s+стар.*\s+к\s+нов)',  # "от новых к старым", "от старых к новым"
                r'\b(сначала\s+нов|сначала\s+стар)',  # "сначала новые", "сначала старые"
                r'\b(по\s+дат|по\s+возраст|по\s+убыван)',  # "по дате", "по возрастанию", "по убыванию"
                r'\b(от\s+больш.*\s+к\s+меньш|от\s+меньш.*\s+к\s+больш)',  # "от большего к меньшему"
                r'\b(oldest\s+first|newest\s+first|by\s+date)',  # English temporal sorting
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
            "split": [
                r'\b(разбей|раздели)',
                r'\b(split|break)',
                r'\b(ячейк)',  # "по ячейкам"
                r'\b(разделит)',
            ],
            "action": [
                r'\b(подсвет|выдел|создай|добав|удали|измени)',
                r'\b(highlight|create|add|delete|modify|update)',
                r'\b(график|диаграмм|chart)',
                r'\b(таблиц)',
                r'\b(table)',
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

        v7.8.10 FIX: Используем РЕАЛЬНЫЕ имена функций из FunctionRegistry
        Было: 90% несуществующих функций → GPT-4o получал только 4 функции
        Стало: 100% существующих функций → GPT-4o получает 10-30 релевантных функций
        """
        function_map = {
            "math": [
                "calculate_abs",
                "calculate_average",
                "calculate_ceiling",
                "calculate_count",
                "calculate_count_all",
                "calculate_covariance",
                "calculate_floor",
                "calculate_iqr",
                "calculate_kurtosis",
                "calculate_log",
                "calculate_mad",
                "calculate_max",
                "calculate_median",
                "calculate_min",
                "calculate_mode",
                "calculate_percentage",
                "calculate_power",
                "calculate_product",
                "calculate_quantile",
                "calculate_rank",
                "calculate_ratio",
                "calculate_round",
                "calculate_skewness",
                "calculate_sqrt",
                "calculate_std",
                "calculate_sum",
                "calculate_z_score",
            ],  # 27 functions
            "filter": [
                "filter_between",
                "filter_bottom_n",
                "filter_in_list",
                "filter_multiple",
                "filter_not_in_list",
                "filter_not_null",
                "filter_null",
                "filter_outliers",
                "filter_regex",
                "filter_rows",
                "filter_top_n",
            ],  # 11 functions
            "group": [
                "aggregate_by_group",
                "pivot_table",
                "top_n_per_group",
                "vlookup",
            ],  # 4 functions
            "sort": [
                "calculate_rank",  # ранжирование
                "filter_bottom_n",  # фильтрация + сортировка (нижние N)
                "filter_top_n",  # фильтрация + сортировка (верхние N)
                "sort_data",  # ГЛАВНАЯ функция сортировки - ЭТО ИСПРАВЛЯЕТ БАГ!
            ],  # 4 functions
            "text": [
                "capitalize",
                "contains_count",
                "extract_emails",
                "extract_numbers",
                "extract_substring",
                "lowercase",
                "pad_string",
                "remove_special_chars",
                "split_column",
                "text_length",
                "title_case",
                "uppercase",
            ],  # 12 functions
            "date": [
                "add_days",
                "end_of_month",
                "extract_day",
                "extract_month",
                "extract_quarter",
                "extract_weekday",
                "extract_year",
                "format_date",
                "start_of_month",
                "subtract_days",
            ],  # 10 functions
            "split": [
                "split_data",
            ],  # 1 function
            "action": [
                "case_when",
                "coalesce",
                "count_distinct",
                "create_bins",
                "cumulative_max",
                "cumulative_min",
                "detect_outliers",
                "ewma",
                "fill_missing",
                "first_value",
                "highlight_rows",
                "if_then_else",
                "lag_column",
                "last_value",
                "lead_column",
                "moving_average",
                "remove_duplicates",
                "search_rows",
            ],  # 18 functions
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
