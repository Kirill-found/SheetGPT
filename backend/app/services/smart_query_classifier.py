"""
Smart Query Classifier v1.0.0 - Гибридная классификация запросов

Три уровня классификации:
1. SIMPLE (60% запросов) - Pattern matching, 0 tokens
   - "сумма продаж", "топ 5", "сортировка по дате"

2. MEDIUM (30% запросов) - Function Calling, ~300 tokens
   - "найди заказы Иванова в Москве за март"

3. COMPLEX (10% запросов) - Text-to-Pandas, ~500 tokens
   - "посчитай корреляцию между возрастом и покупками"
   - "сделай pivot таблицу продаж по регионам и месяцам"
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class QueryComplexity(Enum):
    SIMPLE = "simple"      # Pattern matching - 0 tokens
    MEDIUM = "medium"      # Function Calling - ~300 tokens
    COMPLEX = "complex"    # Text-to-Pandas - ~500 tokens


@dataclass
class ClassificationResult:
    """Результат классификации запроса."""
    complexity: QueryComplexity
    confidence: float
    reason: str
    detected_pattern: Optional[str] = None
    suggested_function: Optional[str] = None
    extracted_params: Optional[Dict[str, Any]] = None


class SmartQueryClassifier:
    """
    Умный классификатор запросов для выбора оптимальной стратегии.

    Приоритет: минимизация токенов при максимизации точности.
    """

    # ===== SIMPLE PATTERNS (0 tokens) =====
    # Формат: (pattern_name, regex, function_name, param_extractor)
    SIMPLE_PATTERNS = [
        # Агрегации
        ("sum", r"(сумм[ауы]|total|итого)\s+(.+)", "calculate_sum", lambda m: {"column": m.group(2)}),
        ("average", r"(средн[еяий]+|average|avg)\s+(.+)", "calculate_average", lambda m: {"column": m.group(2)}),
        ("count", r"(сколько|количество|count)\s+(строк|записей|всего)", "calculate_count", lambda m: {}),
        ("max", r"(максимум|макс|max|наибольш[еаяий]+)\s+(.+)", "calculate_max", lambda m: {"column": m.group(2)}),
        ("min", r"(минимум|мин|min|наименьш[еаяий]+)\s+(.+)", "calculate_min", lambda m: {"column": m.group(2)}),

        # Top N
        ("top_n", r"(топ|top|лучши[хе]|первы[хе])\s*(\d+)", "filter_top_n", lambda m: {"n": int(m.group(2))}),
        ("bottom_n", r"(худши[хе]|последни[хе]|bottom)\s*(\d+)", "filter_bottom_n", lambda m: {"n": int(m.group(2))}),

        # Сортировка
        ("sort_asc", r"(сортир|отсортир|упоряд).*(по возраст|asc|↑)", "sort_data", lambda m: {"ascending": True}),
        ("sort_desc", r"(сортир|отсортир|упоряд).*(по убыв|desc|↓)", "sort_data", lambda m: {"ascending": False}),
        ("sort_simple", r"(сортир|отсортир|упоряд)\w*\s+(по\s+)?(.+)", "sort_data", lambda m: {"column": m.group(3)}),

        # Фильтрация базовая
        ("filter_empty", r"(пуст[ыеоая]+|empty)\s+(строк|ячеек)", "filter_empty", lambda m: {}),
        ("filter_duplicates", r"(дублика|повтор|duplicat)", "filter_duplicates", lambda m: {}),
        ("filter_unique", r"(уникальн|unique)", "filter_unique", lambda m: {}),

        # Подсветка
        ("highlight", r"(выдел[иь]|подсвет[иь]|highlight)\s+.*(где|which|with)", "highlight_rows", lambda m: {}),
    ]

    # ===== MEDIUM INDICATORS =====
    # Запросы, требующие Function Calling
    MEDIUM_INDICATORS = [
        r"(где|which|where)\s+.+\s*(=|>|<|равн|больш|меньш)",  # Условия
        r"(найд[иь]|find|search)\s+.+",                          # Поиск
        r"(группир|group\s*by)\s+.+",                            # Группировка
        r"(объедини|merge|join)\s+.+",                           # Объединение
        r"(за\s+\w+\s+(месяц|год|квартал|неделю))",              # Фильтр по периоду
        r"(\w+)\s+(и|или|and|or)\s+(\w+)",                       # Составные условия
    ]

    # ===== COMPLEX INDICATORS =====
    # Запросы, требующие Code Generation
    COMPLEX_INDICATORS = [
        r"(корреляц|correlation)",                               # Статистика
        r"(pivot|сводн|кросс.?табл)",                            # Pivot tables
        r"(регресс|regression|прогноз|forecast)",                # Прогнозирование
        r"(распределени|distribution|гистограмм)",               # Распределения
        r"(кластер|cluster|сегмент)",                            # Кластеризация
        r"(процентил|percentile|квартил|quartile)",              # Квантили
        r"(накопител|cumulative|нарастающ)",                     # Накопительные
        r"(скольз|moving|rolling)\s*(средн|average|sum)",        # Скользящие
        r"(год к году|год/год|yoy|year.over.year)",              # YoY анализ
        r"(топ.?\d+.*(для|по|в)\s*кажд)",                        # Top N per group
    ]

    def classify(self, query: str, column_names: List[str] = None) -> ClassificationResult:
        """
        Классифицирует запрос и возвращает рекомендуемую стратегию.

        Args:
            query: Текст запроса пользователя
            column_names: Список названий колонок (для уточнения)

        Returns:
            ClassificationResult с рекомендацией
        """
        query_lower = query.lower().strip()

        # 1. Проверяем SIMPLE patterns (0 tokens!)
        for pattern_name, regex, func_name, param_extractor in self.SIMPLE_PATTERNS:
            match = re.search(regex, query_lower, re.IGNORECASE)
            if match:
                try:
                    params = param_extractor(match)

                    # Валидируем параметры (если указана колонка, проверяем её наличие)
                    if column_names and "column" in params:
                        col_param = params["column"]
                        matched_col = self._fuzzy_match_column(col_param, column_names)
                        if matched_col:
                            params["column"] = matched_col
                        else:
                            # Колонка не найдена - переходим к MEDIUM
                            continue

                    return ClassificationResult(
                        complexity=QueryComplexity.SIMPLE,
                        confidence=0.95,
                        reason=f"Pattern match: {pattern_name}",
                        detected_pattern=pattern_name,
                        suggested_function=func_name,
                        extracted_params=params
                    )
                except:
                    continue

        # 2. Проверяем COMPLEX indicators
        for pattern in self.COMPLEX_INDICATORS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return ClassificationResult(
                    complexity=QueryComplexity.COMPLEX,
                    confidence=0.90,
                    reason=f"Complex pattern detected: {pattern[:30]}..."
                )

        # 3. Проверяем MEDIUM indicators
        for pattern in self.MEDIUM_INDICATORS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return ClassificationResult(
                    complexity=QueryComplexity.MEDIUM,
                    confidence=0.85,
                    reason=f"Medium pattern detected: {pattern[:30]}..."
                )

        # 4. Эвристика по длине и сложности
        word_count = len(query.split())
        has_numbers = bool(re.search(r'\d+', query))
        has_operators = bool(re.search(r'[><=!]', query))

        complexity_score = 0
        complexity_score += min(word_count / 5, 2)  # Длина запроса
        complexity_score += 0.5 if has_numbers else 0
        complexity_score += 0.5 if has_operators else 0
        complexity_score += query_lower.count(' и ') * 0.3
        complexity_score += query_lower.count(' или ') * 0.3

        if complexity_score < 1.5:
            return ClassificationResult(
                complexity=QueryComplexity.SIMPLE,
                confidence=0.70,
                reason="Short simple query (heuristic)"
            )
        elif complexity_score < 3:
            return ClassificationResult(
                complexity=QueryComplexity.MEDIUM,
                confidence=0.75,
                reason=f"Medium complexity (score={complexity_score:.1f})"
            )
        else:
            return ClassificationResult(
                complexity=QueryComplexity.COMPLEX,
                confidence=0.80,
                reason=f"High complexity (score={complexity_score:.1f})"
            )

    def _fuzzy_match_column(self, search: str, column_names: List[str]) -> Optional[str]:
        """Нечёткий поиск колонки по названию."""
        search_lower = search.lower().strip()

        # 1. Точное совпадение
        for col in column_names:
            if col.lower() == search_lower:
                return col

        # 2. Содержит искомое
        for col in column_names:
            if search_lower in col.lower():
                return col

        # 3. Искомое содержит название колонки
        for col in column_names:
            if col.lower() in search_lower:
                return col

        return None

    def get_execution_strategy(self, result: ClassificationResult) -> Dict[str, Any]:
        """
        Возвращает стратегию выполнения на основе классификации.
        """
        strategies = {
            QueryComplexity.SIMPLE: {
                "method": "pattern_execution",
                "model": None,  # No LLM call
                "tokens_estimate": 0,
                "latency_estimate": "50ms",
                "function": result.suggested_function,
                "params": result.extracted_params
            },
            QueryComplexity.MEDIUM: {
                "method": "function_calling",
                "model": "gpt-4o-mini",
                "tokens_estimate": 300,
                "latency_estimate": "500ms"
            },
            QueryComplexity.COMPLEX: {
                "method": "text_to_pandas",
                "model": "gpt-4o",
                "tokens_estimate": 800,
                "latency_estimate": "1500ms"
            }
        }

        return strategies[result.complexity]


# Singleton
_classifier = None

def get_smart_classifier() -> SmartQueryClassifier:
    """Возвращает singleton instance SmartQueryClassifier."""
    global _classifier
    if _classifier is None:
        _classifier = SmartQueryClassifier()
    return _classifier
