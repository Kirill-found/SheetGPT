"""
Schema Extractor v1.0.0 - Schema-Aware Processing для SheetGPT

Автоматически определяет:
- Типы данных колонок (numeric, text, date, category, boolean)
- Уникальные значения для категориальных колонок
- Статистику для числовых колонок
- Форматы дат

Это позволяет LLM точно понимать структуру данных БЕЗ угадывания.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import re


class SchemaExtractor:
    """
    Извлекает схему данных из DataFrame для передачи в LLM.

    Преимущества:
    - LLM знает точные названия колонок (нет ошибок fuzzy matching)
    - LLM знает типы данных (нет ошибок преобразования)
    - LLM знает возможные значения (для фильтрации)
    """

    # Лимиты для оптимизации токенов
    MAX_UNIQUE_VALUES = 10  # Макс. уникальных значений для категории
    MAX_SAMPLE_VALUES = 5   # Макс. примеров значений

    def extract_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Извлекает полную схему DataFrame.

        Returns:
            {
                "row_count": 100,
                "column_count": 5,
                "columns": [
                    {
                        "name": "Менеджер",
                        "type": "category",
                        "unique_count": 5,
                        "unique_values": ["Иванов", "Петров", ...],
                        "nullable": False
                    },
                    {
                        "name": "Сумма продаж",
                        "type": "numeric",
                        "min": 1000,
                        "max": 500000,
                        "mean": 50000,
                        "nullable": True
                    },
                    ...
                ]
            }
        """
        schema = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": []
        }

        for col in df.columns:
            col_schema = self._extract_column_schema(df, col)
            schema["columns"].append(col_schema)

        return schema

    def _extract_column_schema(self, df: pd.DataFrame, column: str) -> Dict[str, Any]:
        """Извлекает схему одной колонки."""
        series = df[column]

        # Базовая информация
        col_schema = {
            "name": column,
            "nullable": series.isna().any(),
            "null_count": int(series.isna().sum())
        }

        # Определяем тип данных
        col_type = self._detect_column_type(series)
        col_schema["type"] = col_type

        # Дополнительная информация в зависимости от типа
        if col_type == "numeric":
            col_schema.update(self._extract_numeric_stats(series))
        elif col_type == "category":
            col_schema.update(self._extract_category_stats(series))
        elif col_type == "date":
            col_schema.update(self._extract_date_stats(series))
        elif col_type == "boolean":
            col_schema.update(self._extract_boolean_stats(series))
        elif col_type == "text":
            col_schema.update(self._extract_text_stats(series))

        return col_schema

    def _detect_column_type(self, series: pd.Series) -> str:
        """
        Определяет тип колонки:
        - numeric: числа (int, float)
        - category: ограниченный набор значений (<= 20 уникальных)
        - date: даты
        - boolean: True/False, Да/Нет
        - text: произвольный текст
        """
        # Пропускаем NaN для анализа
        non_null = series.dropna()

        if len(non_null) == 0:
            return "empty"

        # Проверка на numeric
        if pd.api.types.is_numeric_dtype(series):
            return "numeric"

        # Пробуем конвертировать в числа
        try:
            converted = pd.to_numeric(non_null, errors='coerce')
            if converted.notna().sum() > len(non_null) * 0.8:
                return "numeric"
        except:
            pass

        # Проверка на boolean
        unique_lower = set(str(v).lower().strip() for v in non_null.unique())
        boolean_values = {'true', 'false', 'да', 'нет', 'yes', 'no', '1', '0', 'истина', 'ложь'}
        if unique_lower.issubset(boolean_values) and len(unique_lower) <= 3:
            return "boolean"

        # Проверка на дату
        if self._is_date_column(non_null):
            return "date"

        # Проверка на категорию (мало уникальных значений)
        unique_ratio = len(non_null.unique()) / len(non_null)
        if unique_ratio < 0.3 or len(non_null.unique()) <= 20:
            return "category"

        return "text"

    def _is_date_column(self, series: pd.Series) -> bool:
        """Проверяет, является ли колонка датой."""
        if pd.api.types.is_datetime64_any_dtype(series):
            return True

        # Пробуем распарсить как дату
        sample = series.head(10)
        date_patterns = [
            r'\d{2}[./]\d{2}[./]\d{4}',  # DD.MM.YYYY or DD/MM/YYYY
            r'\d{4}[.-]\d{2}[.-]\d{2}',  # YYYY-MM-DD
            r'\d{2}[.-]\d{2}[.-]\d{2}',  # DD-MM-YY
        ]

        matches = 0
        for val in sample:
            val_str = str(val)
            for pattern in date_patterns:
                if re.match(pattern, val_str):
                    matches += 1
                    break

        return matches >= len(sample) * 0.7

    def _extract_numeric_stats(self, series: pd.Series) -> Dict[str, Any]:
        """Статистика для числовой колонки."""
        # Конвертируем в числа если нужно
        if not pd.api.types.is_numeric_dtype(series):
            series = pd.to_numeric(series, errors='coerce')

        non_null = series.dropna()

        if len(non_null) == 0:
            return {"min": None, "max": None, "mean": None}

        return {
            "min": float(non_null.min()),
            "max": float(non_null.max()),
            "mean": round(float(non_null.mean()), 2),
            "median": round(float(non_null.median()), 2),
            "is_integer": bool(non_null.apply(lambda x: x == int(x) if pd.notna(x) else True).all()),
            "sample_values": [float(v) for v in non_null.head(self.MAX_SAMPLE_VALUES).tolist()]
        }

    def _extract_category_stats(self, series: pd.Series) -> Dict[str, Any]:
        """Статистика для категориальной колонки."""
        value_counts = series.value_counts()
        unique_values = value_counts.index.tolist()

        # Ограничиваем количество уникальных значений
        if len(unique_values) > self.MAX_UNIQUE_VALUES:
            top_values = unique_values[:self.MAX_UNIQUE_VALUES]
            return {
                "unique_count": len(unique_values),
                "unique_values": top_values,
                "has_more_values": True,
                "top_value": str(unique_values[0]),
                "top_value_count": int(value_counts.iloc[0])
            }

        return {
            "unique_count": len(unique_values),
            "unique_values": [str(v) for v in unique_values],
            "has_more_values": False
        }

    def _extract_date_stats(self, series: pd.Series) -> Dict[str, Any]:
        """Статистика для колонки с датами."""
        try:
            dates = pd.to_datetime(series, errors='coerce')
            non_null = dates.dropna()

            if len(non_null) == 0:
                return {"date_format": "unknown"}

            return {
                "min_date": non_null.min().strftime("%Y-%m-%d"),
                "max_date": non_null.max().strftime("%Y-%m-%d"),
                "date_format": self._detect_date_format(series),
                "sample_values": [str(v) for v in series.head(3).tolist()]
            }
        except:
            return {"date_format": "unknown"}

    def _detect_date_format(self, series: pd.Series) -> str:
        """Определяет формат даты."""
        sample = str(series.dropna().iloc[0]) if len(series.dropna()) > 0 else ""

        if re.match(r'\d{2}\.\d{2}\.\d{4}', sample):
            return "DD.MM.YYYY"
        elif re.match(r'\d{2}/\d{2}/\d{4}', sample):
            return "DD/MM/YYYY"
        elif re.match(r'\d{4}-\d{2}-\d{2}', sample):
            return "YYYY-MM-DD"
        else:
            return "unknown"

    def _extract_boolean_stats(self, series: pd.Series) -> Dict[str, Any]:
        """Статистика для булевой колонки."""
        value_counts = series.value_counts()
        return {
            "true_count": int(value_counts.get(True, value_counts.get('Да', value_counts.get('да', 0)))),
            "false_count": int(value_counts.get(False, value_counts.get('Нет', value_counts.get('нет', 0)))),
            "unique_values": [str(v) for v in series.unique().tolist()]
        }

    def _extract_text_stats(self, series: pd.Series) -> Dict[str, Any]:
        """Статистика для текстовой колонки."""
        non_null = series.dropna()

        if len(non_null) == 0:
            return {}

        lengths = non_null.astype(str).str.len()

        return {
            "avg_length": round(float(lengths.mean()), 1),
            "max_length": int(lengths.max()),
            "sample_values": [str(v)[:50] for v in non_null.head(3).tolist()]
        }

    def schema_to_prompt(self, schema: Dict[str, Any]) -> str:
        """
        Конвертирует схему в текст для промпта LLM.
        Оптимизировано для минимального количества токенов.
        """
        lines = [
            f"Таблица: {schema['row_count']} строк × {schema['column_count']} колонок",
            "",
            "Колонки:"
        ]

        for col in schema["columns"]:
            col_desc = self._column_to_prompt(col)
            lines.append(f"  • {col_desc}")

        return "\n".join(lines)

    def _column_to_prompt(self, col: Dict[str, Any]) -> str:
        """Форматирует одну колонку для промпта."""
        name = col["name"]
        col_type = col["type"]

        if col_type == "numeric":
            if col.get("is_integer"):
                return f'"{name}" (число, {col["min"]}-{col["max"]})'
            else:
                return f'"{name}" (число, {col["min"]:.0f}-{col["max"]:.0f}, среднее {col["mean"]:.0f})'

        elif col_type == "category":
            values = col.get("unique_values", [])
            if len(values) <= 5:
                values_str = ", ".join(f'"{v}"' for v in values)
                return f'"{name}" (категория: {values_str})'
            else:
                values_str = ", ".join(f'"{v}"' for v in values[:5])
                return f'"{name}" (категория: {values_str}... +{len(values)-5} ещё)'

        elif col_type == "date":
            fmt = col.get("date_format", "unknown")
            return f'"{name}" (дата, формат {fmt}, {col.get("min_date", "?")} - {col.get("max_date", "?")})'

        elif col_type == "boolean":
            return f'"{name}" (да/нет)'

        else:
            return f'"{name}" (текст)'


# Singleton instance
_schema_extractor = None

def get_schema_extractor() -> SchemaExtractor:
    """Возвращает singleton instance SchemaExtractor."""
    global _schema_extractor
    if _schema_extractor is None:
        _schema_extractor = SchemaExtractor()
    return _schema_extractor
