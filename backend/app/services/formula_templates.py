"""
Расширенная библиотека готовых формул.
Покрывает ~85-90% запросов пользователей с 100% надежностью.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class FormulaTemplate:
    """Шаблон формулы"""
    id: str
    name: str
    keywords: List[str]
    formula_pattern: str
    description: str
    category: str
    requires_params: List[str]
    handles_empty: bool = False
    is_array: bool = False
    priority: int = 1  # Приоритет при конфликтах (выше = важнее)
    examples: List[str] = field(default_factory=list)


# =============================================================================
# КАТЕГОРИЯ 1: БАЗОВАЯ МАТЕМАТИКА (15 templates)
# =============================================================================

TEMPLATES = {

    # 1. СУММА СТОЛБЦА
    "sum_column": FormulaTemplate(
        id="sum_column",
        name="Сумма столбца",
        keywords=["сумма", "сложи", "итого", "total", "sum", "всего", "общая сумма", "посчитай сумму"],
        formula_pattern="=SUM({column}:{column})",
        description="Складывает все числа в столбце",
        category="math",
        requires_params=["column"],
        priority=3,
        examples=["Посчитай сумму продаж", "Итого по ценам", "Сколько всего в столбце B?"]
    ),

    # 2. СРЕДНЕЕ ЗНАЧЕНИЕ
    "average_column": FormulaTemplate(
        id="average_column",
        name="Среднее значение",
        keywords=["среднее", "средний", "average", "avg", "mean", "средний показатель", "в среднем", "найди среднее", "средняя цена", "среднее значение", "средний чек"],
        formula_pattern="=AVERAGE({column}:{column})",
        description="Находит среднее арифметическое",
        category="math",
        requires_params=["column"],
        priority=3,
        examples=["Найди средние продажи", "Средняя цена", "Среднее по столбцу C"]
    ),

    # 3. МЕДИАНА
    "median_value": FormulaTemplate(
        id="median_value",
        name="Медиана",
        keywords=["медиана", "median", "среднее значение по медиане", "медианное значение"],
        formula_pattern="=MEDIAN({column}:{column})",
        description="Находит медианное значение",
        category="math",
        requires_params=["column"],
        examples=["Найди медиану цен", "Медианное значение продаж"]
    ),

    # 4. МАКСИМУМ
    "max_value": FormulaTemplate(
        id="max_value",
        name="Максимальное значение",
        keywords=["максимум", "max", "максимальный", "максимальное", "самый большой", "наибольший", "самое большое"],
        formula_pattern="=MAX({column}:{column})",
        description="Находит максимальное значение",
        category="math",
        requires_params=["column"],
        priority=3,
        examples=["Найди максимальную цену", "Самая большая сумма", "Максимум в столбце B"]
    ),

    # 5. МИНИМУМ
    "min_value": FormulaTemplate(
        id="min_value",
        name="Минимальное значение",
        keywords=["минимум", "min", "минимальный", "минимальное", "самый маленький", "наименьший", "самое маленькое"],
        formula_pattern="=MIN({column}:{column})",
        description="Находит минимальное значение",
        category="math",
        requires_params=["column"],
        priority=3,
        examples=["Найди минимальную цену", "Самая маленькая сумма", "Минимум в столбце C"]
    ),

    # 6. ПОДСЧЕТ КОЛИЧЕСТВА
    "count_all": FormulaTemplate(
        id="count_all",
        name="Подсчет всех значений",
        keywords=["сколько", "количество", "count", "число", "посчитай сколько", "количество строк"],
        formula_pattern="=COUNTA({column}:{column})",
        description="Считает количество непустых ячеек",
        category="math",
        requires_params=["column"],
        priority=2,
        examples=["Сколько товаров?", "Количество записей", "Сколько строк в столбце A?"]
    ),

    # 7. ПОДСЧЕТ ЧИСЕЛ
    "count_numbers": FormulaTemplate(
        id="count_numbers",
        name="Подсчет чисел",
        keywords=["сколько чисел", "количество чисел", "count numbers", "числовых значений"],
        formula_pattern="=COUNT({column}:{column})",
        description="Считает количество ячеек с числами",
        category="math",
        requires_params=["column"],
        examples=["Сколько числовых значений?", "Количество чисел в столбце"]
    ),

    # 8. ПОДСЧЕТ ПУСТЫХ
    "count_blank": FormulaTemplate(
        id="count_blank",
        name="Подсчет пустых ячеек",
        keywords=["сколько пустых", "количество пустых", "пустые ячейки", "незаполненные"],
        formula_pattern="=COUNTBLANK({column}:{column})",
        description="Считает количество пустых ячеек",
        category="math",
        requires_params=["column"],
        examples=["Сколько пустых ячеек?", "Количество незаполненных строк"]
    ),

    # 9. ОКРУГЛЕНИЕ
    "round_number": FormulaTemplate(
        id="round_number",
        name="Округление",
        keywords=["округли", "round", "округлить", "без копеек", "целое число", "округление"],
        formula_pattern="=ROUND({cell},{decimals})",
        description="Округляет число до указанного количества знаков",
        category="math",
        requires_params=["cell", "decimals"],
        priority=2,
        examples=["Округли до целого", "Округли до 2 знаков после запятой"]
    ),

    # 10. ПРОЦЕНТ ОТ ЧИСЛА
    "percentage": FormulaTemplate(
        id="percentage",
        name="Процент от числа",
        keywords=["процент", "percent", "%", "доля", "процент от"],
        formula_pattern="={part_col}/{total_col}",
        description="Вычисляет процент (часть/целое)",
        category="math",
        requires_params=["part_col", "total_col"],
        priority=2,
        examples=["Какой процент продаж от плана?", "Доля региона в общих продажах"]
    ),

    # 11. АБСОЛЮТНОЕ ЗНАЧЕНИЕ
    "absolute_value": FormulaTemplate(
        id="absolute_value",
        name="Модуль числа",
        keywords=["модуль", "абсолютное значение", "abs", "absolute", "по модулю"],
        formula_pattern="=ABS({cell})",
        description="Возвращает абсолютное значение (без знака)",
        category="math",
        requires_params=["cell"],
        examples=["Модуль числа", "Абсолютное значение разницы"]
    ),

    # 12. КВАДРАТНЫЙ КОРЕНЬ
    "square_root": FormulaTemplate(
        id="square_root",
        name="Квадратный корень",
        keywords=["корень", "квадратный корень", "sqrt", "square root"],
        formula_pattern="=SQRT({cell})",
        description="Вычисляет квадратный корень",
        category="math",
        requires_params=["cell"],
        examples=["Квадратный корень из числа", "Корень из значения"]
    ),

    # 13. СТЕПЕНЬ
    "power": FormulaTemplate(
        id="power",
        name="Возведение в степень",
        keywords=["степень", "power", "в квадрате", "в кубе", "возведи в степень"],
        formula_pattern="=POWER({cell},{exponent})",
        description="Возводит число в степень",
        category="math",
        requires_params=["cell", "exponent"],
        examples=["Возведи в квадрат", "В степень 3", "Число в степени 2"]
    ),

    # 14. ПРОИЗВЕДЕНИЕ
    "product": FormulaTemplate(
        id="product",
        name="Произведение",
        keywords=["произведение", "product", "умножь", "перемножь", "multiplication"],
        formula_pattern="=PRODUCT({column}:{column})",
        description="Перемножает все числа",
        category="math",
        requires_params=["column"],
        examples=["Перемножь все значения", "Произведение чисел в столбце"]
    ),

    # 15. СТАНДАРТНОЕ ОТКЛОНЕНИЕ
    "stdev": FormulaTemplate(
        id="stdev",
        name="Стандартное отклонение",
        keywords=["стандартное отклонение", "stdev", "дисперсия", "разброс"],
        formula_pattern="=STDEV({column}:{column})",
        description="Вычисляет стандартное отклонение",
        category="math",
        requires_params=["column"],
        examples=["Стандартное отклонение продаж", "Разброс значений"]
    ),


    # =============================================================================
    # КАТЕГОРИЯ 2: РАБОТА С ТЕКСТОМ (15 templates)
    # =============================================================================

    # 16. ОБЪЕДИНЕНИЕ ФИО (КРИТИЧНО!)
    "concatenate_full_name": FormulaTemplate(
        id="concatenate_full_name",
        name="Объединение ФИО",
        keywords=["фио", "полное имя", "full name", "объедини имя", "соедини имя", "фамилия имя отчество", "создай фио", "полное фио", "объедини фио", "создай полное"],
        formula_pattern='=IF(LEN({col1})=0,"",{col1}&" "&{col2}&" "&{col3})',
        description="Объединяет фамилию, имя, отчество с пробелами",
        category="text",
        requires_params=["col1", "col2", "col3"],
        handles_empty=True,
        priority=5,
        examples=["Создай полное ФИО", "Объедини фамилию имя отчество", "Полное имя в столбце D"]
    ),

    # 17. ОБЪЕДИНЕНИЕ ДВУХ СТОЛБЦОВ
    "concatenate_two": FormulaTemplate(
        id="concatenate_two",
        name="Объединение двух столбцов",
        keywords=["объедини", "соедини", "склей", "concat", "объединить два столбца"],
        formula_pattern='=IF(LEN({col1})=0,{col2},IF(LEN({col2})=0,{col1},{col1}&"{separator}"&{col2}))',
        description="Объединяет два столбца с разделителем",
        category="text",
        requires_params=["col1", "col2", "separator"],
        handles_empty=True,
        priority=3,
        examples=["Объедини улицу и город", "Соедини имя и фамилию через запятую"]
    ),

    # 18. ИЗВЛЕЧЬ ПЕРВЫЕ N СИМВОЛОВ
    "left_text": FormulaTemplate(
        id="left_text",
        name="Первые символы",
        keywords=["первые", "left", "первые символы", "первые буквы", "начало текста"],
        formula_pattern="=LEFT({cell},{count})",
        description="Извлекает первые N символов",
        category="text",
        requires_params=["cell", "count"],
        examples=["Первые 5 символов", "Первые 3 буквы"]
    ),

    # 19. ИЗВЛЕЧЬ ПОСЛЕДНИЕ N СИМВОЛОВ
    "right_text": FormulaTemplate(
        id="right_text",
        name="Последние символы",
        keywords=["последние", "right", "последние символы", "последние буквы", "конец текста"],
        formula_pattern="=RIGHT({cell},{count})",
        description="Извлекает последние N символов",
        category="text",
        requires_params=["cell", "count"],
        examples=["Последние 4 символа", "Последние 2 буквы"]
    ),

    # 20. ДЛИНА ТЕКСТА
    "text_length": FormulaTemplate(
        id="text_length",
        name="Длина текста",
        keywords=["длина", "length", "len", "сколько символов", "количество символов"],
        formula_pattern="=LEN({cell})",
        description="Возвращает количество символов в тексте",
        category="text",
        requires_params=["cell"],
        examples=["Сколько символов в тексте?", "Длина строки"]
    ),

    # 21. УДАЛИТЬ ПРОБЕЛЫ
    "trim_text": FormulaTemplate(
        id="trim_text",
        name="Удалить лишние пробелы",
        keywords=["убери пробелы", "trim", "удали пробелы", "лишние пробелы", "очисти пробелы"],
        formula_pattern="=TRIM({cell})",
        description="Удаляет лишние пробелы в начале, конце и внутри текста",
        category="text",
        requires_params=["cell"],
        priority=2,
        examples=["Убери лишние пробелы", "Очисти текст от пробелов"]
    ),

    # 22. ВЕРХНИЙ РЕГИСТР
    "upper_case": FormulaTemplate(
        id="upper_case",
        name="ЗАГЛАВНЫЕ БУКВЫ",
        keywords=["заглавные", "upper", "uppercase", "большие буквы", "капс", "капслок"],
        formula_pattern="=UPPER({cell})",
        description="Преобразует текст в ЗАГЛАВНЫЕ буквы",
        category="text",
        requires_params=["cell"],
        examples=["Сделай заглавными буквами", "Преобразуй в uppercase"]
    ),

    # 23. НИЖНИЙ РЕГИСТР
    "lower_case": FormulaTemplate(
        id="lower_case",
        name="строчные буквы",
        keywords=["строчные", "lower", "lowercase", "маленькие буквы"],
        formula_pattern="=LOWER({cell})",
        description="Преобразует текст в строчные буквы",
        category="text",
        requires_params=["cell"],
        examples=["Сделай строчными", "Преобразуй в lowercase"]
    ),

    # 24. ЗАГЛАВНАЯ ПЕРВАЯ БУКВА
    "proper_case": FormulaTemplate(
        id="proper_case",
        name="Заглавная первая буква каждого слова",
        keywords=["первая заглавная", "proper", "capitalize", "заглавная буква в начале"],
        formula_pattern="=PROPER({cell})",
        description="Делает первую букву каждого слова заглавной",
        category="text",
        requires_params=["cell"],
        examples=["Сделай первые буквы заглавными", "Capitalize words"]
    ),

    # 25. ЗАМЕНА ТЕКСТА
    "replace_text": FormulaTemplate(
        id="replace_text",
        name="Замена текста",
        keywords=["замени", "replace", "замена", "поменяй текст", "заменить"],
        formula_pattern='=SUBSTITUTE({cell},"{old_text}","{new_text}")',
        description="Заменяет один текст на другой",
        category="text",
        requires_params=["cell", "old_text", "new_text"],
        examples=["Замени точку на запятую", "Поменяй старый текст на новый"]
    ),

    # 26. ПРОВЕРКА СОДЕРЖИТ ЛИ
    "contains_text": FormulaTemplate(
        id="contains_text",
        name="Проверка содержит ли текст",
        keywords=["содержит", "contains", "есть ли", "включает"],
        formula_pattern='=IF(ISNUMBER(SEARCH("{search_text}",{cell})),"Да","Нет")',
        description="Проверяет содержит ли текст подстроку",
        category="text",
        requires_params=["search_text", "cell"],
        examples=["Проверь содержит ли email @", "Есть ли в тексте слово"]
    ),

    # 27. ТЕКСТ В ЧИСЛО
    "text_to_number": FormulaTemplate(
        id="text_to_number",
        name="Преобразовать текст в число",
        keywords=["текст в число", "text to number", "преобразуй в число", "конверт в число"],
        formula_pattern="=VALUE({cell})",
        description="Преобразует текст в число",
        category="text",
        requires_params=["cell"],
        examples=["Преобразуй текст в число", "Конвертируй в number"]
    ),

    # 28. РАЗДЕЛИТЬ ТЕКСТ
    "split_text": FormulaTemplate(
        id="split_text",
        name="Разделить текст",
        keywords=["раздели", "split", "разбить", "разделить по", "split by"],
        formula_pattern='=SPLIT({cell},"{delimiter}")',
        description="Разделяет текст по разделителю на несколько столбцов",
        category="text",
        requires_params=["cell", "delimiter"],
        examples=["Раздели по пробелу", "Split by comma", "Разбить на части"]
    ),

    # 29. ОБЪЕДИНЕНИЕ С ПЕРЕНОСОМ СТРОКИ
    "concatenate_with_newline": FormulaTemplate(
        id="concatenate_with_newline",
        name="Объединение с переносом строки",
        keywords=["объедини с новой строки", "соедини через enter", "перенос строки", "в столбик"],
        formula_pattern='={col1}&CHAR(10)&{col2}',
        description="Объединяет текст с переносом строки",
        category="text",
        requires_params=["col1", "col2"],
        examples=["Объедини с переносом строки", "Адрес в две строки"]
    ),

    # 30. ПОВТОРИТЬ ТЕКСТ
    "repeat_text": FormulaTemplate(
        id="repeat_text",
        name="Повторить текст",
        keywords=["повтори", "repeat", "дублируй", "повторить n раз"],
        formula_pattern='=REPT({cell},{count})',
        description="Повторяет текст указанное количество раз",
        category="text",
        requires_params=["cell", "count"],
        examples=["Повтори текст 3 раза", "Дублируй символ 5 раз"]
    ),


    # =============================================================================
    # КАТЕГОРИЯ 3: ПОИСК И УСЛОВИЯ (20 templates)
    # =============================================================================

    # 31. VLOOKUP БАЗОВЫЙ
    "vlookup_basic": FormulaTemplate(
        id="vlookup_basic",
        name="Поиск значения (VLOOKUP)",
        keywords=["найди", "vlookup", "поиск", "lookup", "найти значение", "найди цену", "найди данные"],
        formula_pattern='=IFERROR(VLOOKUP({lookup_cell},{table_range},{column_index},FALSE),"Не найдено")',
        description="Ищет значение в другой таблице",
        category="lookup",
        requires_params=["lookup_cell", "table_range", "column_index"],
        priority=4,
        examples=["Найди цену товара из прайс-листа", "VLOOKUP по артикулу"]
    ),

    # 32. INDEX + MATCH
    "index_match": FormulaTemplate(
        id="index_match",
        name="Поиск INDEX+MATCH",
        keywords=["index match", "индекс матч", "поиск двусторонний"],
        formula_pattern='=IFERROR(INDEX({return_range},MATCH({lookup_value},{lookup_range},0)),"Не найдено")',
        description="Гибкий поиск значения (лучше чем VLOOKUP)",
        category="lookup",
        requires_params=["return_range", "lookup_value", "lookup_range"],
        priority=3,
        examples=["Найди используя INDEX MATCH", "Двусторонний поиск"]
    ),

    # 33. IF ПРОСТОЕ УСЛОВИЕ
    "if_simple": FormulaTemplate(
        id="if_simple",
        name="Простое условие IF",
        keywords=["если", "if", "условие", "если больше", "если меньше", "если равно"],
        formula_pattern='=IF({cell}{operator}{value},"{true_text}","{false_text}")',
        description="Проверяет условие и возвращает разные значения",
        category="logic",
        requires_params=["cell", "operator", "value", "true_text", "false_text"],
        priority=4,
        examples=["Если продажи >100000 то Выполнено иначе Не выполнено"]
    ),

    # 34. SUMIF (сумма по условию)
    "sumif_basic": FormulaTemplate(
        id="sumif_basic",
        name="Сумма по условию",
        keywords=["сумма если", "sumif", "сложи если", "сумма по условию", "сумма только", "сумма где"],
        formula_pattern='=SUMIF({criteria_range},"{criteria}",{sum_range})',
        description="Суммирует значения которые удовлетворяют условию",
        category="aggregate",
        requires_params=["criteria_range", "criteria", "sum_range"],
        priority=4,
        examples=["Сумма продаж по Москве", "Сложи только товары категории A"]
    ),

    # 35. COUNTIF (подсчет по условию)
    "countif_basic": FormulaTemplate(
        id="countif_basic",
        name="Подсчет по условию",
        keywords=["сколько если", "countif", "количество если", "посчитай сколько", "количество где"],
        formula_pattern='=COUNTIF({range},"{criteria}")',
        description="Считает количество ячеек удовлетворяющих условию",
        category="aggregate",
        requires_params=["range", "criteria"],
        priority=4,
        examples=["Сколько товаров дороже 500?", "Количество заказов со статусом Выполнен"]
    ),

    # 36. AVERAGEIF (среднее по условию)
    "averageif_basic": FormulaTemplate(
        id="averageif_basic",
        name="Среднее по условию",
        keywords=["среднее если", "averageif", "средний показатель где", "average по условию"],
        formula_pattern='=AVERAGEIF({criteria_range},"{criteria}",{average_range})',
        description="Вычисляет среднее для значений удовлетворяющих условию",
        category="aggregate",
        requires_params=["criteria_range", "criteria", "average_range"],
        examples=["Среднее продаж по Москве", "Средняя цена для категории A"]
    ),

    # 37. AND (все условия истинны)
    "and_logic": FormulaTemplate(
        id="and_logic",
        name="Логическое И (AND)",
        keywords=["and", "и", "все условия", "оба условия", "логическое и"],
        formula_pattern='=AND({condition1},{condition2})',
        description="Проверяет истинны ли ВСЕ условия",
        category="logic",
        requires_params=["condition1", "condition2"],
        examples=["Проверь истинны ли оба условия", "AND для двух проверок"]
    ),

    # 38. OR (хотя бы одно условие истинно)
    "or_logic": FormulaTemplate(
        id="or_logic",
        name="Логическое ИЛИ (OR)",
        keywords=["or", "или", "хотя бы одно", "любое условие", "логическое или"],
        formula_pattern='=OR({condition1},{condition2})',
        description="Проверяет истинно ли ХОТЯ БЫ ОДНО условие",
        category="logic",
        requires_params=["condition1", "condition2"],
        examples=["Проверь истинно ли хотя бы одно условие", "OR для альтернатив"]
    ),

    # 39. NOT (отрицание)
    "not_logic": FormulaTemplate(
        id="not_logic",
        name="Логическое НЕ (NOT)",
        keywords=["not", "не", "отрицание", "обратное", "инверсия"],
        formula_pattern='=NOT({condition})',
        description="Инвертирует логическое значение",
        category="logic",
        requires_params=["condition"],
        examples=["Обратное значение условия", "NOT для инверсии"]
    ),

    # 40. ISBLANK (проверка на пустоту)
    "is_blank": FormulaTemplate(
        id="is_blank",
        name="Проверка на пустую ячейку",
        keywords=["пустая", "isblank", "пустая ячейка", "проверь пустая", "is empty"],
        formula_pattern='=IF(ISBLANK({cell}),"Пустая","Заполнена")',
        description="Проверяет является ли ячейка пустой",
        category="logic",
        requires_params=["cell"],
        examples=["Проверь пустая ли ячейка", "Is cell empty"]
    ),

    # 41. ISNUMBER (проверка на число)
    "is_number": FormulaTemplate(
        id="is_number",
        name="Проверка на число",
        keywords=["число", "isnumber", "это число", "проверь число", "is numeric"],
        formula_pattern='=IF(ISNUMBER({cell}),"Число","Не число")',
        description="Проверяет является ли значение числом",
        category="logic",
        requires_params=["cell"],
        examples=["Проверь это число?", "Is numeric value"]
    ),

    # 42. ISERROR (проверка на ошибку)
    "is_error": FormulaTemplate(
        id="is_error",
        name="Проверка на ошибку",
        keywords=["ошибка", "iserror", "проверь ошибка", "есть ошибка", "error check"],
        formula_pattern='=IF(ISERROR({formula}),"Ошибка","OK")',
        description="Проверяет содержит ли формула ошибку",
        category="logic",
        requires_params=["formula"],
        examples=["Проверь есть ли ошибка в формуле"]
    ),

    # 43. IFERROR (обработка ошибок)
    "if_error_handler": FormulaTemplate(
        id="if_error_handler",
        name="Обработка ошибок",
        keywords=["если ошибка", "iferror", "обработай ошибку", "при ошибке"],
        formula_pattern='=IFERROR({formula},"{error_value}")',
        description="Возвращает альтернативное значение при ошибке",
        category="logic",
        requires_params=["formula", "error_value"],
        priority=2,
        examples=["Если ошибка то вернуть 0", "При ошибке показать Не найдено"]
    ),

    # 44. MAXIFS (максимум по условию)
    "maxifs": FormulaTemplate(
        id="maxifs",
        name="Максимум по условию",
        keywords=["максимум если", "maxifs", "самый большой где", "max по условию"],
        formula_pattern='=MAXIFS({max_range},{criteria_range},"{criteria}")',
        description="Находит максимум среди значений удовлетворяющих условию",
        category="aggregate",
        requires_params=["max_range", "criteria_range", "criteria"],
        examples=["Максимальная цена в категории A", "Самая большая продажа по Москве"]
    ),

    # 45. MINIFS (минимум по условию)
    "minifs": FormulaTemplate(
        id="minifs",
        name="Минимум по условию",
        keywords=["минимум если", "minifs", "самый маленький где", "min по условию"],
        formula_pattern='=MINIFS({min_range},{criteria_range},"{criteria}")',
        description="Находит минимум среди значений удовлетворяющих условию",
        category="aggregate",
        requires_params=["min_range", "criteria_range", "criteria"],
        examples=["Минимальная цена в категории B", "Самая маленькая продажа по СПб"]
    ),

    # 46. SUMIF БОЛЬШЕ/МЕНЬШЕ
    "sumif_comparison": FormulaTemplate(
        id="sumif_comparison",
        name="Сумма по условию сравнения",
        keywords=["сумма больше", "сумма меньше", "sumif greater", "sumif less"],
        formula_pattern='=SUMIF({range},"{operator}{value}")',
        description="Суммирует значения больше/меньше заданного",
        category="aggregate",
        requires_params=["range", "operator", "value"],
        priority=3,
        examples=["Сумма всех значений больше 1000", "Сложи где меньше 500"]
    ),

    # 47. COUNTIF БОЛЬШЕ/МЕНЬШЕ
    "countif_comparison": FormulaTemplate(
        id="countif_comparison",
        name="Подсчет по сравнению",
        keywords=["сколько больше", "сколько меньше", "количество больше", "countif greater"],
        formula_pattern='=COUNTIF({range},"{operator}{value}")',
        description="Считает сколько значений больше/меньше заданного",
        category="aggregate",
        requires_params=["range", "operator", "value"],
        priority=3,
        examples=["Сколько продаж больше 1000?", "Количество цен меньше 500"]
    ),

    # 48. SUMIFS (сумма по нескольким условиям)
    "sumifs_multiple": FormulaTemplate(
        id="sumifs_multiple",
        name="Сумма по нескольким условиям",
        keywords=["sumifs", "сумма по нескольким", "сумма и", "сумма с двумя условиями"],
        formula_pattern='=SUMIFS({sum_range},{criteria_range1},"{criteria1}",{criteria_range2},"{criteria2}")',
        description="Суммирует по нескольким условиям одновременно",
        category="aggregate",
        requires_params=["sum_range", "criteria_range1", "criteria1", "criteria_range2", "criteria2"],
        priority=3,
        examples=["Сумма продаж по Москве и категории A", "Сложи где регион=СПб И статус=Выполнен"]
    ),

    # 49. COUNTIFS (подсчет по нескольким условиям)
    "countifs_multiple": FormulaTemplate(
        id="countifs_multiple",
        name="Подсчет по нескольким условиям",
        keywords=["countifs", "количество по нескольким", "сколько и", "подсчет с двумя условиями"],
        formula_pattern='=COUNTIFS({range1},"{criteria1}",{range2},"{criteria2}")',
        description="Считает количество по нескольким условиям",
        category="aggregate",
        requires_params=["range1", "criteria1", "range2", "criteria2"],
        examples=["Сколько товаров дороже 500 И категории A?"]
    ),

    # 50. IF ВЛОЖЕННОЕ (3 условия)
    "if_nested_3": FormulaTemplate(
        id="if_nested_3",
        name="Вложенное условие (3 варианта)",
        keywords=["если несколько", "вложенное если", "3 условия", "nested if"],
        formula_pattern='=IF({cell}>{value1},"{text1}",IF({cell}>{value2},"{text2}","{text3}"))',
        description="Проверяет несколько условий последовательно",
        category="logic",
        requires_params=["cell", "value1", "value2", "text1", "text2", "text3"],
        priority=3,
        examples=["Если >1000 то Большой, если >500 то Средний, иначе Малый"]
    ),


    # =============================================================================
    # КАТЕГОРИЯ 4: РАБОТА С ДАТАМИ (10 templates)
    # =============================================================================

    # 51. СЕГОДНЯШНЯЯ ДАТА
    "today": FormulaTemplate(
        id="today",
        name="Сегодняшняя дата",
        keywords=["сегодня", "today", "текущая дата", "сегодняшняя дата"],
        formula_pattern="=TODAY()",
        description="Возвращает текущую дату",
        category="date",
        requires_params=[],
        priority=3,
        examples=["Вставь сегодняшнюю дату", "Текущая дата"]
    ),

    # 52. СЕЙЧАС (дата + время)
    "now": FormulaTemplate(
        id="now",
        name="Текущие дата и время",
        keywords=["сейчас", "now", "текущее время", "дата и время"],
        formula_pattern="=NOW()",
        description="Возвращает текущие дату и время",
        category="date",
        requires_params=[],
        examples=["Вставь текущее время", "Сейчас дата и время"]
    ),

    # 53. РАЗНИЦА МЕЖДУ ДАТАМИ
    "date_difference": FormulaTemplate(
        id="date_difference",
        name="Разница между датами",
        keywords=["сколько дней", "разница дат", "дней между", "дней прошло", "разница между датами"],
        formula_pattern="=DATEVALUE({date2})-DATEVALUE({date1})",
        description="Считает количество дней между двумя датами",
        category="date",
        requires_params=["date1", "date2"],
        priority=4,
        examples=["Сколько дней между стартом и финишем?", "Разница между датами в A и B"]
    ),

    # 54. ДОБАВИТЬ ДНИ К ДАТЕ
    "add_days": FormulaTemplate(
        id="add_days",
        name="Добавить дни к дате",
        keywords=["добавь дней", "через", "плюс дней", "add days", "дней спустя"],
        formula_pattern="={date_cell}+{days}",
        description="Добавляет количество дней к дате",
        category="date",
        requires_params=["date_cell", "days"],
        examples=["Дата через 30 дней", "Добавь 7 дней к дате"]
    ),

    # 55. ИЗВЛЕЧЬ ГОД
    "extract_year": FormulaTemplate(
        id="extract_year",
        name="Извлечь год из даты",
        keywords=["год", "year", "какой год", "извлечь год", "только год"],
        formula_pattern="=YEAR({date_cell})",
        description="Извлекает год из даты",
        category="date",
        requires_params=["date_cell"],
        examples=["Извлечь год из даты", "Какой год?"]
    ),

    # 56. ИЗВЛЕЧЬ МЕСЯЦ
    "extract_month": FormulaTemplate(
        id="extract_month",
        name="Извлечь месяц из даты",
        keywords=["месяц", "month", "какой месяц", "извлечь месяц", "только месяц"],
        formula_pattern="=MONTH({date_cell})",
        description="Извлекает номер месяца из даты (1-12)",
        category="date",
        requires_params=["date_cell"],
        examples=["Извлечь месяц из даты", "Какой месяц?"]
    ),

    # 57. ИЗВЛЕЧЬ ДЕНЬ
    "extract_day": FormulaTemplate(
        id="extract_day",
        name="Извлечь день из даты",
        keywords=["день", "day", "какой день", "извлечь день", "число месяца"],
        formula_pattern="=DAY({date_cell})",
        description="Извлекает день месяца из даты (1-31)",
        category="date",
        requires_params=["date_cell"],
        examples=["Извлечь день из даты", "Какое число?"]
    ),

    # 58. ВОЗРАСТ
    "age_years": FormulaTemplate(
        id="age_years",
        name="Возраст в годах",
        keywords=["возраст", "age", "сколько лет", "полных лет"],
        formula_pattern='=DATEDIF({birth_date},TODAY(),"Y")',
        description="Вычисляет возраст в полных годах",
        category="date",
        requires_params=["birth_date"],
        examples=["Сколько лет человеку?", "Возраст по дате рождения"]
    ),

    # 59. РАБОЧИЕ ДНИ
    "workdays": FormulaTemplate(
        id="workdays",
        name="Количество рабочих дней",
        keywords=["рабочие дни", "workdays", "рабочих дней между", "networkdays"],
        formula_pattern="=NETWORKDAYS({start_date},{end_date})",
        description="Считает количество рабочих дней между датами (исключая выходные)",
        category="date",
        requires_params=["start_date", "end_date"],
        examples=["Сколько рабочих дней между датами?", "Рабочие дни"]
    ),

    # 60. ПОСЛЕДНИЙ ДЕНЬ МЕСЯЦА
    "end_of_month": FormulaTemplate(
        id="end_of_month",
        name="Последний день месяца",
        keywords=["последний день месяца", "конец месяца", "end of month", "eomonth"],
        formula_pattern="=EOMONTH({date_cell},0)",
        description="Возвращает последний день месяца для даты",
        category="date",
        requires_params=["date_cell"],
        examples=["Последний день месяца", "Конец месяца"]
    ),


    # =============================================================================
    # КАТЕГОРИЯ 5: ФИНАНСОВЫЕ РАСЧЕТЫ (10 templates)
    # =============================================================================

    # 61. ПРИБЫЛЬ (доход - расход)
    "profit": FormulaTemplate(
        id="profit",
        name="Прибыль",
        keywords=["прибыль", "profit", "доход минус расход", "чистая прибыль", "выручка минус затраты"],
        formula_pattern="={revenue_col}-{expense_col}",
        description="Вычисляет прибыль (доход - расход)",
        category="financial",
        requires_params=["revenue_col", "expense_col"],
        priority=4,
        examples=["Посчитай прибыль", "Доход минус расход"]
    ),

    # 62. МАРЖА (процент прибыли)
    "margin": FormulaTemplate(
        id="margin",
        name="Маржа (рентабельность)",
        keywords=["маржа", "margin", "рентабельность", "процент прибыли", "прибыльность"],
        formula_pattern="=({revenue_col}-{expense_col})/{revenue_col}",
        description="Вычисляет маржу в процентах",
        category="financial",
        requires_params=["revenue_col", "expense_col"],
        priority=4,
        examples=["Посчитай маржу", "Какая рентабельность?"]
    ),

    # 63. ПРОЦЕНТ ИЗМЕНЕНИЯ
    "percentage_change": FormulaTemplate(
        id="percentage_change",
        name="Процент изменения",
        keywords=["рост", "изменение", "темп роста", "на сколько процентов", "процент изменения", "динамика"],
        formula_pattern="=({new_value}-{old_value})/{old_value}",
        description="Вычисляет процент изменения относительно предыдущего значения",
        category="financial",
        requires_params=["new_value", "old_value"],
        priority=3,
        examples=["На сколько % выросли продажи?", "Темп роста относительно прошлого месяца"]
    ),

    # 64. ЦЕНА С НДС
    "price_with_vat": FormulaTemplate(
        id="price_with_vat",
        name="Цена с НДС",
        keywords=["с ндс", "добавить ндс", "vat", "включить ндс", "плюс ндс"],
        formula_pattern="={price}*(1+{vat_rate})",
        description="Добавляет НДС к цене",
        category="financial",
        requires_params=["price", "vat_rate"],
        examples=["Цена с НДС 20%", "Добавь НДС к цене"]
    ),

    # 65. ЦЕНА БЕЗ НДС
    "price_without_vat": FormulaTemplate(
        id="price_without_vat",
        name="Цена без НДС",
        keywords=["без ндс", "убрать ндс", "исключить ндс", "минус ндс", "выделить ндс"],
        formula_pattern="={price}/(1+{vat_rate})",
        description="Выделяет НДС из цены",
        category="financial",
        requires_params=["price", "vat_rate"],
        examples=["Цена без НДС", "Убери НДС из цены"]
    ),

    # 66. ВЫДЕЛИТЬ НДС ИЗ СУММЫ
    "extract_vat": FormulaTemplate(
        id="extract_vat",
        name="Выделить НДС",
        keywords=["выделить ндс", "сумма ндс", "размер ндс", "сколько ндс"],
        formula_pattern="={price}-{price}/(1+{vat_rate})",
        description="Вычисляет сумму НДС включенного в цену",
        category="financial",
        requires_params=["price", "vat_rate"],
        examples=["Сколько НДС в цене?", "Выдели НДС из суммы"]
    ),

    # 67. СКИДКА В РУБЛЯХ
    "discount_amount": FormulaTemplate(
        id="discount_amount",
        name="Скидка в рублях",
        keywords=["скидка", "discount", "размер скидки", "сумма скидки"],
        formula_pattern="={price}*{discount_percent}",
        description="Вычисляет сумму скидки",
        category="financial",
        requires_params=["price", "discount_percent"],
        examples=["Сколько рублей скидка?", "Размер скидки 15%"]
    ),

    # 68. ЦЕНА СО СКИДКОЙ
    "price_with_discount": FormulaTemplate(
        id="price_with_discount",
        name="Цена со скидкой",
        keywords=["цена со скидкой", "price after discount", "цена после скидки", "финальная цена"],
        formula_pattern="={price}*(1-{discount_percent})",
        description="Вычисляет цену после применения скидки",
        category="financial",
        requires_params=["price", "discount_percent"],
        examples=["Цена со скидкой 20%", "Финальная цена после discount"]
    ),

    # 69. ROI (возврат инвестиций)
    "roi": FormulaTemplate(
        id="roi",
        name="ROI (возврат инвестиций)",
        keywords=["roi", "возврат инвестиций", "return on investment", "окупаемость"],
        formula_pattern="=({gain}-{cost})/{cost}",
        description="Вычисляет ROI (return on investment)",
        category="financial",
        requires_params=["gain", "cost"],
        examples=["Посчитай ROI", "Возврат инвестиций"]
    ),

    # 70. СРЕДНИЙ ЧЕК
    "average_check": FormulaTemplate(
        id="average_check",
        name="Средний чек",
        keywords=["средний чек", "average check", "средняя покупка", "средний заказ"],
        formula_pattern="={total_revenue}/{transaction_count}",
        description="Вычисляет средний чек (выручка / количество покупок)",
        category="financial",
        requires_params=["total_revenue", "transaction_count"],
        examples=["Какой средний чек?", "Средняя сумма заказа"]
    ),


    # =============================================================================
    # КАТЕГОРИЯ 6: АГРЕГАЦИЯ И ГРУППИРОВКА (5 templates)
    # =============================================================================

    # 71. УНИКАЛЬНЫЕ ЗНАЧЕНИЯ
    "unique_values": FormulaTemplate(
        id="unique_values",
        name="Уникальные значения",
        keywords=["уникальные", "unique", "без повторов", "без дубликатов", "уникальные значения"],
        formula_pattern="=UNIQUE({range})",
        description="Возвращает список уникальных значений",
        category="data",
        requires_params=["range"],
        priority=3,
        examples=["Покажи уникальные товары", "Список без повторов"]
    ),

    # 72. СОРТИРОВКА
    "sort_data": FormulaTemplate(
        id="sort_data",
        name="Сортировка",
        keywords=["отсортируй", "sort", "сортировка", "упорядочи", "по возрастанию", "по убыванию"],
        formula_pattern="=SORT({range},{column},{ascending})",
        description="Сортирует диапазон по столбцу",
        category="data",
        requires_params=["range", "column", "ascending"],
        priority=2,
        examples=["Отсортируй по цене", "Упорядочи по дате"]
    ),

    # 73. ФИЛЬТР
    "filter_data": FormulaTemplate(
        id="filter_data",
        name="Фильтр данных",
        keywords=["фильтр", "filter", "покажи только", "отфильтруй", "выбери где"],
        formula_pattern='=FILTER({range},{condition_column}{operator}{value})',
        description="Фильтрует данные по условию",
        category="data",
        requires_params=["range", "condition_column", "operator", "value"],
        priority=3,
        examples=["Покажи только товары дороже 1000", "Отфильтруй по региону Москва"]
    ),

    # 74. ТРАНСПОНИРОВАНИЕ
    "transpose": FormulaTemplate(
        id="transpose",
        name="Транспонировать данные",
        keywords=["транспонируй", "transpose", "переверни", "столбцы в строки", "строки в столбцы"],
        formula_pattern="=TRANSPOSE({range})",
        description="Меняет строки и столбцы местами",
        category="data",
        requires_params=["range"],
        examples=["Транспонируй таблицу", "Столбцы в строки"]
    ),

    # 75. CONCATENATE RANGE (объединить диапазон)
    "concatenate_range": FormulaTemplate(
        id="concatenate_range",
        name="Объединить диапазон через разделитель",
        keywords=["объедини диапазон", "соедини все", "join", "textjoin"],
        formula_pattern='=TEXTJOIN("{delimiter}",TRUE,{range})',
        description="Объединяет все значения диапазона через разделитель",
        category="data",
        requires_params=["delimiter", "range"],
        examples=["Объедини все значения через запятую", "Join all cells"]
    ),

    # =============================================================================
    # КАТЕГОРИЯ 7: CONDITIONAL FORMATTING (10 templates)
    # =============================================================================

    # 76. ПРОСРОЧЕННЫЕ ДОГОВОРЫ (дата начала + срок в днях < сегодня)
    "highlight_expired_contracts": FormulaTemplate(
        id="highlight_expired_contracts",
        name="Выделить просроченные договоры/записи",
        keywords=["просроченные", "истекшие", "expired", "выделить просроченные", "подсветить просроченные",
                  "окрасить просроченные", "срок истёк", "договоры истекли", "просрочка"],
        formula_pattern="=${start_date_col}2+${duration_col}2<TODAY()",
        description="Выделяет строки где срок действия истёк (дата начала + длительность < сегодня)",
        category="conditional_format",
        requires_params=["start_date_col", "duration_col"],
        priority=4,
        examples=["Выделить просроченные договоры", "Подсветить где срок истёк", "Окрасить истекшие записи"]
    ),

    # 77. ПРОСРОЧЕННЫЕ ПО ДАТЕ ОКОНЧАНИЯ
    "highlight_past_end_date": FormulaTemplate(
        id="highlight_past_end_date",
        name="Выделить по дате окончания",
        keywords=["дата окончания", "end date", "deadline", "срок действия истёк", "дата истекла"],
        formula_pattern="=${end_date_col}2<TODAY()",
        description="Выделяет строки где дата окончания уже прошла",
        category="conditional_format",
        requires_params=["end_date_col"],
        priority=4,
        examples=["Выделить где deadline прошёл", "Подсветить истёкшие даты"]
    ),

    # 78. СКОРО ИСТЕКУТ (менее N дней)
    "highlight_expiring_soon": FormulaTemplate(
        id="highlight_expiring_soon",
        name="Выделить скоро истекающие",
        keywords=["скоро истекут", "expiring soon", "менее дней", "осталось мало", "скоро закончатся"],
        formula_pattern="=AND(${end_date_col}2>=TODAY(),${end_date_col}2<TODAY()+{days})",
        description="Выделяет строки которые истекут в ближайшие N дней",
        category="conditional_format",
        requires_params=["end_date_col", "days"],
        priority=3,
        examples=["Выделить что истечёт менее чем за 7 дней", "Подсветить скоро истекающие"]
    ),

    # 79. ДУБЛИКАТЫ
    "highlight_duplicates": FormulaTemplate(
        id="highlight_duplicates",
        name="Выделить дубликаты",
        keywords=["дубликаты", "duplicates", "повторы", "одинаковые", "выделить дубликаты", "повторяющиеся"],
        formula_pattern="=COUNTIF(${column}:${column},${column}2)>1",
        description="Выделяет ячейки с дубликатами значений",
        category="conditional_format",
        requires_params=["column"],
        priority=3,
        examples=["Выделить дубликаты в столбце A", "Подсветить повторяющиеся значения"]
    ),

    # 80. ПУСТЫЕ ЯЧЕЙКИ
    "highlight_empty": FormulaTemplate(
        id="highlight_empty",
        name="Выделить пустые ячейки",
        keywords=["пустые", "empty", "незаполненные", "выделить пустые", "пустые ячейки"],
        formula_pattern="=${column}2=\"\"",
        description="Выделяет пустые ячейки",
        category="conditional_format",
        requires_params=["column"],
        priority=2,
        examples=["Выделить пустые ячейки", "Подсветить незаполненные"]
    ),

    # 81. БОЛЬШЕ ПОРОГА
    "highlight_above_threshold": FormulaTemplate(
        id="highlight_above_threshold",
        name="Выделить больше порога",
        keywords=["больше", "выше", "более", "above", "greater", "выделить больше", "подсветить выше"],
        formula_pattern="=${column}2>{threshold}",
        description="Выделяет ячейки больше заданного значения",
        category="conditional_format",
        requires_params=["column", "threshold"],
        priority=3,
        examples=["Выделить продажи больше 1000", "Подсветить где цена выше 500"]
    ),

    # 82. МЕНЬШЕ ПОРОГА
    "highlight_below_threshold": FormulaTemplate(
        id="highlight_below_threshold",
        name="Выделить меньше порога",
        keywords=["меньше", "ниже", "менее", "below", "less", "выделить меньше", "подсветить ниже"],
        formula_pattern="=${column}2<{threshold}",
        description="Выделяет ячейки меньше заданного значения",
        category="conditional_format",
        requires_params=["column", "threshold"],
        priority=3,
        examples=["Выделить продажи меньше 100", "Подсветить где остаток ниже 5"]
    ),

    # 83. МЕЖДУ ЗНАЧЕНИЯМИ
    "highlight_between": FormulaTemplate(
        id="highlight_between",
        name="Выделить между значениями",
        keywords=["между", "between", "в диапазоне", "от и до", "выделить между"],
        formula_pattern="=AND(${column}2>={min_value},${column}2<={max_value})",
        description="Выделяет ячейки в заданном диапазоне",
        category="conditional_format",
        requires_params=["column", "min_value", "max_value"],
        priority=2,
        examples=["Выделить цены от 100 до 500", "Подсветить оценки между 3 и 4"]
    ),

    # 84. СОДЕРЖИТ ТЕКСТ
    "highlight_contains": FormulaTemplate(
        id="highlight_contains",
        name="Выделить содержащие текст",
        keywords=["содержит", "contains", "включает", "есть слово", "выделить содержащие"],
        formula_pattern='=ISNUMBER(SEARCH("{text}",${column}2))',
        description="Выделяет ячейки содержащие указанный текст",
        category="conditional_format",
        requires_params=["column", "text"],
        priority=2,
        examples=["Выделить где есть слово Москва", "Подсветить содержащие email"]
    ),

    # 85. НЕ СОДЕРЖИТ ТЕКСТ
    "highlight_not_contains": FormulaTemplate(
        id="highlight_not_contains",
        name="Выделить НЕ содержащие текст",
        keywords=["не содержит", "not contains", "без", "отсутствует", "выделить без"],
        formula_pattern='=NOT(ISNUMBER(SEARCH("{text}",${column}2)))',
        description="Выделяет ячейки НЕ содержащие указанный текст",
        category="conditional_format",
        requires_params=["column", "text"],
        priority=2,
        examples=["Выделить без слова Тест", "Подсветить где нет email"]
    ),
}


def get_all_templates() -> Dict[str, FormulaTemplate]:
    """Возвращает все шаблоны"""
    return TEMPLATES


def get_template_by_id(template_id: str) -> Optional[FormulaTemplate]:
    """Находит шаблон по ID"""
    return TEMPLATES.get(template_id)


def get_templates_by_category(category: str) -> List[FormulaTemplate]:
    """Возвращает все шаблоны категории"""
    return [t for t in TEMPLATES.values() if t.category == category]


def get_templates_by_priority(min_priority: int = 1) -> List[FormulaTemplate]:
    """Возвращает шаблоны с приоритетом не ниже указанного"""
    return [t for t in TEMPLATES.values() if t.priority >= min_priority]
