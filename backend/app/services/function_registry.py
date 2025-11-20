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

            # Filtering Advanced (NEW)
            "filter_multiple": self.filter_multiple,
            "filter_null": self.filter_null,
            "filter_not_null": self.filter_not_null,
            "filter_between": self.filter_between,
            "filter_in_list": self.filter_in_list,
            "filter_not_in_list": self.filter_not_in_list,
            "filter_regex": self.filter_regex,
            "filter_top_n": self.filter_top_n,
            "filter_bottom_n": self.filter_bottom_n,
            "filter_outliers": self.filter_outliers,

            # Вычисления (базовые)
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

            # Вычисления (Math Operations - NEW)
            "calculate_max": self.calculate_max,
            "calculate_min": self.calculate_min,
            "calculate_count": self.calculate_count,
            "calculate_count_all": self.calculate_count_all,
            "calculate_mode": self.calculate_mode,
            "calculate_std": self.calculate_std,
            "calculate_abs": self.calculate_abs,
            "calculate_round": self.calculate_round,
            "calculate_ceiling": self.calculate_ceiling,
            "calculate_floor": self.calculate_floor,
            "calculate_log": self.calculate_log,
            "calculate_power": self.calculate_power,
            "calculate_sqrt": self.calculate_sqrt,
            "calculate_product": self.calculate_product,
            "calculate_ratio": self.calculate_ratio,

            # Группировка и агрегация
            "aggregate_by_group": self.aggregate_by_group,
            "pivot_table": self.pivot_table,
            "top_n_per_group": self.top_n_per_group,

            # Текстовые операции
            "concat_columns": self.concat_columns,
            "replace_text": self.replace_text,
            "trim_whitespace": self.trim_whitespace,

            # Text Operations Advanced (NEW)
            "extract_substring": self.extract_substring,
            "split_column": self.split_column,
            "uppercase": self.uppercase,
            "lowercase": self.lowercase,
            "capitalize": self.capitalize,
            "title_case": self.title_case,
            "text_length": self.text_length,
            "contains_count": self.contains_count,
            "extract_numbers": self.extract_numbers,
            "extract_emails": self.extract_emails,
            "remove_special_chars": self.remove_special_chars,
            "pad_string": self.pad_string,

            # Работа с датами
            "parse_dates": self.parse_dates,
            "date_difference": self.date_difference,
            "filter_by_date_range": self.filter_by_date_range,

            # Date Operations Advanced (NEW)
            "extract_year": self.extract_year,
            "extract_month": self.extract_month,
            "extract_day": self.extract_day,
            "extract_weekday": self.extract_weekday,
            "extract_quarter": self.extract_quarter,
            "add_days": self.add_days,
            "subtract_days": self.subtract_days,
            "start_of_month": self.start_of_month,
            "end_of_month": self.end_of_month,
            "format_date": self.format_date,

            # Продвинутые операции
            "vlookup": self.vlookup,
            "conditional_calculation": self.conditional_calculation,
            "create_bins": self.create_bins,
            "normalize_data": self.normalize_data,

            # Statistical Operations (NEW)
            "calculate_skewness": self.calculate_skewness,
            "calculate_kurtosis": self.calculate_kurtosis,
            "calculate_iqr": self.calculate_iqr,
            "calculate_z_score": self.calculate_z_score,
            "detect_outliers": self.detect_outliers,
            "calculate_quantile": self.calculate_quantile,
            "calculate_covariance": self.calculate_covariance,
            "calculate_mad": self.calculate_mad,

            # Window Functions (NEW)
            "lag_column": self.lag_column,
            "lead_column": self.lead_column,
            "cumulative_max": self.cumulative_max,
            "cumulative_min": self.cumulative_min,
            "moving_average": self.moving_average,
            "ewma": self.ewma,

            # Conditional Logic (NEW)
            "if_then_else": self.if_then_else,
            "case_when": self.case_when,
            "coalesce": self.coalesce,

            # Aggregation Advanced (NEW)
            "count_distinct": self.count_distinct,
            "first_value": self.first_value,
            "last_value": self.last_value,
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
                            "description": """Цвет выделения. ВАЖНО - выбирай цвет на основе смысла запроса:
                            - 'green' (#90EE90) - для положительных/высоких/топовых значений (топ продаж, больше среднего, максимум, лучшие)
                            - 'red' (#FFB6C1) - для негативных/низких/проблемных значений (отмененные заказы, меньше минимума, худшие, ошибки)
                            - 'blue' (#ADD8E6) - для нейтральных/информационных значений (оплаченные заказы, определенный статус)
                            - 'orange' (#FFA500) - для предупреждений или особых случаев
                            - 'yellow' (#FFFF00) - используй ТОЛЬКО если не подходит ни один из вариантов выше
                            Примеры: 'больше 100000'→green, 'отмененные'→red, 'оплаченные'→blue""",
                            "default": "yellow"
                        }
                    },
                    "required": ["column", "operator", "value"]
                }
            },

            {
                "name": "split_data",
                "description": "Разбиение строк по разделителю. ВАЖНО: Поддерживает auto-detect! Используй column='auto' и delimiter='auto' для автоматического определения. Используй для 'разбей данные по ячейкам', 'split data', 'разбей все данные'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для разбиения. Используй 'auto' для автоопределения колонки с разделителями",
                            "default": "auto"
                        },
                        "delimiter": {
                            "type": "string",
                            "description": "Разделитель (|, запятая, точка с запятой и т.д.). Используй 'auto' для автоопределения",
                            "default": "auto"
                        }
                    },
                    "required": []
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
                "description": "Сумма значений в колонке. Используй для 'сумма', 'итого', 'total'. Поддерживает фильтрацию перед вычислением (например: 'сумма продаж в Москве' → column='Сумма', condition={column:'Город', operator:'==', value:'Москва'})",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для суммирования"
                        },
                        "condition": {
                            "type": "object",
                            "description": "Фильтр перед вычислением (опционально). Структура: {column: 'название_колонки', operator: '==' или 'contains' или '>' или '<', value: 'значение'}. Пример: {column: 'Статус', operator: '==', value: 'Оплачен'}",
                            "properties": {
                                "column": {
                                    "type": "string",
                                    "description": "Колонка для фильтрации"
                                },
                                "operator": {
                                    "type": "string",
                                    "description": "Оператор сравнения: '==', '!=', '>', '<', '>=', '<=', 'contains'"
                                },
                                "value": {
                                    "description": "Значение для сравнения (string, number, или boolean)"
                                }
                            },
                            "required": ["column", "operator", "value"]
                        }
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_average",
                "description": "Среднее значение. Используй для 'среднее', 'average', 'mean'. Поддерживает фильтрацию перед вычислением (например: 'средний чек в Москве' → column='Сумма', condition={column:'Город', operator:'==', value:'Москва'})",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для вычисления среднего"
                        },
                        "condition": {
                            "type": "object",
                            "description": "Фильтр перед вычислением (опционально). Структура: {column: 'название_колонки', operator: '==' или 'contains' или '>' или '<', value: 'значение'}. Пример: {column: 'Город', operator: '==', value: 'Москва'}",
                            "properties": {
                                "column": {
                                    "type": "string",
                                    "description": "Колонка для фильтрации"
                                },
                                "operator": {
                                    "type": "string",
                                    "description": "Оператор сравнения: '==', '!=', '>', '<', '>=', '<=', 'contains'"
                                },
                                "value": {
                                    "description": "Значение для сравнения (string, number, или boolean)"
                                }
                            },
                            "required": ["column", "operator", "value"]
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

            # ========== MATH OPERATIONS (NEW) ==========
            {
                "name": "calculate_max",
                "description": "Максимальное значение в колонке. Используй для 'максимум', 'max', 'наибольшее'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для поиска максимума"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_min",
                "description": "Минимальное значение в колонке. Используй для 'минимум', 'min', 'наименьшее'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для поиска минимума"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_count",
                "description": "Количество непустых значений. Используй для 'сколько', 'количество', 'count'. ВАЖНО: 'сколько ЗАКАЗОВ' = COUNT (не SUM!). Поддерживает фильтрацию (например: 'сколько заказов ждут оплаты' → column='Товар', condition={column:'Статус', operator:'contains', value:'Ожидает'})",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для подсчета (обычно та, по которой считаем количество записей)"
                        },
                        "condition": {
                            "type": "object",
                            "description": "Фильтр перед подсчетом (опционально). Структура: {column: 'название_колонки', operator: '==' или 'contains', value: 'значение'}. Пример: {column: 'Статус', operator: 'contains', value: 'Ожидает'}",
                            "properties": {
                                "column": {
                                    "type": "string",
                                    "description": "Колонка для фильтрации"
                                },
                                "operator": {
                                    "type": "string",
                                    "description": "Оператор сравнения: '==', '!=', '>', '<', '>=', '<=', 'contains'"
                                },
                                "value": {
                                    "description": "Значение для сравнения (string, number, или boolean)"
                                }
                            },
                            "required": ["column", "operator", "value"]
                        }
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_count_all",
                "description": "Количество всех строк (включая пустые). Используй для 'сколько всего строк', 'count all'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для подсчета (опционально)"}
                    }
                }
            },

            {
                "name": "calculate_mode",
                "description": "Мода (наиболее частое значение). Используй для 'самое частое', 'мода', 'mode'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для поиска моды"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_std",
                "description": "Стандартное отклонение. Используй для 'стандартное отклонение', 'std', 'standard deviation'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для вычисления"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_abs",
                "description": "Абсолютное значение (модуль). Используй для 'модуль', 'абсолютное значение', 'abs'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для преобразования"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_round",
                "description": "Округление чисел. Используй для 'округли', 'round'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для округления"},
                        "decimals": {"type": "integer", "description": "Количество знаков после запятой", "default": 0}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_ceiling",
                "description": "Округление вверх. Используй для 'округли вверх', 'ceiling'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для округления"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_floor",
                "description": "Округление вниз. Используй для 'округли вниз', 'floor'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для округления"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_log",
                "description": "Логарифм. Используй для 'логарифм', 'log'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для вычисления"},
                        "base": {"type": "number", "description": "Основание логарифма (e, 10, 2, etc.)", "default": 10}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_power",
                "description": "Возведение в степень. Используй для 'в квадрате', 'в степени', 'power'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для возведения в степень"},
                        "exponent": {"type": "number", "description": "Показатель степени"}
                    },
                    "required": ["column", "exponent"]
                }
            },

            {
                "name": "calculate_sqrt",
                "description": "Квадратный корень. Используй для 'корень квадратный', 'sqrt'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для извлечения корня"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_product",
                "description": "Произведение всех значений. Используй для 'произведение', 'product', 'умножить все'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для перемножения"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_ratio",
                "description": "Отношение двух колонок (деление). Используй для 'отношение', 'ratio', 'поделить'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "numerator_column": {"type": "string", "description": "Числитель (колонка)"},
                        "denominator_column": {"type": "string", "description": "Знаменатель (колонка)"}
                    },
                    "required": ["numerator_column", "denominator_column"]
                }
            },

            # ========== FILTERING ADVANCED (NEW) ==========
            {
                "name": "filter_multiple",
                "description": "Фильтрация по множественным условиям (AND/OR). Используй для 'где X и Y', 'где X или Y'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "conditions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "operator": {"type": "string", "enum": ["<", ">", "==", "!=", "<=", ">=", "contains"]},
                                    "value": {"type": ["string", "number"]}
                                }
                            }
                        },
                        "logic": {"type": "string", "enum": ["AND", "OR"], "default": "AND"}
                    },
                    "required": ["conditions"]
                }
            },

            {
                "name": "filter_null",
                "description": "Фильтр только пустых значений. Используй для 'где пусто', 'null values'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для проверки"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "filter_not_null",
                "description": "Фильтр только непустых значений. Используй для 'где не пусто', 'not null'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string", "description": "Колонка для проверки"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "filter_between",
                "description": "Фильтр значений в диапазоне. Используй для 'между X и Y', 'в диапазоне'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "min_value": {"type": "number"},
                        "max_value": {"type": "number"}
                    },
                    "required": ["column", "min_value", "max_value"]
                }
            },

            {
                "name": "filter_in_list",
                "description": "Фильтр значений из списка. Используй для 'где X в списке', 'один из'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "values": {"type": "array", "items": {"type": ["string", "number"]}}
                    },
                    "required": ["column", "values"]
                }
            },

            {
                "name": "filter_not_in_list",
                "description": "Исключить значения из списка. Используй для 'где X не в списке', 'исключить'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "values": {"type": "array", "items": {"type": ["string", "number"]}}
                    },
                    "required": ["column", "values"]
                }
            },

            {
                "name": "filter_regex",
                "description": "Фильтр по регулярному выражению. Используй для сложных паттернов поиска",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "pattern": {"type": "string", "description": "Регулярное выражение"}
                    },
                    "required": ["column", "pattern"]
                }
            },

            {
                "name": "filter_top_n",
                "description": "Топ N значений по колонке. Используй для 'топ 10', 'лучшие N'. ВАЖНО: поддерживает фильтрацию перед отбором топа (например: 'топ 3 самых дорогих оплаченных заказа' → column='Сумма', n=3, condition={column:'Статус', operator:'equals', value:'Оплачен'}). Для 'топ N в Москве' → добавь condition={column:'Город', operator:'equals', value:'Москва'}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для сортировки (например: 'Сумма', 'Дата')"
                        },
                        "n": {
                            "type": "integer",
                            "description": "Количество записей для отбора"
                        },
                        "condition": {
                            "type": "object",
                            "description": "Фильтр перед отбором топ N (опционально). Применяется ДО сортировки и отбора",
                            "properties": {
                                "column": {"type": "string", "description": "Колонка для фильтрации"},
                                "operator": {
                                    "type": "string",
                                    "description": "Оператор: equals, not_equals, contains, greater_than, less_than"
                                },
                                "value": {"description": "Значение для сравнения"}
                            },
                            "required": ["column", "operator", "value"]
                        }
                    },
                    "required": ["column", "n"]
                }
            },

            {
                "name": "filter_bottom_n",
                "description": "Худшие N значений. Используй для 'худшие 10', 'последние N'. ВАЖНО: поддерживает фильтрацию перед отбором (например: '5 самых дешевых оплаченных заказов' → column='Сумма', n=5, condition={column:'Статус', operator:'equals', value:'Оплачен'})",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {
                            "type": "string",
                            "description": "Колонка для сортировки (например: 'Сумма', 'Дата')"
                        },
                        "n": {
                            "type": "integer",
                            "description": "Количество записей для отбора"
                        },
                        "condition": {
                            "type": "object",
                            "description": "Фильтр перед отбором худших N (опционально). Применяется ДО сортировки и отбора",
                            "properties": {
                                "column": {"type": "string", "description": "Колонка для фильтрации"},
                                "operator": {
                                    "type": "string",
                                    "description": "Оператор: equals, not_equals, contains, greater_than, less_than"
                                },
                                "value": {"description": "Значение для сравнения"}
                            },
                            "required": ["column", "operator", "value"]
                        }
                    },
                    "required": ["column", "n"]
                }
            },

            {
                "name": "filter_outliers",
                "description": "Исключить выбросы (outliers). Используй для 'без выбросов', 'remove outliers'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "method": {"type": "string", "enum": ["iqr", "zscore"], "default": "iqr"},
                        "threshold": {"type": "number", "default": 1.5}
                    },
                    "required": ["column"]
                }
            },

            # ========== ГРУППИРОВКА ==========
            {
                "name": "aggregate_by_group",
                "description": "Группировка с агрегацией. ОБЯЗАТЕЛЬНО используй для запросов с 'у каждого', 'для каждого', 'по каждому', 'у всех'. Также для 'сумма по группам', 'количество по группам', 'группировка', 'итого по категориям'. Примеры: 'сколько заказов у каждого менеджера?', 'сумма продаж по городам', 'средний чек для каждого клиента', 'количество у всех'",
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

            # ========== TEXT OPERATIONS ADVANCED (NEW) ==========
            {
                "name": "extract_substring",
                "description": "Извлечь подстроку. Используй для 'возьми первые N символов', 'извлечь часть строки'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "start": {"type": "integer", "description": "Начальная позиция (0-indexed)"},
                        "length": {"type": "integer", "description": "Длина подстроки (опционально)"}
                    },
                    "required": ["column", "start"]
                }
            },

            {
                "name": "split_column",
                "description": "Разбить колонку на несколько по разделителю. Используй для 'раздели на части', 'split by'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "delimiter": {"type": "string", "default": " "},
                        "max_split": {"type": "integer", "default": -1, "description": "Максимум частей (-1 = все)"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "uppercase",
                "description": "Верхний регистр. Используй для 'в верхнем регистре', 'заглавными буквами', 'CAPS'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "lowercase",
                "description": "Нижний регистр. Используй для 'в нижнем регистре', 'маленькими буквами'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "capitalize",
                "description": "Первая буква заглавная, остальные строчные. Используй для 'с заглавной буквы'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "title_case",
                "description": "Title Case - каждое слово с заглавной буквы. Используй для 'Title Case', 'каждое слово заглавное'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "text_length",
                "description": "Длина строки в символах. Используй для 'сколько символов', 'длина текста'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "contains_count",
                "description": "Сколько раз подстрока встречается. Используй для 'сколько раз встречается', 'количество вхождений'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "substring": {"type": "string"}
                    },
                    "required": ["column", "substring"]
                }
            },

            {
                "name": "extract_numbers",
                "description": "Извлечь числа из текста. Используй для 'достань число', 'вытащи цифры'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "extract_emails",
                "description": "Извлечь email адреса. Используй для 'найди email', 'вытащи почту'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "remove_special_chars",
                "description": "Удалить спецсимволы (оставить только буквы, цифры, пробелы). Используй для 'убери спецсимволы', 'только буквы и цифры'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "pad_string",
                "description": "Дополнить строку до указанной длины. Используй для 'дополни до N символов', 'выровняй по длине'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "width": {"type": "integer"},
                        "fillchar": {"type": "string", "default": " "},
                        "side": {"type": "string", "enum": ["left", "right", "center"], "default": "left"}
                    },
                    "required": ["column", "width"]
                }
            },

            # ========== DATE OPERATIONS ADVANCED (NEW) ==========
            {
                "name": "extract_year",
                "description": "Извлечь год из даты. Используй для 'год', 'какой год', 'year'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "extract_month",
                "description": "Извлечь месяц из даты. Используй для 'месяц', 'какой месяц', 'month'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "extract_day",
                "description": "Извлечь день из даты. Используй для 'день', 'какой день', 'day'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "extract_weekday",
                "description": "День недели (Monday, Tuesday, etc.). Используй для 'день недели', 'weekday'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "extract_quarter",
                "description": "Квартал (1-4). Используй для 'квартал', 'Q1/Q2/Q3/Q4', 'quarter'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "add_days",
                "description": "Добавить дни к дате. Используй для 'добавь 30 дней', 'через N дней'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "days": {"type": "integer"}
                    },
                    "required": ["column", "days"]
                }
            },

            {
                "name": "subtract_days",
                "description": "Вычесть дни из даты. Используй для 'вычти 7 дней', 'N дней назад'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "days": {"type": "integer"}
                    },
                    "required": ["column", "days"]
                }
            },

            {
                "name": "start_of_month",
                "description": "Первый день месяца. Используй для 'начало месяца', 'первый день месяца'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "end_of_month",
                "description": "Последний день месяца. Используй для 'конец месяца', 'последний день месяца'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "format_date",
                "description": "Форматировать дату в строку. Используй для 'формат даты', 'преобразуй в формат'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "format_string": {"type": "string", "default": "%Y-%m-%d", "description": "Формат: %Y=год, %m=месяц, %d=день"}
                    },
                    "required": ["column"]
                }
            },

            # ========== STATISTICAL OPERATIONS (NEW) ==========
            {
                "name": "calculate_skewness",
                "description": "Асимметрия распределения (skewness). Используй для 'асимметрия', 'skewness'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_kurtosis",
                "description": "Эксцесс распределения (kurtosis). Используй для 'эксцесс', 'kurtosis'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_iqr",
                "description": "Межквартильный размах (IQR). Используй для 'межквартильный размах', 'IQR'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_z_score",
                "description": "Z-score (стандартизация). Используй для 'z-score', 'стандартизация', 'сколько стандартных отклонений'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "detect_outliers",
                "description": "Обнаружить выбросы (возвращает True/False). Используй для 'найди выбросы', 'какие значения аномальные'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "method": {"type": "string", "enum": ["iqr", "zscore"], "default": "iqr"},
                        "threshold": {"type": "number", "default": 1.5}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "calculate_quantile",
                "description": "Квантиль (любой процентиль). Используй для 'квантиль 0.75', 'перцентиль', 'quantile'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "q": {"type": "number", "description": "Квантиль от 0 до 1 (например 0.5 = медиана)"}
                    },
                    "required": ["column", "q"]
                }
            },

            {
                "name": "calculate_covariance",
                "description": "Ковариация между двумя колонками. Используй для 'ковариация', 'covariance'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column1": {"type": "string"},
                        "column2": {"type": "string"}
                    },
                    "required": ["column1", "column2"]
                }
            },

            {
                "name": "calculate_mad",
                "description": "Среднее абсолютное отклонение (MAD). Используй для 'среднее абсолютное отклонение', 'MAD'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            # ========== WINDOW FUNCTIONS (NEW) ==========
            {
                "name": "lag_column",
                "description": "Предыдущее значение (сдвиг вниз). Используй для 'предыдущее значение', 'значение из прошлой строки', 'lag'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "periods": {"type": "integer", "default": 1, "description": "На сколько строк сдвинуть"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "lead_column",
                "description": "Следующее значение (сдвиг вверх). Используй для 'следующее значение', 'значение из следующей строки', 'lead'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "periods": {"type": "integer", "default": 1}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "cumulative_max",
                "description": "Накопительный максимум. Используй для 'максимум до этой строки', 'cumulative max'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "cumulative_min",
                "description": "Накопительный минимум. Используй для 'минимум до этой строки', 'cumulative min'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "moving_average",
                "description": "Скользящее среднее (moving average). Используй для 'скользящее среднее за N дней', 'moving average'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "window": {"type": "integer", "description": "Размер окна (например, 7 для недели)"}
                    },
                    "required": ["column", "window"]
                }
            },

            {
                "name": "ewma",
                "description": "Экспоненциальное скользящее среднее (EWMA). Используй для 'экспоненциальное среднее', 'EWMA'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "span": {"type": "integer", "default": 10}
                    },
                    "required": ["column"]
                }
            },

            # ========== CONDITIONAL LOGIC (NEW) ==========
            {
                "name": "if_then_else",
                "description": "IF-THEN-ELSE логика. Используй для 'если условие то X иначе Y', 'IF-THEN-ELSE'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "condition_column": {"type": "string"},
                        "operator": {"type": "string", "enum": ["<", ">", "==", "!=", "<=", ">="]},
                        "threshold": {"type": ["string", "number"]},
                        "true_value": {"type": ["string", "number"]},
                        "false_value": {"type": ["string", "number"]}
                    },
                    "required": ["condition_column", "operator", "threshold", "true_value", "false_value"]
                }
            },

            {
                "name": "case_when",
                "description": "CASE WHEN (множественные условия). Используй для 'когда X то Y, когда Z то W', 'CASE WHEN'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "conditions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "operator": {"type": "string"},
                                    "value": {"type": ["string", "number"]},
                                    "then": {"type": ["string", "number"]}
                                }
                            }
                        }
                    },
                    "required": ["conditions"]
                }
            },

            {
                "name": "coalesce",
                "description": "Первое непустое значение из нескольких колонок. Используй для 'первое непустое', 'COALESCE'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "columns": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["columns"]
                }
            },

            # ========== AGGREGATION ADVANCED (NEW) ==========
            {
                "name": "count_distinct",
                "description": "Количество уникальных значений. Используй для 'сколько уникальных', 'COUNT DISTINCT'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "first_value",
                "description": "Первое значение (глобально или по группам). Используй для 'первое значение', 'FIRST_VALUE'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "group_by": {"type": "string", "description": "Группировать по колонке (опционально)"}
                    },
                    "required": ["column"]
                }
            },

            {
                "name": "last_value",
                "description": "Последнее значение (глобально или по группам). Используй для 'последнее значение', 'LAST_VALUE'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "group_by": {"type": "string", "description": "Группировать по колонке (опционально)"}
                    },
                    "required": ["column"]
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
        Примеры: "р.857 765" -> 857765, "100 000" -> 100000, "$1,234.56" -> 1234.56, "12,6" -> 12.6
        """
        def parse_value(val):
            if pd.isna(val):
                return val
            if isinstance(val, (int, float)):
                return val

            # Преобразуем в строку
            val_str = str(val)

            # ИСПРАВЛЕНИЕ: Заменяем запятую на точку для десятичных чисел (европейский формат)
            # Если есть только одна запятая и она между цифрами - это десятичный разделитель
            if ',' in val_str and val_str.count(',') == 1:
                # Проверяем, что это десятичная запятая (не разделитель тысяч)
                parts = val_str.split(',')
                if len(parts) == 2 and len(parts[1].replace(' ', '').replace('.', '')) <= 2:
                    # Максимум 2 цифры после запятой - это десятичный разделитель
                    val_str = val_str.replace(',', '.')

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
            # v7.6.1 FIX: Определяем тип данных (дата или число)
            is_date_comparison = False

            # Проверяем, является ли value датой (формат YYYY-MM-DD или DD-MM-YYYY)
            if isinstance(value, str) and re.match(r'\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4}', value):
                is_date_comparison = True

            if operator in ['<', '>', '<=', '>=']:
                if is_date_comparison:
                    # Конвертируем в datetime для сравнения дат
                    try:
                        column_data = pd.to_datetime(df[column], errors='coerce')
                        value = pd.to_datetime(value, errors='coerce')
                    except:
                        # Fallback to string comparison
                        column_data = df[column]
                else:
                    # Конвертируем в числа для сравнения чисел
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

    def split_data(self, df: pd.DataFrame, column: str = "auto", delimiter: str = "auto") -> pd.DataFrame:
        """
        Разбиение строк по разделителю

        Поддерживает auto-detect:
        - column="auto" → автоматически находит колонку с разделителями
        - delimiter="auto" → автоматически определяет разделитель (|, ,, ;)
        """
        # AUTO-DETECT: Находим колонку с разделителями
        if column == "auto":
            possible_delimiters = ["|", ",", ";", "\t"]
            found = False

            for col in df.columns:
                # Проверяем первые 5 строк на наличие разделителей
                sample = df[col].astype(str).head(5)
                for delim in possible_delimiters:
                    if sample.str.contains(f"\\{delim}" if delim in ["|", "."] else delim, regex=True).any():
                        column = col
                        if delimiter == "auto":
                            delimiter = delim
                        found = True
                        print(f"[SPLIT_DATA] Auto-detected column: '{column}', delimiter: '{delimiter}'")
                        break
                if found:
                    break

            if not found:
                # DEBUG: Показываем первые строки данных
                print(f"[SPLIT_DATA v7.5.5] Не найдена колонка с разделителями")
                print(f"[SPLIT_DATA v7.5.5] Первые строки данных:")
                for col in df.columns[:5]:  # Первые 5 колонок
                    sample = df[col].head(3).tolist()
                    print(f"  - '{col}': {sample}")

                # v7.5.5 FIX: Если разделители не найдены - данные УЖЕ разбиты
                # Возвращаем существующий DataFrame вместо ошибки
                print(f"[SPLIT_DATA v7.5.5] ✅ Данные УЖЕ разбиты по колонкам ({len(df.columns)} колонок)")
                print(f"[SPLIT_DATA v7.5.5] Возвращаем существующие данные для отображения таблицы")
                return df

        # AUTO-DETECT: Определяем разделитель
        if delimiter == "auto":
            possible_delimiters = ["|", ",", ";", "\t"]
            sample = df[column].astype(str).head(5)

            for delim in possible_delimiters:
                if sample.str.contains(f"\\{delim}" if delim in ["|", "."] else delim, regex=True).any():
                    delimiter = delim
                    print(f"[SPLIT_DATA] Auto-detected delimiter: '{delimiter}'")
                    break

            if delimiter == "auto":
                raise ValueError("Не найден разделитель в данных. Укажите delimiter вручную")

        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        # Разбиваем строки по разделителю
        split_result = df[column].astype(str).str.split(delimiter, expand=True)

        # Очищаем пробелы в каждой ячейке
        split_result = split_result.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        # Используем первую строку как заголовки
        headers = split_result.iloc[0].values.tolist()
        headers = [h if h else f"Column_{i+1}" for i, h in enumerate(headers)]  # Пустые заголовки → Column_1, Column_2...

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
            # v7.5.6 FIX: Convert to numeric to handle string numbers from Sheets API
            return pd.to_numeric(filtered_df[column], errors='coerce').sum()

        # v7.5.6 FIX: Convert to numeric to handle string numbers from Sheets API
        return pd.to_numeric(df[column], errors='coerce').sum()

    def calculate_average(self, df: pd.DataFrame, column: str, condition: Optional[Dict] = None) -> float:
        """Среднее значение"""
        if column not in df.columns:
            raise ValueError(f"Колонка '{column}' не найдена")

        if condition:
            filtered_df = self.filter_rows(df, **condition)
            # v7.5.6 FIX: Convert to numeric to handle string numbers from Sheets API
            return pd.to_numeric(filtered_df[column], errors='coerce').mean()

        # v7.5.6 FIX: Convert to numeric to handle string numbers from Sheets API
        return pd.to_numeric(df[column], errors='coerce').mean()

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

    # Math Operations (NEW)
    def calculate_max(self, df: pd.DataFrame, column: str) -> float:
        """Максимальное значение"""
        column = self._find_column(df, column)
        return df[column].max()

    def calculate_min(self, df: pd.DataFrame, column: str) -> float:
        """Минимальное значение"""
        column = self._find_column(df, column)
        return df[column].min()

    def calculate_count(self, df: pd.DataFrame, column: str, condition: Optional[Dict] = None) -> int:
        """Количество непустых значений"""
        column = self._find_column(df, column)

        if condition:
            filtered_df = self.filter_rows(df, **condition)
            return int(filtered_df[column].count())

        return int(df[column].count())

    def calculate_count_all(self, df: pd.DataFrame, column: Optional[str] = None) -> int:
        """Количество всех строк"""
        return len(df)

    def calculate_mode(self, df: pd.DataFrame, column: str) -> Any:
        """Мода (наиболее частое значение)"""
        column = self._find_column(df, column)
        mode_result = df[column].mode()
        return mode_result.iloc[0] if len(mode_result) > 0 else None

    def calculate_std(self, df: pd.DataFrame, column: str) -> float:
        """Стандартное отклонение"""
        column = self._find_column(df, column)
        return df[column].std()

    def calculate_abs(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Абсолютное значение"""
        column = self._find_column(df, column)
        return df[column].abs()

    def calculate_round(self, df: pd.DataFrame, column: str, decimals: int = 0) -> pd.Series:
        """Округление"""
        column = self._find_column(df, column)
        return df[column].round(decimals)

    def calculate_ceiling(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Округление вверх"""
        column = self._find_column(df, column)
        return np.ceil(df[column])

    def calculate_floor(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Округление вниз"""
        column = self._find_column(df, column)
        return np.floor(df[column])

    def calculate_log(self, df: pd.DataFrame, column: str, base: float = 10) -> pd.Series:
        """Логарифм"""
        column = self._find_column(df, column)
        if base == np.e or base == "e":
            return np.log(df[column])
        elif base == 10:
            return np.log10(df[column])
        elif base == 2:
            return np.log2(df[column])
        else:
            return np.log(df[column]) / np.log(base)

    def calculate_power(self, df: pd.DataFrame, column: str, exponent: float) -> pd.Series:
        """Возведение в степень"""
        column = self._find_column(df, column)
        return df[column] ** exponent

    def calculate_sqrt(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Квадратный корень"""
        column = self._find_column(df, column)
        return np.sqrt(df[column])

    def calculate_product(self, df: pd.DataFrame, column: str) -> float:
        """Произведение всех значений"""
        column = self._find_column(df, column)
        return df[column].product()

    def calculate_ratio(self, df: pd.DataFrame, numerator_column: str, denominator_column: str) -> pd.Series:
        """Отношение двух колонок"""
        numerator_column = self._find_column(df, numerator_column)
        denominator_column = self._find_column(df, denominator_column)
        return df[numerator_column] / df[denominator_column]

    # Filtering Advanced (NEW)
    def filter_multiple(self, df: pd.DataFrame, conditions: List[Dict], logic: str = "AND") -> pd.DataFrame:
        """Множественная фильтрация с AND/OR"""
        masks = []
        for cond in conditions:
            column = self._find_column(df, cond["column"])
            operator = cond["operator"]
            value = cond["value"]

            if operator == "contains":
                mask = df[column].astype(str).str.contains(str(value), case=False, na=False)
            else:
                if operator in ['<', '>', '<=', '>=']:
                    column_data = self._parse_numeric_column(df[column])
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

            masks.append(mask)

        if logic == "AND":
            combined_mask = masks[0]
            for mask in masks[1:]:
                combined_mask = combined_mask & mask
        else:  # OR
            combined_mask = masks[0]
            for mask in masks[1:]:
                combined_mask = combined_mask | mask

        return df[combined_mask]

    def filter_null(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Фильтр пустых значений"""
        column = self._find_column(df, column)
        return df[df[column].isnull()]

    def filter_not_null(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Фильтр непустых значений"""
        column = self._find_column(df, column)
        return df[df[column].notnull()]

    def filter_between(self, df: pd.DataFrame, column: str, min_value: float, max_value: float) -> pd.DataFrame:
        """Фильтр значений в диапазоне"""
        column = self._find_column(df, column)
        return df[(df[column] >= min_value) & (df[column] <= max_value)]

    def filter_in_list(self, df: pd.DataFrame, column: str, values: List[Union[str, int, float]]) -> pd.DataFrame:
        """Фильтр значений из списка"""
        column = self._find_column(df, column)
        return df[df[column].isin(values)]

    def filter_not_in_list(self, df: pd.DataFrame, column: str, values: List[Union[str, int, float]]) -> pd.DataFrame:
        """Исключить значения из списка"""
        column = self._find_column(df, column)
        return df[~df[column].isin(values)]

    def filter_regex(self, df: pd.DataFrame, column: str, pattern: str) -> pd.DataFrame:
        """Фильтр по регулярному выражению"""
        column = self._find_column(df, column)
        return df[df[column].astype(str).str.contains(pattern, regex=True, na=False)]

    def filter_top_n(self, df: pd.DataFrame, column: str, n: int, condition: Optional[Dict] = None) -> pd.DataFrame:
        """Топ N значений"""
        column = self._find_column(df, column)

        # v7.8.6 FIX: Apply condition filter BEFORE selecting top N
        # Example: "топ 3 оплаченных заказа" → filter by status FIRST, then get top 3
        if condition:
            df = self.filter_rows(df, **condition)

        # v7.5.7 FIX: Convert to numeric for nlargest to work with string numbers
        df_copy = df.copy()
        df_copy[column] = pd.to_numeric(df_copy[column], errors='coerce')
        return df_copy.nlargest(n, column)

    def filter_bottom_n(self, df: pd.DataFrame, column: str, n: int, condition: Optional[Dict] = None) -> pd.DataFrame:
        """Худшие N значений"""
        column = self._find_column(df, column)

        # v7.8.6 FIX: Apply condition filter BEFORE selecting bottom N
        # Example: "5 самых дешевых оплаченных" → filter by status FIRST, then get bottom 5
        if condition:
            df = self.filter_rows(df, **condition)

        # v7.5.7 FIX: Convert to numeric for nsmallest to work with string numbers
        df_copy = df.copy()
        df_copy[column] = pd.to_numeric(df_copy[column], errors='coerce')
        return df_copy.nsmallest(n, column)

    def filter_outliers(self, df: pd.DataFrame, column: str, method: str = "iqr", threshold: float = 1.5) -> pd.DataFrame:
        """Исключить выбросы"""
        column = self._find_column(df, column)

        if method == "iqr":
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
        elif method == "zscore":
            mean = df[column].mean()
            std = df[column].std()
            z_scores = np.abs((df[column] - mean) / std)
            return df[z_scores < threshold]

        return df

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

    # Text Operations Advanced (NEW)
    def extract_substring(self, df: pd.DataFrame, column: str, start: int, length: Optional[int] = None) -> pd.Series:
        """Извлечь подстроку"""
        column = self._find_column(df, column)
        if length:
            return df[column].astype(str).str[start:start+length]
        return df[column].astype(str).str[start:]

    def split_column(self, df: pd.DataFrame, column: str, delimiter: str = " ", max_split: int = -1) -> pd.DataFrame:
        """Разбить колонку на несколько"""
        column = self._find_column(df, column)
        result_df = df.copy()
        split_df = result_df[column].astype(str).str.split(delimiter, n=max_split, expand=True)
        for i, col in enumerate(split_df.columns):
            result_df[f"{column}_part_{i+1}"] = split_df[col]
        return result_df

    def uppercase(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Верхний регистр"""
        column = self._find_column(df, column)
        return df[column].astype(str).str.upper()

    def lowercase(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Нижний регистр"""
        column = self._find_column(df, column)
        return df[column].astype(str).str.lower()

    def capitalize(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Первая буква заглавная"""
        column = self._find_column(df, column)
        return df[column].astype(str).str.capitalize()

    def title_case(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Title Case"""
        column = self._find_column(df, column)
        return df[column].astype(str).str.title()

    def text_length(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Длина строки"""
        column = self._find_column(df, column)
        return df[column].astype(str).str.len()

    def contains_count(self, df: pd.DataFrame, column: str, substring: str) -> pd.Series:
        """Сколько раз содержится подстрока"""
        column = self._find_column(df, column)
        return df[column].astype(str).str.count(substring)

    def extract_numbers(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Извлечь числа из текста"""
        column = self._find_column(df, column)
        return df[column].astype(str).str.extract(r'(\d+)', expand=False)

    def extract_emails(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Извлечь email"""
        column = self._find_column(df, column)
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return df[column].astype(str).str.extract(f'({email_pattern})', expand=False)

    def remove_special_chars(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Удалить спецсимволы"""
        column = self._find_column(df, column)
        return df[column].astype(str).str.replace(r'[^a-zA-Z0-9\s]', '', regex=True)

    def pad_string(self, df: pd.DataFrame, column: str, width: int, fillchar: str = " ", side: str = "left") -> pd.Series:
        """Дополнить строку до длины"""
        column = self._find_column(df, column)
        if side == "left":
            return df[column].astype(str).str.pad(width, side='left', fillchar=fillchar)
        elif side == "right":
            return df[column].astype(str).str.pad(width, side='right', fillchar=fillchar)
        return df[column].astype(str).str.center(width, fillchar=fillchar)

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

    # Date Operations Advanced (NEW)
    def extract_year(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Извлечь год"""
        column = self._find_column(df, column)
        return pd.to_datetime(df[column]).dt.year

    def extract_month(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Извлечь месяц"""
        column = self._find_column(df, column)
        return pd.to_datetime(df[column]).dt.month

    def extract_day(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Извлечь день"""
        column = self._find_column(df, column)
        return pd.to_datetime(df[column]).dt.day

    def extract_weekday(self, df: pd.DataFrame, column: str) -> pd.Series:
        """День недели"""
        column = self._find_column(df, column)
        return pd.to_datetime(df[column]).dt.day_name()

    def extract_quarter(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Квартал"""
        column = self._find_column(df, column)
        return pd.to_datetime(df[column]).dt.quarter

    def add_days(self, df: pd.DataFrame, column: str, days: int) -> pd.Series:
        """Добавить дни"""
        column = self._find_column(df, column)
        return pd.to_datetime(df[column]) + pd.Timedelta(days=days)

    def subtract_days(self, df: pd.DataFrame, column: str, days: int) -> pd.Series:
        """Вычесть дни"""
        column = self._find_column(df, column)
        return pd.to_datetime(df[column]) - pd.Timedelta(days=days)

    def start_of_month(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Начало месяца"""
        column = self._find_column(df, column)
        dates = pd.to_datetime(df[column])
        return dates - pd.to_timedelta(dates.dt.day - 1, unit='D')

    def end_of_month(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Конец месяца"""
        column = self._find_column(df, column)
        dates = pd.to_datetime(df[column])
        return dates + pd.offsets.MonthEnd(0)

    def format_date(self, df: pd.DataFrame, column: str, format_string: str = "%Y-%m-%d") -> pd.Series:
        """Форматировать дату"""
        column = self._find_column(df, column)
        return pd.to_datetime(df[column]).dt.strftime(format_string)

    # Statistical Operations (NEW)
    def calculate_skewness(self, df: pd.DataFrame, column: str) -> float:
        """Асимметрия"""
        column = self._find_column(df, column)
        return df[column].skew()

    def calculate_kurtosis(self, df: pd.DataFrame, column: str) -> float:
        """Эксцесс"""
        column = self._find_column(df, column)
        return df[column].kurt()

    def calculate_iqr(self, df: pd.DataFrame, column: str) -> float:
        """Межквартильный размах"""
        column = self._find_column(df, column)
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        return Q3 - Q1

    def calculate_z_score(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Z-score"""
        column = self._find_column(df, column)
        mean = df[column].mean()
        std = df[column].std()
        return (df[column] - mean) / std

    def detect_outliers(self, df: pd.DataFrame, column: str, method: str = "iqr", threshold: float = 1.5) -> pd.Series:
        """Обнаружение выбросов (возвращает boolean Series)"""
        column = self._find_column(df, column)
        if method == "iqr":
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            return (df[column] < lower_bound) | (df[column] > upper_bound)
        elif method == "zscore":
            z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
            return z_scores > threshold
        return pd.Series([False] * len(df))

    def calculate_quantile(self, df: pd.DataFrame, column: str, q: float) -> float:
        """Квантиль"""
        column = self._find_column(df, column)
        return df[column].quantile(q)

    def calculate_covariance(self, df: pd.DataFrame, column1: str, column2: str) -> float:
        """Ковариация"""
        column1 = self._find_column(df, column1)
        column2 = self._find_column(df, column2)
        return df[column1].cov(df[column2])

    def calculate_mad(self, df: pd.DataFrame, column: str) -> float:
        """Среднее абсолютное отклонение"""
        column = self._find_column(df, column)
        return df[column].mad()

    # Window Functions (NEW)
    def lag_column(self, df: pd.DataFrame, column: str, periods: int = 1) -> pd.Series:
        """Предыдущее значение (сдвиг вниз)"""
        column = self._find_column(df, column)
        return df[column].shift(periods)

    def lead_column(self, df: pd.DataFrame, column: str, periods: int = 1) -> pd.Series:
        """Следующее значение (сдвиг вверх)"""
        column = self._find_column(df, column)
        return df[column].shift(-periods)

    def cumulative_max(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Накопительный максимум"""
        column = self._find_column(df, column)
        return df[column].cummax()

    def cumulative_min(self, df: pd.DataFrame, column: str) -> pd.Series:
        """Накопительный минимум"""
        column = self._find_column(df, column)
        return df[column].cummin()

    def moving_average(self, df: pd.DataFrame, column: str, window: int) -> pd.Series:
        """Скользящее среднее"""
        column = self._find_column(df, column)
        return df[column].rolling(window=window).mean()

    def ewma(self, df: pd.DataFrame, column: str, span: int = 10) -> pd.Series:
        """Экспоненциальное скользящее среднее"""
        column = self._find_column(df, column)
        return df[column].ewm(span=span).mean()

    # Conditional Logic (NEW)
    def if_then_else(self, df: pd.DataFrame, condition_column: str, operator: str, threshold: Any,
                     true_value: Any, false_value: Any) -> pd.Series:
        """IF-THEN-ELSE логика"""
        condition_column = self._find_column(df, condition_column)
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

    def case_when(self, df: pd.DataFrame, conditions: List[Dict]) -> pd.Series:
        """CASE WHEN (множественные условия)"""
        result = pd.Series([None] * len(df), index=df.index)
        for cond in conditions:
            column = self._find_column(df, cond["column"])
            operator = cond["operator"]
            value = cond["value"]
            then_value = cond["then"]
            ops = {
                '<': lambda x, y: x < y,
                '>': lambda x, y: x > y,
                '==': lambda x, y: x == y,
                '!=': lambda x, y: x != y,
            }
            mask = ops[operator](df[column], value)
            result[mask] = then_value
        return result

    def coalesce(self, df: pd.DataFrame, columns: List[str]) -> pd.Series:
        """Первое непустое значение"""
        result = None
        for col in columns:
            col_name = self._find_column(df, col)
            if result is None:
                result = df[col_name]
            else:
                result = result.fillna(df[col_name])
        return result

    # Aggregation Advanced (NEW)
    def count_distinct(self, df: pd.DataFrame, column: str) -> int:
        """Количество уникальных"""
        column = self._find_column(df, column)
        return int(df[column].nunique())

    def first_value(self, df: pd.DataFrame, column: str, group_by: Optional[str] = None) -> Any:
        """Первое значение"""
        column = self._find_column(df, column)
        if group_by:
            group_by = self._find_column(df, group_by)
            return df.groupby(group_by)[column].first()
        return df[column].iloc[0] if len(df) > 0 else None

    def last_value(self, df: pd.DataFrame, column: str, group_by: Optional[str] = None) -> Any:
        """Последнее значение"""
        column = self._find_column(df, column)
        if group_by:
            group_by = self._find_column(df, group_by)
            return df.groupby(group_by)[column].last()
        return df[column].iloc[-1] if len(df) > 0 else None

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
