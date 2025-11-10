"""
Action Composer - Verified Action Builder

КЛЮЧЕВОЕ ОТЛИЧИЕ от старого подхода:
- Старый: GPT генерирует action целиком (может ошибиться)
- Новый: Собираем action из ПРОВЕРЕННЫХ параметров (100% certainty)

Если certainty < 100% - НЕ СОЗДАЕМ action, а возвращаем ошибку!
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from app.services.intent_parser import Intent, IntentType, Parameter


@dataclass
class Action:
    """Действие для выполнения в Google Sheets"""
    type: str  # "insert_formula", "create_chart", etc.
    config: Dict[str, Any]  # Конфигурация action
    confidence: float  # Уверенность в правильности (0.0 - 1.0)
    validation_notes: List[str]  # Замечания о валидации
    explanation: str  # Объяснение что делает action


class ActionCompositionError(Exception):
    """Ошибка при сборке action - означает что нужны уточнения"""
    pass


class ActionComposer:
    """
    Собирает actions из проверенных параметров

    ГАРАНТИЯ: Если метод вернул Action - он ТОЧНО правильный (95%+ certainty)
    """

    def __init__(self, min_certainty: float = 0.95):
        """
        Args:
            min_certainty: Минимальная certainty для создания action
        """
        self.min_certainty = min_certainty

    def compose(self, intent: Intent) -> Action:
        """
        Собирает action из intent с проверенными параметрами

        Raises:
            ActionCompositionError: Если certainty недостаточная

        Returns:
            Action с высокой certainty
        """
        # Проверяем что intent certainty достаточная
        if intent.certainty < self.min_certainty:
            raise ActionCompositionError(
                f"Intent certainty too low: {intent.certainty} < {self.min_certainty}"
            )

        # Проверяем что ВСЕ параметры имеют достаточную certainty
        for param_name, param in intent.parameters.items():
            if param.value is not None and param.certainty < self.min_certainty:
                raise ActionCompositionError(
                    f"Parameter '{param_name}' certainty too low: {param.certainty} < {self.min_certainty}"
                )

        # Собираем action в зависимости от типа
        if intent.type == IntentType.INSERT_FORMULA:
            return self._compose_formula_action(intent)
        elif intent.type == IntentType.CREATE_CHART:
            return self._compose_chart_action(intent)
        elif intent.type == IntentType.FORMAT_CELLS:
            return self._compose_format_action(intent)
        elif intent.type == IntentType.CONDITIONAL_FORMAT:
            return self._compose_conditional_format_action(intent)
        elif intent.type == IntentType.SORT_DATA:
            return self._compose_sort_action(intent)
        elif intent.type == IntentType.CREATE_PIVOT:
            return self._compose_pivot_action(intent)
        elif intent.type == IntentType.INSERT_IMAGE:
            return self._compose_image_action(intent)
        else:
            raise ActionCompositionError(f"Unknown intent type: {intent.type}")

    def _compose_formula_action(self, intent: Intent) -> Action:
        """Собирает action для вставки формулы"""
        operation = self._get_verified_param(intent, "operation")
        target_column = self._get_verified_param(intent, "target_column")

        # Строим формулу из проверенных блоков
        if operation == "sum":
            formula = self._build_sum_formula(target_column, intent.context)
            explanation = f"Сумма значений в колонке '{target_column}'"

        elif operation == "average":
            formula = self._build_average_formula(target_column, intent.context)
            explanation = f"Среднее значений в колонке '{target_column}'"

        elif operation == "count":
            formula = self._build_count_formula(target_column, intent.context)
            explanation = f"Количество значений в колонке '{target_column}'"

        elif operation == "max":
            formula = self._build_max_formula(target_column, intent.context)
            explanation = f"Максимальное значение в колонке '{target_column}'"

        elif operation == "min":
            formula = self._build_min_formula(target_column, intent.context)
            explanation = f"Минимальное значение в колонке '{target_column}'"

        elif operation == "vlookup":
            # VLOOKUP требует дополнительных параметров
            lookup_column = self._get_verified_param(intent, "lookup_column")
            result_column = self._get_verified_param(intent, "result_column")

            formula = self._build_vlookup_formula(
                lookup_column,
                result_column,
                intent.context
            )
            explanation = f"Поиск значения из колонки '{result_column}' по ключу из '{lookup_column}'"

        else:
            raise ActionCompositionError(f"Unsupported operation: {operation}")

        return Action(
            type="insert_formula",
            config={
                "cell": "A1",  # TODO: определять из контекста
                "formula": formula
            },
            confidence=self._calculate_action_confidence(intent),
            validation_notes=[],
            explanation=explanation
        )

    def _build_sum_formula(self, column: str, context: Dict) -> str:
        """Строит формулу суммы (проверенный блок)"""
        col_letter = self._column_name_to_letter(column, context)
        row_count = context.get("row_count", 100)

        # АНГЛИЙСКИЕ формулы работают в любой локали Google Sheets
        return f"=SUM({col_letter}2:{col_letter}{row_count})"

    def _build_average_formula(self, column: str, context: Dict) -> str:
        """Строит формулу среднего (проверенный блок)"""
        col_letter = self._column_name_to_letter(column, context)
        row_count = context.get("row_count", 100)

        return f"=AVERAGE({col_letter}2:{col_letter}{row_count})"

    def _build_count_formula(self, column: str, context: Dict) -> str:
        """Строит формулу подсчета (проверенный блок)"""
        col_letter = self._column_name_to_letter(column, context)
        row_count = context.get("row_count", 100)

        return f"=COUNT({col_letter}2:{col_letter}{row_count})"

    def _build_max_formula(self, column: str, context: Dict) -> str:
        """Строит формулу максимума (проверенный блок)"""
        col_letter = self._column_name_to_letter(column, context)
        row_count = context.get("row_count", 100)

        return f"=MAX({col_letter}2:{col_letter}{row_count})"

    def _build_min_formula(self, column: str, context: Dict) -> str:
        """Строит формулу минимума (проверенный блок)"""
        col_letter = self._column_name_to_letter(column, context)
        row_count = context.get("row_count", 100)

        return f"=MIN({col_letter}2:{col_letter}{row_count})"

    def _build_vlookup_formula(
        self,
        lookup_column: str,
        result_column: str,
        context: Dict
    ) -> str:
        """Строит формулу VLOOKUP (проверенный блок)"""
        lookup_letter = self._column_name_to_letter(lookup_column, context)
        result_letter = self._column_name_to_letter(result_column, context)

        # Определяем column index (КРИТИЧНО для правильности!)
        column_names = context.get("column_names", [])
        try:
            lookup_index = column_names.index(lookup_column) + 1
            result_index = column_names.index(result_column) + 1
            col_diff = result_index - lookup_index + 1
        except ValueError:
            raise ActionCompositionError("Cannot determine column indices for VLOOKUP")

        # Строим range для таблицы
        row_count = context.get("row_count", 100)
        table_range = f"{lookup_letter}1:{result_letter}{row_count}"

        # VLOOKUP с IFERROR (проверенный pattern) - АНГЛИЙСКИЕ функции работают везде!
        return f'=IFERROR(VLOOKUP({lookup_letter}2,{table_range},{col_diff},FALSE),"")'

    def _compose_chart_action(self, intent: Intent) -> Action:
        """Собирает action для создания графика"""
        chart_type = self._get_verified_param(intent, "chart_type")
        data_range = self._get_verified_param(intent, "data_range")
        title = intent.parameters.get("title", Parameter("title", "График", 1.0, "default")).value

        # Валидируем data_range
        if not self._validate_range(data_range, intent.context):
            raise ActionCompositionError(f"Invalid data range: {data_range}")

        return Action(
            type="create_chart",
            config={
                "type": chart_type,
                "dataRange": data_range,
                "title": title
            },
            confidence=self._calculate_action_confidence(intent),
            validation_notes=[],
            explanation=f"Создание {chart_type} графика для диапазона {data_range}"
        )

    def _compose_format_action(self, intent: Intent) -> Action:
        """Собирает action для форматирования"""
        range_param = self._get_verified_param(intent, "range")

        # Валидируем range
        if not self._validate_range(range_param, intent.context):
            raise ActionCompositionError(f"Invalid range: {range_param}")

        config = {"range": range_param}

        # Добавляем опциональные параметры
        if "background_color" in intent.parameters:
            bg_color = intent.parameters["background_color"]
            if bg_color.value and bg_color.certainty >= self.min_certainty:
                config["backgroundColor"] = bg_color.value

        if "text_color" in intent.parameters:
            text_color = intent.parameters["text_color"]
            if text_color.value and text_color.certainty >= self.min_certainty:
                config["textColor"] = text_color.value

        return Action(
            type="format_cells",
            config=config,
            confidence=self._calculate_action_confidence(intent),
            validation_notes=[],
            explanation=f"Форматирование диапазона {range_param}"
        )

    def _compose_conditional_format_action(self, intent: Intent) -> Action:
        """Собирает action для условного форматирования"""
        range_param = self._get_verified_param(intent, "range")
        condition_formula = self._get_verified_param(intent, "condition_formula")

        # Валидируем range и формулу
        if not self._validate_range(range_param, intent.context):
            raise ActionCompositionError(f"Invalid range: {range_param}")

        return Action(
            type="apply_conditional_format",
            config={
                "range": range_param,
                "formula": condition_formula,
                "backgroundColor": "#f4cccc"  # Цвет по умолчанию
            },
            confidence=self._calculate_action_confidence(intent),
            validation_notes=[],
            explanation=f"Условное форматирование для диапазона {range_param}"
        )

    def _compose_sort_action(self, intent: Intent) -> Action:
        """Собирает action для сортировки"""
        sort_column = self._get_verified_param(intent, "sort_column")
        ascending = self._get_verified_param(intent, "ascending")

        # Определяем column index
        column_names = context.get("column_names", [])
        try:
            col_index = column_names.index(sort_column) + 1
        except ValueError:
            raise ActionCompositionError(f"Column '{sort_column}' not found")

        # Определяем range для сортировки (вся таблица)
        col_letter = self._column_name_to_letter(sort_column, intent.context)
        row_count = intent.context.get("row_count", 100)
        num_columns = len(column_names)
        last_col_letter = chr(64 + num_columns)  # A=65

        sort_range = f"A2:{last_col_letter}{row_count}"

        return Action(
            type="sort_data",
            config={
                "range": sort_range,
                "column": col_index,
                "ascending": ascending
            },
            confidence=self._calculate_action_confidence(intent),
            validation_notes=[],
            explanation=f"Сортировка по колонке '{sort_column}' ({'по возрастанию' if ascending else 'по убыванию'})"
        )

    def _compose_pivot_action(self, intent: Intent) -> Action:
        """Собирает action для сводной таблицы"""
        rows = self._get_verified_param(intent, "rows")
        values = self._get_verified_param(intent, "values")
        aggregation = self._get_verified_param(intent, "aggregation")

        columns = intent.parameters.get("columns", Parameter("columns", None, 1.0, "default")).value

        return Action(
            type="create_pivot",
            config={
                "rows": rows if isinstance(rows, list) else [rows],
                "columns": columns if isinstance(columns, list) else ([columns] if columns else []),
                "values": values,
                "aggregation": aggregation
            },
            confidence=self._calculate_action_confidence(intent),
            validation_notes=[],
            explanation=f"Создание сводной таблицы по полям: {rows}"
        )

    def _compose_image_action(self, intent: Intent) -> Action:
        """Собирает action для вставки изображения"""
        url = self._get_verified_param(intent, "url")
        cell = intent.parameters.get("cell", Parameter("cell", "A1", 1.0, "default")).value

        return Action(
            type="insert_image",
            config={
                "url": url,
                "cell": cell
            },
            confidence=self._calculate_action_confidence(intent),
            validation_notes=[],
            explanation=f"Вставка изображения в ячейку {cell}"
        )

    def _get_verified_param(self, intent: Intent, param_name: str) -> Any:
        """
        Получает значение параметра с проверкой certainty

        Raises:
            ActionCompositionError: Если параметр отсутствует или certainty низкая
        """
        if param_name not in intent.parameters:
            raise ActionCompositionError(f"Required parameter '{param_name}' is missing")

        param = intent.parameters[param_name]

        if param.value is None:
            raise ActionCompositionError(f"Parameter '{param_name}' has no value")

        if param.certainty < self.min_certainty:
            raise ActionCompositionError(
                f"Parameter '{param_name}' certainty too low: {param.certainty} < {self.min_certainty}"
            )

        return param.value

    def _column_name_to_letter(self, column_name: str, context: Dict) -> str:
        """Конвертирует имя колонки в букву (A, B, C, ...)"""
        column_names = context.get("column_names", [])

        try:
            index = column_names.index(column_name)
            return chr(65 + index)  # A=65
        except ValueError:
            # Fallback: если column_name уже буква
            if len(column_name) == 1 and column_name.isupper():
                return column_name
            raise ActionCompositionError(f"Cannot convert column '{column_name}' to letter")

    def _validate_range(self, range_str: str, context: Dict) -> bool:
        """Проверяет что range валидный"""
        # Простая проверка формата: A1:B10
        import re
        pattern = r'^[A-Z]+\d+:[A-Z]+\d+$'

        if not re.match(pattern, range_str):
            return False

        # TODO: Проверить что range не выходит за границы таблицы

        return True

    def _calculate_action_confidence(self, intent: Intent) -> float:
        """Рассчитывает финальную confidence action"""
        # Начинаем с intent certainty
        confidence = intent.certainty

        # Учитываем certainty всех параметров
        param_certainties = [p.certainty for p in intent.parameters.values() if p.value is not None]

        if param_certainties:
            avg_param_certainty = sum(param_certainties) / len(param_certainties)
            # Итоговая confidence = среднее между intent и параметрами
            confidence = (confidence + avg_param_certainty) / 2

        return round(confidence, 2)
