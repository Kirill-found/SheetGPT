"""
Function Registry для SheetGPT v7.0.0
Реестр всех доступных функций с OpenAI function calling definitions
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Union
import re
from datetime import datetime, timedelta


class FunctionRegistry:
    """Реестр функций с проверенной реализацией"""

    def __init__(self):
        self.functions = {
            # Базовые операции
            "filter_rows": self.filter_rows,
            "sort_data": self.sort_data,
            "search_rows": self.search_rows,
            "highlight_rows": self.highlight_rows,
            "split_data": self.split_data,
            "remove_duplicates": self.remove_duplicates,
            "fill_missing": self.fill_missing,
            "rename_columns": self.rename_columns,
            "drop_columns": self.drop_columns,
            "reorder_columns": self.reorder_columns,

            # Вычисления
            "calculate_sum": self.calculate_sum,
            "calculate_average": self.calculate_average,
            "calculate_median": self.calculate_median,
            "calculate_percentage": self.calculate_percentage,
            "calculate_growth_rate": self.calculate_growth_rate,
            "calculate_running_total": self.calculate_running_total,
            "calculate_rank": self.calculate_rank,
            "calculate_percentile": self.calculate_percentile,
            "calculate_variance": self.calculate_variance,
            "calculate_correlation": self.calculate_correlation,

            # Группировка и агрегация
            "aggregate_by_group": self.aggregate_by_group,
            "pivot_table": self.pivot_table,
            "top_n_per_group": self.top_n_per_group,

            # Текстовые операции
            "concat_columns": self.concat_columns,
            "replace_text": self.replace_text,
            "trim_whitespace": self.trim_whitespace,

            # Работа с датами
            "parse_dates": self.parse_dates,
            "date_difference": self.date_difference,
            "filter_by_date_range": self.filter_by_date_range,

            # Продвинутые операции
            "vlookup": self.vlookup,
            "conditional_calculation": self.conditional_calculation,
            "create_bins": self.create_bins,
            "normalize_data": self.normalize_data,
        }

    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Возвращает OpenAI function calling definitions"""
        return [
            # ========== БАЗОВЫЕ ОПЕРАЦИИ ==========
            {
                "name": "filter_rows",
                "description": "Фильтрация строк по условию. Используй для запросов типа 'покажи строки где', 'найди где значение больше/меньше'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Название колонки для фильтрации"
                        },
                        "operator": {
                            "type": "string",
                            "enum": ["<", ">", "==", "!=", "<=", ">=", "contains"],
                            "description": "Оператор сравнения"
                        },
                        "value": {
                            "type": ["string", "number"],
                            "description": "Значение для сравнения"
                        }
                    },
                    "required": ["column", "operator", "value"]
                }
            },

            {
                "name": "sort_data",
                "description": "Сортировка данных по одной или нескольким колонкам. Используй для 'отсортируй', 'упорядочь'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список колонок для сортировки"
                        },
                        "ascending": {
                            "type": "boolean",
                            "description": "True для сортировки по возрастанию, False для убывания",
                            "default": True
                        }
                    },
                    "required": ["columns"]
                }
            },

            {
                "name": "search_rows",
                "description": "Поиск строк по текстовому значению. Используй для 'найди строки с', 'где содержится'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для поиска"
                        },
                        "search_term": {
                            "type": "string",
                            "description": "Текст для поиска"
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Учитывать ли регистр",
                            "default": False
                        }
                    },
                    "required": ["column", "search_term"]
                }
            },

            {
                "name": "highlight_rows",
                "description": """Выделение строк цветом по условию. Используй для 'выдели', 'подсвети', 'отметь цветом'.
                ВАЖНО: Поддерживает приблизительные названия колонок (например 'Сумма' найдет 'Заказали на сумму' или 'Сумма продаж').
                Автоматически преобразует строковые числа (например 'р.857 765' -> 857765) для числовых сравнений.
                Примеры: 'выдели где продажи > 100000', 'подсвети строки где сумма меньше 50000'""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для проверки (можно неточное название, система найдет похожую)"
                        },
                        "operator": {
                            "type": "string",
                            "enum": ["<", ">", "==", "!=", "<=", ">="],
                            "description": "Оператор сравнения"
                        },
                        "value": {
                            "type": ["string", "number"],
                            "description": "Значение для сравнения (можно число или строку)"
                        },
                        "color": {
                            "type": "string",
                            "description": "Цвет выделения: yellow, red, green, blue, orange",
                            "default": "yellow"
                        }
                    },
                    "required": ["column", "operator", "value"]
                }
            },

            {
                "name": "split_data",
                "description": "Разбиение строк по разделителю. Используй для 'разбей по запятым', 'split data'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для разбиения"
                        },
                        "delimiter": {
                            "type": "string",
                            "description": "Разделитель (запятая, точка с запятой и т.д.)",
                            "default": ","
                        }
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "remove_duplicates",
                "description": "Удаление дубликатов. Используй для 'удали дубликаты', 'оставь уникальные'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Колонки для проверки дубликатов. Если не указаны, проверяются все"
                        },
                        "keep": {
                            "type": "string",
                            "enum": ["first", "last"],
                            "description": "Какую запись оставить: первую или последнюю",
                            "default": "first"
                        }
                    }
                }
            },

            {
                "name": "fill_missing",
                "description": "Заполнение пустых значений. Используй для 'заполни пустые', 'убери пропуски'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для заполнения"
                        },
                        "method": {
                            "type": "string",
                            "enum": ["ffill", "bfill", "mean", "median", "zero"],
                            "description": "Метод заполнения: ffill (предыдущим), bfill (следующим), mean (средним), median (медианой), zero (нулем)"
                        },
                        "value": {
                            "type": ["string", "number"],
                            "description": "Конкретное значение для заполнения (вместо method)"
                        }
                    },
                    "required": ["column"]
                }
            },

            # ========== ВЫЧИСЛЕНИЯ ==========
            {
                "name": "calculate_sum",
                "description": "Сумма значений в колонке. Используй для 'сумма', 'итого', 'total'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для суммирования"
                        },
                        "condition": {
                            "type": "object",
                            "description": "Условие для фильтрации (опционально)",
                            "properties": {
                                "column": {"type": "string"},
                                "operator": {"type": "string"},
                                "value": {"type": ["string", "number"]}
                            }
                        }
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_average",
                "description": "Среднее значение. Используй для 'среднее', 'average', 'mean'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для вычисления среднего"
                        },
                        "condition": {
                            "type": "object",
                            "description": "Условие для фильтрации (опционально)"
                        }
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_median",
                "description": "Медиана (срединное значение). Используй для 'медиана', 'median'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для вычисления медианы"
                        }
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_percentage",
                "description": "Процент от общей суммы. Используй для 'процент от общей', 'доля в процентах'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка со значениями"
                        },
                        "total_column": {
                            "type": "string",
                            "description": "Колонка с общей суммой (опционально, если не указано - сумма всей колонки)"
                        }
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_rank",
                "description": "Ранжирование значений. Используй для 'ранг', 'место', 'rank'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для ранжирования"
                        },
                        "ascending": {
                            "type": "boolean",
                            "description": "True - меньшие значения получают меньший ранг, False - наоборот",
                            "default": False
                        },
                        "method": {
                            "type": "string",
                            "enum": ["min", "max", "dense", "average"],
                            "description": "Метод обработки одинаковых значений",
                            "default": "min"
                        }
                    },
                    "required": ["column"]
                }
            },

            # ========== ГРУППИРОВКА ==========
            {
                "name": "aggregate_by_group",
                "description": "Группировка с агрегацией. Используй для 'сумма по группам', 'группировка', 'итого по категориям'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "group_by": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Колонки для группировки"
                        },
                        "agg_column": {
                            "type": "string",
                            "description": "Колонка для агрегации"
                        },
                        "agg_func": {
                            "type": "string",
                            "enum": ["sum", "mean", "count", "min", "max", "median", "std"],
                            "description": "Функция агрегации"
                        }
                    },
                    "required": ["group_by", "agg_column", "agg_func"]
                }
            },

            {
                "name": "pivot_table",
                "description": "Сводная таблица. Используй для 'сводная таблица', 'pivot', 'кросс-таблица'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Колонки для строк"
                        },
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Колонки для столбцов"
                        },
                        "values": {
                            "type": "string",
                            "description": "Колонка со значениями"
                        },
                        "aggfunc": {
                            "type": "string",
                            "enum": ["sum", "mean", "count", "min", "max"],
                            "description": "Функция агрегации",
                            "default": "sum"
                        }
                    },
                    "required": ["index", "columns", "values"]
                }
            },

            {
                "name": "top_n_per_group",
                "description": "Топ N в каждой группе. Используй для 'топ 3 в каждой категории', 'лучшие по группам'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "group_by": {
                            "type": "string",
                            "description": "Колонка для группировки"
                        },
                        "sort_column": {
                            "type": "string",
                            "description": "Колонка для сортировки"
                        },
                        "n": {
                            "type": "integer",
                            "description": "Количество элементов в топе"
                        },
                        "ascending": {
                            "type": "boolean",
                            "description": "False для топ (наибольшие), True для худших (наименьшие)",
                            "default": False
                        }
                    },
                    "required": ["group_by", "sort_column", "n"]
                }
            },

            # ========== ПРОДВИНУТЫЕ ==========
            {
                "name": "vlookup",
                "description": "Аналог VLOOKUP Excel. Используй для 'найди значение по ключу', 'подтяни данные'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lookup_value": {
                            "type": ["string", "number"],
                            "description": "Значение для поиска"
                        },
                        "lookup_column": {
                            "type": "string",
                            "description": "Колонка для поиска"
                        },
                        "return_column": {
                            "type": "string",
                            "description": "Колонка для возврата значения"
                        }
                    },
                    "required": ["lookup_value", "lookup_column", "return_column"]
                }
            },

            {
                "name": "create_bins",
                "description": "Создание категорий из числовых значений. Используй для 'раздели на категории', 'группировка диапазонов'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для биннинга"
                        },
                        "bins": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Границы интервалов, например [0, 50000, 100000, 200000]"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Названия категорий, например ['Низкие', 'Средние', 'Высокие']"
                        }
                    },
                    "required": ["column", "bins"]
                }
            },
        ]

    def execute(self, func_name: str, df: pd.DataFrame, **params) -> Dict[str, Any]:
        """Выполнить функцию"""
        try:
            if func_name not in self.functions:
                return {
                    "success": False,
                    "error": f"Функция {func_name} не найдена"
                }

            func = self.functions[func_name]
            result = func(df, **params)

            return {
                "success": True,
                "result": result,
                "function_used": func_name,
                "parameters": params
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "function_used": func_name,
                "parameters": params
            }

    # ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

    def _find_column(self, df: pd.DataFrame, column_name: str) -> str:
        """
        Умный поиск колонки: если точное совпадение не найдено, ищет похожую
        Например: "Сумма" найдет "Заказали на сумму" или "Сумма продаж"
        """
        # Точное совпадение
        if column_name in df.columns:
            return column_name

        # Case-insensitive поиск
        for col in df.columns:
            if col.lower() == column_name.lower():
                return col

        # Частичное совпадение (колонка содержит искомое слово)
        column_lower = column_name.lower()
        matches = [col for col in df.columns if column_lower in col.lower()]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Если несколько совпадений, выбираем самое короткое (наиболее точное)
            return min(matches, key=len)

        # Обратное совпадение (искомое слово содержит название колонки)
        reverse_matches = [col for col in df.columns if col.lower() in column_lower]
        if reverse_matches:
            return max(reverse_matches, key=len)

        # Не найдено - возвращаем исходное название для ошибки
        raise ValueError(f"Колонка '{column_name}' не найдена. Доступные: {', '.join(df.columns)}")

    def _parse_numeric_column(self, series: pd.Series) -> pd.Series:
        """
        Преобразует строковые числа в numeric
        Примеры: "р.857 765" -> 857765, "100 000" -> 100000, "$1,234.56" -> 1234.56
        """
        def parse_value(val):
            if pd.isna(val):
                return val
            if isinstance(val, (int, float)):
                return val

            # Преобразуем в строку
            val_str = str(val)

            # Убираем все кроме цифр, точки и минуса
            cleaned = re.sub(r'[^\d.-]', '', val_str)

            try:
                # Пытаемся преобразовать в float
                return float(cleaned) if cleaned else 0
            except:
                # Если не получилось, возвращаем исходное значение
                return val

        return series.apply(parse_value)

    # ========== РЕАЛИЗАЦИЯ ФУНКЦИЙ ==========

    # Базовые операции
    def filter_rows(self, df: pd.DataFrame, column: str, operator: str, value: Union[str, int, float]) -> pd.DataFrame:
        """Фильтрация строк с умным поиском колонок и преобразованием строковых чисел"""
        # Умный поиск колонки
        column = self._find_column(df, column)

        if operator == "contains":
            mask = df[column].astype(str).str.contains(str(value), case=False, na=False)
        else:
            # Для числовых операторов пытаемся преобразовать колонку в числа
            if operator in ['<', '>', '<=', '>=']:
                column_data = self._parse_numeric_column(df[column])
                # Преобразуем value тоже, если это строка
                if isinstance(value, str):
                    value = float(re.sub(r'[^\d.-]', '', value)) if value else 0
            else:
                column_data = df[column]

            ops = {
                '<': lambda x, y: x < y,
                '>': lambda x, y: x > y,
                '==': lambda x, y: x == y,
                '!=': lambda x, y: x != y,
                '<=': lambda x, y: x <= y,
                '>=': lambda x, y: x >= y,
            }
            mask = ops[operator](column_data, value)

        return df[mask]

    def sort_data(self, df: pd.DataFrame, columns: List[str], ascending: bool = True) -> pd.DataFrame:
        """Сортировка данных"""
        for col in columns:
            if col not in df.columns:
                raise ValueError(f"Колонка '{col}' не найдена")

        return df.sort_values(by=columns, ascending=ascending)

    def search_rows(self, df: pd.DataFrame, column: str, search_term: str, case_sensitive: bool = False) -> pd.DataFrame:
        """Поиск строк"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        mask = df[column].astype(str).str.contains(search_term, case=case_sensitive, na=False)
        return df[mask]

    def highlight_rows(self, df: pd.DataFrame, column: str, operator: str, value: Union[str, int, float], color: str = "yellow") -> Dict[str, Any]:
        """Выделение строк с умным поиском колонок и преобразованием строковых чисел"""
        # Умный поиск колонки
        column = self._find_column(df, column)

        # Для числовых операторов пытаемся преобразовать колонку в числа
        if operator in ['<', '>', '<=', '>=']:
            column_data = self._parse_numeric_column(df[column])
            # Преобразуем value тоже, если это строка
            if isinstance(value, str):
                value = float(re.sub(r'[^\d.-]', '', value)) if value else 0
        else:
            column_data = df[column]

        ops = {
            '<': lambda x, y: x < y,
            '>': lambda x, y: x > y,
            '==': lambda x, y: x == y,
            '!=': lambda x, y: x != y,
            '<=': lambda x, y: x <= y,
            '>=': lambda x, y: x >= y,
        }

        mask = ops[operator](column_data, value)
        rows = df[mask].index.tolist()

        # Преобразуем в 1-based index для Google Sheets (строка 1 = заголовки, данные с 2)
        rows_1based = [r + 2 for r in rows]  # +2 потому что: +1 для pandas index -> 1-based, +1 для заголовков

        return {
            "highlight_rows": rows_1based,
            "highlight_color": color,
            "message": f"Выделено {len(rows)} строк где {column} {operator} {value}, цвет: {color}"
        }

    def split_data(self, df: pd.DataFrame, column: str, delimiter: str = ",") -> pd.DataFrame:
        """Разбиение строк по разделителю"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        # Разбиваем первую строку чтобы получить заголовки
        split_result = df[column].str.split(delimiter, expand=True)

        # Используем первую строку как заголовки
        headers = split_result.iloc[0].values.tolist()

        # Остальные строки - данные
        data_rows = split_result.iloc[1:].values.tolist()

        # Создаем новый DataFrame
        result_df = pd.DataFrame(data_rows, columns=headers)

        return result_df

    def remove_duplicates(self, df: pd.DataFrame, columns: Optional[List[str]] = None, keep: str = "first") -> pd.DataFrame:
        """Удаление дубликатов"""
        if columns:
            for col in columns:
                if col not in df.columns:
                    raise ValueError(f"Колонка '{col}' не найдена")

        return df.drop_duplicates(subset=columns, keep=keep)

    def fill_missing(self, df: pd.DataFrame, column: str, method: Optional[str] = None, value: Optional[Union[str, int, float]] = None) -> pd.DataFrame:
        """Заполнение пустых значений"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        result_df = df.copy()

        if value is not None:
            result_df[column] = result_df[column].fillna(value)
        elif method == "ffill":
            result_df[column] = result_df[column].fillna(method='ffill')
        elif method == "bfill":
            result_df[column] = result_df[column].fillna(method='bfill')
        elif method == "mean":
            result_df[column] = result_df[column].fillna(result_df[column].mean())
        elif method == "median":
            result_df[column] = result_df[column].fillna(result_df[column].median())
        elif method == "zero":
            result_df[column] = result_df[column].fillna(0)

        return result_df

    def rename_columns(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """Переименование колонок"""
        return df.rename(columns=mapping)

    def drop_columns(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """Удаление колонок"""
        return df.drop(columns=columns, errors='ignore')

    def reorder_columns(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """Изменение порядка колонок"""
        # Добавляем колонки которых нет в новом порядке
        remaining = [c for c in df.columns if c not in columns]
        new_order = columns + remaining
        return df[new_order]

    # Вычисления
    def calculate_sum(self, df: pd.DataFrame, column: str, condition: Optional[Dict] = None) -> float:
        """Сумма значений"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        if condition:
            filtered_df = self.filter_rows(df, **condition)
            return filtered_df[column].sum()

        return df[column].sum()

    def calculate_average(self, df: pd.DataFrame, column: str, condition: Optional[Dict] = None) -> float:
        """Среднее значение"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        if condition:
            filtered_df = self.filter_rows(df, **condition)
            return filtered_df[column].mean()

        return df[column].mean()

    def calculate_median(self, df: pd.DataFrame, column: str) -> float:
        """Медиана"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        return df[column].median()

    def calculate_percentage(self, df: pd.DataFrame, column: str, total_column: Optional[str] = None) -> pd.Series:
        """Процент от общей суммы"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        if total_column and total_column in df.columns:
            total = df[total_column].sum()
        else:
            total = df[column].sum()

        return (df[column] / total * 100).round(2)

    def calculate_growth_rate(self, df: pd.DataFrame, column: str, date_column: str, period: str = "MoM") -> pd.DataFrame:
        """Темп роста"""
        result_df = df.copy()
        result_df[f'{column}_growth'] = df[column].pct_change() * 100
        return result_df

    def calculate_running_total(self, df: pd.DataFrame, column: str, sort_by: Optional[str] = None) -> pd.Series:
        """Накопительная сумма"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        if sort_by and sort_by in df.columns:
            df_sorted = df.sort_values(by=sort_by)
            return df_sorted[column].cumsum()

        return df[column].cumsum()

    def calculate_rank(self, df: pd.DataFrame, column: str, ascending: bool = False, method: str = "min") -> pd.Series:
        """Ранжирование"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        return df[column].rank(ascending=ascending, method=method)

    def calculate_percentile(self, df: pd.DataFrame, column: str, percentile: int = 50) -> float:
        """Процентиль"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        return df[column].quantile(percentile / 100)

    def calculate_variance(self, df: pd.DataFrame, column: str) -> Dict[str, float]:
        """Дисперсия и стандартное отклонение"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        return {
            "variance": df[column].var(),
            "std": df[column].std()
        }

    def calculate_correlation(self, df: pd.DataFrame, column1: str, column2: str) -> float:
        """Корреляция между колонками"""
        if column1 not in df.columns or column2 not in df.columns:
            raise ValueError("Одна или обе колонки не найдены")

        return df[column1].corr(df[column2])

    # Группировка
    def aggregate_by_group(self, df: pd.DataFrame, group_by: List[str], agg_column: str, agg_func: str) -> pd.DataFrame:
        """Группировка с агрегацией"""
        for col in group_by:
            if col not in df.columns:
                raise ValueError(f"Колонка '{col}' не найдена")

        if agg_column not in df.columns:
            raise ValueError(f"Колонка '{agg_column}' не найдена")

        return df.groupby(group_by)[agg_column].agg(agg_func).reset_index()

    def pivot_table(self, df: pd.DataFrame, index: List[str], columns: List[str], values: str, aggfunc: str = "sum") -> pd.DataFrame:
        """Сводная таблица"""
        return pd.pivot_table(df, values=values, index=index, columns=columns, aggfunc=aggfunc, fill_value=0)

    def top_n_per_group(self, df: pd.DataFrame, group_by: str, sort_column: str, n: int, ascending: bool = False) -> pd.DataFrame:
        """Топ N в каждой группе"""
        if group_by not in df.columns or sort_column not in df.columns:
            raise ValueError("Колонка не найдена")

        return df.groupby(group_by, group_keys=False).apply(
            lambda x: x.nlargest(n, sort_column) if not ascending else x.nsmallest(n, sort_column)
        ).reset_index(drop=True)

    # Текстовые операции
    def concat_columns(self, df: pd.DataFrame, columns: List[str], separator: str = " ") -> pd.Series:
        """Объединение колонок"""
        for col in columns:
            if col not in df.columns:
                raise ValueError(f"Колонка '{col}' не найдена")

        return df[columns].astype(str).agg(separator.join, axis=1)

    def replace_text(self, df: pd.DataFrame, column: str, old: str, new: str, regex: bool = False) -> pd.DataFrame:
        """Замена текста"""
        result_df = df.copy()
        result_df[column] = result_df[column].str.replace(old, new, regex=regex)
        return result_df

    def trim_whitespace(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """Удаление пробелов"""
        result_df = df.copy()
        for col in columns:
            if col in df.columns:
                result_df[col] = result_df[col].str.strip()
        return result_df

    # Работа с датами
    def parse_dates(self, df: pd.DataFrame, column: str, format: Optional[str] = None) -> pd.DataFrame:
        """Парсинг дат"""
        result_df = df.copy()
        result_df[column] = pd.to_datetime(result_df[column], format=format, errors='coerce')
        return result_df

    def date_difference(self, df: pd.DataFrame, date_column1: str, date_column2: str, unit: str = "days") -> pd.Series:
        """Разница между датами"""
        diff = df[date_column1] - df[date_column2]

        if unit == "days":
            return diff.dt.days
        elif unit == "hours":
            return diff.dt.total_seconds() / 3600
        elif unit == "minutes":
            return diff.dt.total_seconds() / 60

        return diff

    def filter_by_date_range(self, df: pd.DataFrame, date_column: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Фильтрация по диапазону дат"""
        mask = (df[date_column] >= start_date) & (df[date_column] <= end_date)
        return df[mask]

    # Продвинутые операции
    def vlookup(self, df: pd.DataFrame, lookup_value: Union[str, int, float], lookup_column: str, return_column: str) -> Any:
        """VLOOKUP"""
        if lookup_column not in df.columns or return_column not in df.columns:
            raise ValueError("Колонка не найдена")

        mask = df[lookup_column] == lookup_value
        result = df.loc[mask, return_column]

        if len(result) == 0:
            return None

        return result.iloc[0]

    def conditional_calculation(self, df: pd.DataFrame, condition_column: str, operator: str, threshold: Union[str, int, float],
                                true_value: Union[str, int, float], false_value: Union[str, int, float]) -> pd.Series:
        """Условные вычисления"""
        ops = {
            '<': lambda x, y: x < y,
            '>': lambda x, y: x > y,
            '==': lambda x, y: x == y,
            '!=': lambda x, y: x != y,
            '<=': lambda x, y: x <= y,
            '>=': lambda x, y: x >= y,
        }

        mask = ops[operator](df[condition_column], threshold)
        return mask.map({True: true_value, False: false_value})

    def create_bins(self, df: pd.DataFrame, column: str, bins: List[float], labels: Optional[List[str]] = None) -> pd.Series:
        """Создание категорий"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        if labels is None:
            labels = [f"Группа {i+1}" for i in range(len(bins)-1)]

        return pd.cut(df[column], bins=bins, labels=labels)

    def normalize_data(self, df: pd.DataFrame, column: str, method: str = "minmax") -> pd.Series:
        """Нормализация данных"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        if method == "minmax":
            min_val = df[column].min()
            max_val = df[column].max()
            return (df[column] - min_val) / (max_val - min_val)
        elif method == "zscore":
            mean = df[column].mean()
            std = df[column].std()
            return (df[column] - mean) / std

        return df[column]
