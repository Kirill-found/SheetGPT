"""
Clarification Dialog System

Генерирует уточняющие вопросы когда certainty параметров низкий.
Это КЛЮЧ к высокой точности - мы не угадываем, а СПРАШИВАЕМ.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.services.intent_parser import Intent, Parameter, IntentType


@dataclass
class Question:
    """Уточняющий вопрос пользователю"""
    parameter_name: str  # Какой параметр уточняем
    question_text: str  # Текст вопроса
    question_type: str  # "select" | "text" | "yes_no" | "range"
    options: Optional[List[Any]] = None  # Варианты ответа (для select)
    default_value: Optional[Any] = None  # Значение по умолчанию
    required: bool = True  # Обязательный ли вопрос
    help_text: Optional[str] = None  # Подсказка для пользователя

    def to_dict(self) -> Dict:
        """Конвертация в словарь для API"""
        return {
            "parameter": self.parameter_name,
            "text": self.question_text,
            "type": self.question_type,
            "options": self.options,
            "default": self.default_value,
            "required": self.required,
            "help": self.help_text
        }


class ClarificationDialog:
    """
    Система генерации уточняющих вопросов

    Принцип: Лучше задать 2-3 вопроса чем выдать неправильный результат!
    """

    def __init__(self, certainty_threshold: float = 0.9):
        """
        Args:
            certainty_threshold: Порог certainty ниже которого задаем вопросы
        """
        self.certainty_threshold = certainty_threshold

    def needs_clarification(self, intent: Intent) -> bool:
        """Нужны ли уточнения для этого intent"""
        return intent.needs_clarification(self.certainty_threshold)

    def generate_questions(self, intent: Intent) -> List[Question]:
        """
        Генерирует список вопросов для уточнения

        Returns:
            Список вопросов в порядке важности
        """
        questions = []

        # Сначала проверяем сам intent
        if intent.certainty < self.certainty_threshold:
            questions.append(self._question_for_intent_type(intent))

        # Затем проверяем параметры
        unclear_params = intent.get_unclear_parameters(self.certainty_threshold)

        for param in unclear_params:
            question = self._question_for_parameter(
                intent.type,
                param,
                intent.context
            )
            if question:
                questions.append(question)

        return questions

    def _question_for_intent_type(self, intent: Intent) -> Question:
        """Генерирует вопрос для уточнения типа intent"""
        return Question(
            parameter_name="_intent_type",
            question_text="Что вы хотите сделать?",
            question_type="select",
            options=[
                {"value": "insert_formula", "label": "Вставить формулу"},
                {"value": "create_chart", "label": "Создать график"},
                {"value": "format_cells", "label": "Форматировать ячейки"},
                {"value": "sort_data", "label": "Сортировать данные"},
                {"value": "create_pivot", "label": "Создать сводную таблицу"}
            ],
            required=True,
            help_text="Выберите действие которое вы хотите выполнить"
        )

    def _question_for_parameter(
        self,
        intent_type: IntentType,
        param: Parameter,
        context: Dict
    ) -> Optional[Question]:
        """
        Генерирует вопрос для конкретного параметра

        В зависимости от типа intent и параметра, генерируем разные типы вопросов
        """
        if intent_type == IntentType.INSERT_FORMULA:
            return self._formula_parameter_question(param, context)
        elif intent_type == IntentType.CREATE_CHART:
            return self._chart_parameter_question(param, context)
        elif intent_type == IntentType.FORMAT_CELLS:
            return self._format_parameter_question(param, context)
        elif intent_type == IntentType.CONDITIONAL_FORMAT:
            return self._conditional_format_parameter_question(param, context)
        elif intent_type == IntentType.SORT_DATA:
            return self._sort_parameter_question(param, context)
        elif intent_type == IntentType.CREATE_PIVOT:
            return self._pivot_parameter_question(param, context)
        elif intent_type == IntentType.INSERT_IMAGE:
            return self._image_parameter_question(param, context)

        return None

    def _formula_parameter_question(
        self,
        param: Parameter,
        context: Dict
    ) -> Optional[Question]:
        """Вопросы для параметров формулы"""

        if param.name == "target_column":
            return Question(
                parameter_name="target_column",
                question_text="На какую колонку применить операцию?",
                question_type="select",
                options=self._column_options(context),
                required=True,
                help_text="Выберите колонку с данными для расчета"
            )

        elif param.name == "lookup_column":
            return Question(
                parameter_name="lookup_column",
                question_text="В какой колонке искать значение?",
                question_type="select",
                options=self._column_options(context),
                required=True,
                help_text="Колонка с ключом для поиска (например, артикул или ID)"
            )

        elif param.name == "result_column":
            return Question(
                parameter_name="result_column",
                question_text="Из какой колонки взять результат?",
                question_type="select",
                options=self._column_options(context),
                required=True,
                help_text="Колонка с данными которые нужно вернуть (например, цена)"
            )

        elif param.name == "operation":
            return Question(
                parameter_name="operation",
                question_text="Какую операцию выполнить?",
                question_type="select",
                options=[
                    {"value": "sum", "label": "Сумма"},
                    {"value": "average", "label": "Среднее"},
                    {"value": "count", "label": "Количество"},
                    {"value": "max", "label": "Максимум"},
                    {"value": "min", "label": "Минимум"},
                    {"value": "vlookup", "label": "Поиск значения (VLOOKUP)"}
                ],
                required=True,
                help_text="Тип расчета для данных"
            )

        return None

    def _chart_parameter_question(
        self,
        param: Parameter,
        context: Dict
    ) -> Optional[Question]:
        """Вопросы для параметров графика"""

        if param.name == "chart_type":
            return Question(
                parameter_name="chart_type",
                question_text="Какой тип графика создать?",
                question_type="select",
                options=[
                    {"value": "column", "label": "Столбчатая диаграмма", "icon": "📊"},
                    {"value": "bar", "label": "Горизонтальная диаграмма", "icon": "📈"},
                    {"value": "line", "label": "Линейный график", "icon": "📉"},
                    {"value": "pie", "label": "Круговая диаграмма", "icon": "🥧"},
                    {"value": "area", "label": "Диаграмма с областями", "icon": "📊"}
                ],
                required=True,
                help_text="Тип визуализации зависит от ваших данных"
            )

        elif param.name == "data_range":
            return Question(
                parameter_name="data_range",
                question_text="Какой диапазон данных использовать для графика?",
                question_type="range",
                help_text="Например: A1:B10 или выберите диапазон мышью",
                required=True
            )

        elif param.name == "title":
            return Question(
                parameter_name="title",
                question_text="Название графика",
                question_type="text",
                default_value=param.value,
                required=False,
                help_text="Оставьте пустым для автоматического названия"
            )

        return None

    def _format_parameter_question(
        self,
        param: Parameter,
        context: Dict
    ) -> Optional[Question]:
        """Вопросы для параметров форматирования"""

        if param.name == "range":
            return Question(
                parameter_name="range",
                question_text="Какой диапазон ячеек отформатировать?",
                question_type="range",
                required=True,
                help_text="Например: A1:B10 или выберите мышью"
            )

        elif param.name == "background_color":
            return Question(
                parameter_name="background_color",
                question_text="Цвет фона",
                question_type="select",
                options=[
                    {"value": "#f44336", "label": "Красный", "color": "#f44336"},
                    {"value": "#4caf50", "label": "Зеленый", "color": "#4caf50"},
                    {"value": "#ffeb3b", "label": "Желтый", "color": "#ffeb3b"},
                    {"value": "#2196f3", "label": "Синий", "color": "#2196f3"},
                    {"value": "#ff9800", "label": "Оранжевый", "color": "#ff9800"},
                    {"value": "#9c27b0", "label": "Фиолетовый", "color": "#9c27b0"},
                    {"value": "#ffffff", "label": "Белый", "color": "#ffffff"},
                    {"value": "", "label": "Без изменений"}
                ],
                required=False,
                help_text="Выберите цвет фона для ячеек"
            )

        elif param.name == "text_color":
            return Question(
                parameter_name="text_color",
                question_text="Цвет текста",
                question_type="select",
                options=[
                    {"value": "#000000", "label": "Черный", "color": "#000000"},
                    {"value": "#ffffff", "label": "Белый", "color": "#ffffff"},
                    {"value": "#f44336", "label": "Красный", "color": "#f44336"},
                    {"value": "#2196f3", "label": "Синий", "color": "#2196f3"},
                    {"value": "", "label": "Без изменений"}
                ],
                required=False,
                help_text="Выберите цвет текста"
            )

        return None

    def _conditional_format_parameter_question(
        self,
        param: Parameter,
        context: Dict
    ) -> Optional[Question]:
        """Вопросы для условного форматирования"""

        if param.name == "condition_formula":
            # Условное форматирование - КРИТИЧНО правильно задать условие
            # Разбиваем на несколько вопросов
            return Question(
                parameter_name="condition_type",
                question_text="Когда применять форматирование?",
                question_type="select",
                options=[
                    {"value": "greater_than", "label": "Значение больше чем..."},
                    {"value": "less_than", "label": "Значение меньше чем..."},
                    {"value": "equal_to", "label": "Значение равно..."},
                    {"value": "between", "label": "Значение между..."},
                    {"value": "date_before", "label": "Дата до..."},
                    {"value": "date_after", "label": "Дата после..."},
                    {"value": "contains_text", "label": "Содержит текст..."},
                    {"value": "custom", "label": "Своя формула"}
                ],
                required=True,
                help_text="Выберите условие для автоматического форматирования"
            )

        elif param.name == "range":
            return Question(
                parameter_name="range",
                question_text="К какому диапазону применить условное форматирование?",
                question_type="range",
                required=True,
                help_text="Диапазон ячеек для проверки условия"
            )

        return None

    def _sort_parameter_question(
        self,
        param: Parameter,
        context: Dict
    ) -> Optional[Question]:
        """Вопросы для сортировки"""

        if param.name == "sort_column":
            return Question(
                parameter_name="sort_column",
                question_text="По какой колонке сортировать?",
                question_type="select",
                options=self._column_options(context),
                required=True,
                help_text="Колонка по значениям которой будет выполнена сортировка"
            )

        elif param.name == "ascending":
            return Question(
                parameter_name="ascending",
                question_text="Направление сортировки",
                question_type="select",
                options=[
                    {"value": True, "label": "По возрастанию (от меньшего к большему)"},
                    {"value": False, "label": "По убыванию (от большего к меньшему)"}
                ],
                default_value=param.value,
                required=True,
                help_text="Порядок сортировки данных"
            )

        return None

    def _pivot_parameter_question(
        self,
        param: Parameter,
        context: Dict
    ) -> Optional[Question]:
        """Вопросы для сводной таблицы"""

        if param.name == "rows":
            return Question(
                parameter_name="rows",
                question_text="Какие поля использовать для строк?",
                question_type="multiselect",
                options=self._column_options(context),
                required=True,
                help_text="Поля для группировки по строкам"
            )

        elif param.name == "columns":
            return Question(
                parameter_name="columns",
                question_text="Какие поля использовать для колонок?",
                question_type="multiselect",
                options=self._column_options(context),
                required=False,
                help_text="Поля для группировки по колонкам (опционально)"
            )

        elif param.name == "values":
            return Question(
                parameter_name="values",
                question_text="Какие поля подсчитывать?",
                question_type="select",
                options=self._column_options(context),
                required=True,
                help_text="Поля с числовыми значениями для расчета"
            )

        elif param.name == "aggregation":
            return Question(
                parameter_name="aggregation",
                question_text="Функция агрегации",
                question_type="select",
                options=[
                    {"value": "sum", "label": "Сумма"},
                    {"value": "average", "label": "Среднее"},
                    {"value": "count", "label": "Количество"},
                    {"value": "max", "label": "Максимум"},
                    {"value": "min", "label": "Минимум"}
                ],
                default_value="sum",
                required=True,
                help_text="Как агрегировать значения"
            )

        return None

    def _image_parameter_question(
        self,
        param: Parameter,
        context: Dict
    ) -> Optional[Question]:
        """Вопросы для вставки изображения"""

        if param.name == "url":
            return Question(
                parameter_name="url",
                question_text="URL изображения или загрузите файл",
                question_type="text",
                required=True,
                help_text="Вставьте ссылку на изображение или загрузите файл"
            )

        elif param.name == "cell":
            return Question(
                parameter_name="cell",
                question_text="В какую ячейку вставить изображение?",
                question_type="text",
                default_value="A1",
                required=True,
                help_text="Например: A1, B5"
            )

        return None

    def _column_options(self, context: Dict) -> List[Dict]:
        """Генерирует options для выбора колонок"""
        column_names = context.get("column_names", [])
        columns_letters = context.get("columns", [])

        options = []
        for i, name in enumerate(column_names):
            letter = columns_letters[i] if i < len(columns_letters) else chr(65 + i)
            options.append({
                "value": name,
                "label": f"{letter}: {name}",
                "column_letter": letter
            })

        return options

    def apply_answers(
        self,
        intent: Intent,
        answers: Dict[str, Any]
    ) -> Intent:
        """
        Применяет ответы пользователя к intent

        Args:
            intent: Оригинальный intent с низкой certainty
            answers: Ответы пользователя {parameter_name: value}

        Returns:
            Обновленный intent с высокой certainty
        """
        # Обновляем intent type если был вопрос о нем
        if "_intent_type" in answers:
            intent.type = IntentType(answers["_intent_type"])
            intent.certainty = 1.0  # Пользователь явно указал - 100% certainty

        # Обновляем параметры
        for param_name, answer_value in answers.items():
            if param_name.startswith("_"):
                continue  # Служебные параметры

            if param_name in intent.parameters:
                # Обновляем существующий параметр
                intent.parameters[param_name].value = answer_value
                intent.parameters[param_name].certainty = 1.0  # Пользователь ответил - 100% certainty
                intent.parameters[param_name].source = "explicit"
            else:
                # Добавляем новый параметр
                intent.parameters[param_name] = Parameter(
                    name=param_name,
                    value=answer_value,
                    certainty=1.0,
                    source="explicit"
                )

        return intent
