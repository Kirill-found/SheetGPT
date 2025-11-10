"""
Intent Parser with Certainty Tracking

Извлекает intent и параметры из пользовательского запроса с уровнем уверенности.
Ключевое отличие от старого подхода: мы ЗНАЕМ что мы НЕ ЗНАЕМ.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class IntentType(Enum):
    """Типы намерений пользователя"""
    INSERT_FORMULA = "insert_formula"
    CREATE_CHART = "create_chart"
    FORMAT_CELLS = "format_cells"
    CONDITIONAL_FORMAT = "conditional_format"
    SORT_DATA = "sort_data"
    CREATE_PIVOT = "create_pivot"
    INSERT_IMAGE = "insert_image"
    ANALYTICAL = "analytical"  # Вопросы типа "какой товар лучше?"
    UNKNOWN = "unknown"


@dataclass
class Parameter:
    """Параметр с уровнем уверенности"""
    name: str
    value: Any
    certainty: float  # 0.0 - 1.0
    source: str  # "explicit" | "inferred" | "default"
    alternatives: List[Any] = None  # Альтернативные значения если certainty низкий

    def needs_clarification(self, threshold: float = 0.9) -> bool:
        """Нужно ли уточнение для этого параметра"""
        return self.certainty < threshold


@dataclass
class Intent:
    """Намерение пользователя с параметрами"""
    type: IntentType
    certainty: float  # Общая уверенность в понимании intent
    parameters: Dict[str, Parameter]
    query: str  # Оригинальный запрос
    context: Dict[str, Any]  # Контекст (колонки, данные)

    def needs_clarification(self, threshold: float = 0.9) -> bool:
        """Нужны ли уточнения для выполнения"""
        if self.certainty < threshold:
            return True

        # Проверяем параметры
        for param in self.parameters.values():
            if param.needs_clarification(threshold):
                return True

        return False

    def get_unclear_parameters(self, threshold: float = 0.9) -> List[Parameter]:
        """Возвращает параметры которые нужно уточнить"""
        return [p for p in self.parameters.values() if p.needs_clarification(threshold)]


class IntentParser:
    """
    Парсер намерений с certainty tracking

    КРИТИЧНО: Никогда не угадываем! Если certainty < 90%, возвращаем низкий certainty.
    """

    def __init__(self):
        # Ключевые слова для reference queries (ссылки на предыдущий контекст)
        self.reference_keywords = {
            "retry": ["попробуй еще раз", "еще раз", "повтори", "заново", "попробуй снова"],
            "modify": ["измени", "поменяй", "замени", "другой", "вместо"],
            "add": ["добавь", "дополнительно", "еще", "также", "плюс"],
            "remove": ["убери", "удали", "без", "минус"],
            "clarify": ["точнее", "уточни", "конкретнее", "детальнее"]
        }

        # Ключевые слова для определения intent (с высокой certainty)
        self.intent_keywords = {
            IntentType.INSERT_FORMULA: [
                "формула", "посчитай", "вычисли", "сумма", "среднее",
                "максимум", "минимум", "количество", "найди", "vlookup"
            ],
            IntentType.CREATE_CHART: [
                "график", "диаграмма", "chart", "построй", "визуализируй",
                "столбчатая", "линейная", "круговая", "pie", "bar"
            ],
            IntentType.CONDITIONAL_FORMAT: [
                # Важно: Conditional format идет ПЕРЕД format_cells!
                # Ключевые признаки условного форматирования:
                "если", "условное", "когда", "автоматически", "динамически",
                "меняй цвет", "подсвечивай когда", "истек", "больше", "меньше"
            ],
            IntentType.FORMAT_CELLS: [
                "выдели", "покрась", "цвет", "жирный", "курсив", "формат",
                "размер шрифта", "фон", "background"
            ],
            IntentType.SORT_DATA: [
                "сортировка", "отсортируй", "упорядочи", "по возрастанию",
                "по убыванию", "sort"
            ],
            IntentType.CREATE_PIVOT: [
                "сводная", "pivot", "агрегация", "группировка"
            ],
            IntentType.INSERT_IMAGE: [
                "вставь картинку", "добавь изображение", "image", "picture"
            ],
            IntentType.ANALYTICAL: [
                "какой", "почему", "что лучше", "анализ", "рекомендуй",
                "посоветуй", "тренд", "прогноз"
            ]
        }

    def parse(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Intent:
        """
        Парсит запрос и возвращает Intent с certainty

        Args:
            query: Запрос пользователя
            context: {
                "columns": ["A", "B", ...],
                "column_names": ["Имя", "Возраст", ...],
                "sample_data": [[...], [...]],
                "row_count": 100
            }

        Returns:
            Intent с параметрами и certainty scores
        """
        query_lower = query.lower()

        # ШАГ 1: Определяем тип intent
        intent_type, intent_certainty = self._detect_intent_type(query_lower)

        # ШАГ 2: Извлекаем параметры в зависимости от типа
        if intent_type == IntentType.INSERT_FORMULA:
            parameters = self._extract_formula_parameters(query, query_lower, context)
        elif intent_type == IntentType.CREATE_CHART:
            parameters = self._extract_chart_parameters(query, query_lower, context)
        elif intent_type == IntentType.FORMAT_CELLS:
            parameters = self._extract_format_parameters(query, query_lower, context)
        elif intent_type == IntentType.CONDITIONAL_FORMAT:
            parameters = self._extract_conditional_format_parameters(query, query_lower, context)
        elif intent_type == IntentType.SORT_DATA:
            parameters = self._extract_sort_parameters(query, query_lower, context)
        elif intent_type == IntentType.CREATE_PIVOT:
            parameters = self._extract_pivot_parameters(query, query_lower, context)
        elif intent_type == IntentType.INSERT_IMAGE:
            parameters = self._extract_image_parameters(query, query_lower, context)
        else:
            parameters = {}

        return Intent(
            type=intent_type,
            certainty=intent_certainty,
            parameters=parameters,
            query=query,
            context=context
        )

    def _detect_intent_type(self, query_lower: str) -> tuple[IntentType, float]:
        """
        Определяет тип intent и certainty

        Returns:
            (IntentType, certainty_score)
        """
        scores = {}

        for intent_type, keywords in self.intent_keywords.items():
            # Считаем сколько ключевых слов найдено
            matches = sum(1 for kw in keywords if kw in query_lower)

            if matches > 0:
                # Новая формула certainty:
                # 1 совпадение = 0.90 (выше threshold!)
                # 2+ совпадений = 0.95
                if matches == 1:
                    certainty = 0.90
                elif matches == 2:
                    certainty = 0.93
                else:
                    certainty = 0.95

                scores[intent_type] = certainty

        if not scores:
            # Не нашли ключевых слов - низкая certainty
            return IntentType.UNKNOWN, 0.3

        # Выбираем intent с наивысшим score
        best_intent = max(scores, key=scores.get)
        return best_intent, scores[best_intent]

    def _extract_formula_parameters(
        self,
        query: str,
        query_lower: str,
        context: Dict
    ) -> Dict[str, Parameter]:
        """Извлекает параметры для формулы"""
        params = {}

        # 1. Определяем тип операции (сумма, среднее, и т.д.)
        operation, op_certainty = self._detect_operation(query_lower)
        params["operation"] = Parameter(
            name="operation",
            value=operation,
            certainty=op_certainty,
            source="inferred" if op_certainty < 0.9 else "explicit"
        )

        # 2. Определяем целевую колонку
        target_column, col_certainty = self._detect_target_column(
            query,
            context.get("column_names", [])
        )
        params["target_column"] = Parameter(
            name="target_column",
            value=target_column,
            certainty=col_certainty,
            source="inferred" if col_certainty < 0.9 else "explicit",
            alternatives=context.get("column_names", []) if col_certainty < 0.7 else None
        )

        # 3. Для VLOOKUP: lookup колонка, result колонка
        if "vlookup" in query_lower or "найди" in query_lower:
            # Эти параметры КРИТИЧНЫ - без них формула будет неправильной
            # Поэтому certainty = 0.0 если не можем определить
            params["lookup_column"] = Parameter(
                name="lookup_column",
                value=None,
                certainty=0.0,  # НУЖНО уточнение!
                source="unknown",
                alternatives=context.get("column_names", [])
            )
            params["result_column"] = Parameter(
                name="result_column",
                value=None,
                certainty=0.0,  # НУЖНО уточнение!
                source="unknown",
                alternatives=context.get("column_names", [])
            )

        return params

    def _detect_operation(self, query_lower: str) -> tuple[str, float]:
        """Определяет тип операции"""
        operations = {
            "sum": (["сумм", "итог", "всего"], 0.95),
            "average": (["средн", "avg"], 0.95),
            "count": (["количество", "счёт", "count"], 0.95),
            "max": (["максимум", "наибольш", "max"], 0.95),
            "min": (["минимум", "наименьш", "min"], 0.95),
            "vlookup": (["найди", "vlookup", "поиск"], 0.90),  # Увеличено до 0.90
            "if": (["если", "условие", "if"], 0.90),  # Увеличено до 0.90
        }

        for op_name, (keywords, certainty) in operations.items():
            if any(kw in query_lower for kw in keywords):
                return op_name, certainty

        # Не определили - низкая certainty
        return "unknown", 0.3

    def _detect_target_column(
        self,
        query: str,
        column_names: List[str]
    ) -> tuple[Optional[str], float]:
        """
        Определяет целевую колонку для операции

        КРИТИЧНО: Если не уверены на 90%+ - возвращаем certainty < 0.9
        """
        query_lower = query.lower()

        # ШАГ 1: Ищем точное упоминание названия колонки
        for col_name in column_names:
            col_lower = col_name.lower()
            if col_lower in query_lower:
                # Нашли явное упоминание - высокая certainty
                return col_name, 0.95

        # ШАГ 2: Ищем частичные совпадения с учетом словоформ
        # Например: "продаж" должно находить "Продажи"
        words = query_lower.split()
        best_match = None
        best_score = 0.0

        for word in words:
            # Пропускаем короткие слова (предлоги, частицы)
            if len(word) < 3:
                continue

            for col_name in column_names:
                col_lower = col_name.lower()

                # Проверяем частичное совпадение в обе стороны
                if word in col_lower:
                    # Слово из запроса входит в название колонки
                    # Например: "продаж" в "продажи"
                    match_ratio = len(word) / len(col_lower)
                    if match_ratio >= 0.7:  # Значительная часть слова
                        score = 0.92  # Высокая certainty!
                    else:
                        score = 0.85

                    if score > best_score:
                        best_match = col_name
                        best_score = score

                elif col_lower in word:
                    # Название колонки входит в слово из запроса
                    # Например: "цен" в "цена"
                    match_ratio = len(col_lower) / len(word)
                    if match_ratio >= 0.7:
                        score = 0.90
                    else:
                        score = 0.75

                    if score > best_score:
                        best_match = col_name
                        best_score = score

        if best_match:
            return best_match, best_score

        # ШАГ 3: Не нашли - возвращаем None с очень низкой certainty
        return None, 0.2

    def _extract_chart_parameters(
        self,
        query: str,
        query_lower: str,
        context: Dict
    ) -> Dict[str, Parameter]:
        """Извлекает параметры для графика"""
        params = {}

        # 1. Тип графика
        chart_type, type_certainty = self._detect_chart_type(query_lower)
        params["chart_type"] = Parameter(
            name="chart_type",
            value=chart_type,
            certainty=type_certainty,
            source="explicit" if type_certainty > 0.9 else "inferred",
            alternatives=["column", "bar", "line", "pie", "area"] if type_certainty < 0.8 else None
        )

        # 2. Data range - КРИТИЧНЫЙ параметр
        # Без правильного range график будет неправильным
        params["data_range"] = Parameter(
            name="data_range",
            value=None,  # Нужно уточнение!
            certainty=0.0,
            source="unknown"
        )

        # 3. Заголовок
        title, title_certainty = self._extract_chart_title(query)
        params["title"] = Parameter(
            name="title",
            value=title,
            certainty=title_certainty,
            source="inferred"
        )

        return params

    def _detect_chart_type(self, query_lower: str) -> tuple[str, float]:
        """Определяет тип графика"""
        chart_types = {
            "column": (["столбч", "колонка", "column"], 0.95),
            "bar": (["гор", "bar"], 0.95),
            "line": (["линейн", "line", "тренд"], 0.95),
            "pie": (["круг", "pie", "долей"], 0.95),
            "area": (["область", "area"], 0.90)
        }

        for chart_type, (keywords, certainty) in chart_types.items():
            if any(kw in query_lower for kw in keywords):
                return chart_type, certainty

        # По умолчанию column, но с низкой certainty
        return "column", 0.6

    def _extract_chart_title(self, query: str) -> tuple[str, float]:
        """Извлекает заголовок графика"""
        # Простая эвристика: первые 3-5 слов
        words = query.split()
        if len(words) <= 5:
            return query, 0.7
        else:
            return " ".join(words[:5]) + "...", 0.5

    def _extract_format_parameters(
        self,
        query: str,
        query_lower: str,
        context: Dict
    ) -> Dict[str, Parameter]:
        """Извлекает параметры для форматирования"""
        params = {}

        # 1. Range для форматирования
        params["range"] = Parameter(
            name="range",
            value=None,
            certainty=0.0,  # НУЖНО уточнение!
            source="unknown"
        )

        # 2. Цвет фона
        bg_color, bg_certainty = self._extract_color(query_lower, "фон")
        params["background_color"] = Parameter(
            name="background_color",
            value=bg_color,
            certainty=bg_certainty,
            source="explicit" if bg_certainty > 0.9 else "inferred"
        )

        # 3. Цвет текста
        text_color, text_certainty = self._extract_color(query_lower, "текст")
        params["text_color"] = Parameter(
            name="text_color",
            value=text_color,
            certainty=text_certainty,
            source="explicit" if text_certainty > 0.9 else "inferred"
        )

        return params

    def _extract_color(self, query_lower: str, context: str) -> tuple[Optional[str], float]:
        """Извлекает цвет из запроса"""
        colors = {
            "красн": "#f44336",
            "зелен": "#4caf50",
            "желт": "#ffeb3b",
            "син": "#2196f3",
            "оранж": "#ff9800",
            "фиолет": "#9c27b0",
            "сер": "#9e9e9e",
            "черн": "#000000",
            "бел": "#ffffff"
        }

        for color_word, hex_code in colors.items():
            if color_word in query_lower:
                return hex_code, 0.95

        # Не нашли цвет
        return None, 0.0

    def _extract_conditional_format_parameters(
        self,
        query: str,
        query_lower: str,
        context: Dict
    ) -> Dict[str, Parameter]:
        """Извлекает параметры для условного форматирования"""
        params = {}

        # Условное форматирование КРИТИЧНО - нужна точная формула условия
        params["condition_formula"] = Parameter(
            name="condition_formula",
            value=None,
            certainty=0.0,  # ВСЕГДА нужно уточнение!
            source="unknown"
        )

        params["range"] = Parameter(
            name="range",
            value=None,
            certainty=0.0,
            source="unknown"
        )

        return params

    def _extract_sort_parameters(
        self,
        query: str,
        query_lower: str,
        context: Dict
    ) -> Dict[str, Parameter]:
        """Извлекает параметры для сортировки"""
        params = {}

        # 1. Колонка для сортировки
        sort_column, col_certainty = self._detect_target_column(query, context.get("column_names", []))
        params["sort_column"] = Parameter(
            name="sort_column",
            value=sort_column,
            certainty=col_certainty,
            source="explicit" if col_certainty > 0.9 else "inferred",
            alternatives=context.get("column_names", []) if col_certainty < 0.8 else None
        )

        # 2. Направление (ascending/descending)
        ascending, asc_certainty = self._detect_sort_direction(query_lower)
        params["ascending"] = Parameter(
            name="ascending",
            value=ascending,
            certainty=asc_certainty,
            source="explicit" if asc_certainty > 0.9 else "default"
        )

        return params

    def _detect_sort_direction(self, query_lower: str) -> tuple[bool, float]:
        """Определяет направление сортировки"""
        if any(kw in query_lower for kw in ["возраст", "убыван", "descending", "больш"]):
            return False, 0.95
        elif any(kw in query_lower for kw in ["возр", "ascending", "меньш"]):
            return True, 0.95
        else:
            # По умолчанию по возрастанию, но с низкой certainty
            return True, 0.6

    def _extract_pivot_parameters(
        self,
        query: str,
        query_lower: str,
        context: Dict
    ) -> Dict[str, Parameter]:
        """Извлекает параметры для сводной таблицы"""
        # Сводная таблица - ОЧЕНЬ сложно угадать правильно
        # ВСЕ параметры нужно уточнить
        return {
            "rows": Parameter("rows", None, 0.0, "unknown", alternatives=context.get("column_names", [])),
            "columns": Parameter("columns", None, 0.0, "unknown", alternatives=context.get("column_names", [])),
            "values": Parameter("values", None, 0.0, "unknown", alternatives=context.get("column_names", [])),
            "aggregation": Parameter("aggregation", "sum", 0.5, "default", alternatives=["sum", "average", "count"])
        }

    def _extract_image_parameters(
        self,
        query: str,
        query_lower: str,
        context: Dict
    ) -> Dict[str, Parameter]:
        """Извлекает параметры для вставки изображения"""
        return {
            "url": Parameter("url", None, 0.0, "unknown"),  # НУЖЕН URL от пользователя
            "cell": Parameter("cell", "A1", 0.5, "default")  # По умолчанию A1
        }

    # ===== Conversation History Support =====

    def _detect_reference_query(self, query: str) -> Optional[str]:
        """
        Определяет является ли запрос reference query (ссылка на предыдущий контекст)

        Returns:
            Тип reference ("retry", "modify", "add", "remove", "clarify") или None
        """
        query_lower = query.lower()

        for ref_type, keywords in self.reference_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return ref_type

        return None

    def parse_with_history(
        self,
        query: str,
        context: Dict[str, Any],
        previous_intent: Optional[Intent] = None
    ) -> Intent:
        """
        Парсит запрос с учетом истории разговора

        Args:
            query: Текущий запрос
            context: Контекст таблицы
            previous_intent: Предыдущий успешный intent (если есть)

        Returns:
            Intent с учетом контекста предыдущих запросов
        """
        # Проверяем является ли это reference query
        ref_type = self._detect_reference_query(query)

        if ref_type and previous_intent:
            # Это reference query - используем previous_intent как базу
            return self._handle_reference_query(query, context, previous_intent, ref_type)
        else:
            # Обычный запрос - парсим как обычно
            return self.parse(query, context)

    def _handle_reference_query(
        self,
        query: str,
        context: Dict[str, Any],
        previous_intent: Intent,
        ref_type: str
    ) -> Intent:
        """
        Обрабатывает reference query используя предыдущий intent

        Args:
            query: Текущий запрос
            context: Контекст таблицы
            previous_intent: Предыдущий успешный intent
            ref_type: Тип reference ("retry", "modify", "add", etc.)

        Returns:
            Модифицированный intent на основе предыдущего
        """
        if ref_type == "retry":
            # "попробуй еще раз" - возвращаем тот же intent
            return Intent(
                type=previous_intent.type,
                certainty=1.0,  # Высокая certainty - это точное повторение
                parameters=previous_intent.parameters.copy(),
                query=query,
                context=context
            )

        elif ref_type == "modify":
            # "измени на X" - парсим новые параметры и мержим с previous
            new_intent = self.parse(query, context)

            # Берем type и базовые параметры из previous_intent
            merged_parameters = previous_intent.parameters.copy()

            # Обновляем параметры которые упомянуты в новом запросе
            for param_name, param in new_intent.parameters.items():
                if param.certainty > 0.5:  # Только если новый параметр достаточно определенный
                    merged_parameters[param_name] = param

            return Intent(
                type=previous_intent.type,  # Сохраняем тип операции
                certainty=0.9,  # Высокая certainty т.к. модифицируем известный intent
                parameters=merged_parameters,
                query=query,
                context=context
            )

        elif ref_type in ["add", "remove"]:
            # "добавь еще" / "убери" - модификация параметров
            # TODO: Реализовать логику для add/remove
            # Пока возвращаем previous_intent
            return previous_intent

        else:
            # Для остальных типов - парсим как обычный запрос
            return self.parse(query, context)
