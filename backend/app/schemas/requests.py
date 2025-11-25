from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Any
import re


class FormulaRequest(BaseModel):
    """Запрос на генерацию формулы с улучшенной валидацией"""
    query: str = Field(..., min_length=1, max_length=2000, description="Запрос пользователя на естественном языке")
    column_names: List[str] = Field(..., min_length=1, max_length=100, description="Названия колонок в таблице")
    sheet_data: Optional[List[List[Any]]] = Field(None, description="Первые 5 строк для контекста")
    history: Optional[List[dict]] = Field(None, max_length=50, description="История предыдущих действий для контекста")
    selected_range: Optional[str] = Field(None, description="Выделенный диапазон (например 'H5:H17')")
    active_cell: Optional[str] = Field(None, description="Активная ячейка (например 'H5')")
    conversation_id: Optional[str] = Field(None, max_length=100, description="ID разговора для поддержки контекстных запросов")
    custom_context: Optional[str] = Field(None, max_length=2000, description="Персонализированная роль AI (например, 'Ты финансовый директор...')")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Валидация и очистка запроса"""
        # Убираем лишние пробелы
        v = ' '.join(v.split())

        # Проверяем на пустой запрос после очистки
        if not v.strip():
            raise ValueError('Запрос не может быть пустым')

        # Проверяем минимальную длину осмысленного запроса
        if len(v.strip()) < 2:
            raise ValueError('Запрос слишком короткий')

        return v

    @field_validator('column_names')
    @classmethod
    def validate_column_names(cls, v: List[str]) -> List[str]:
        """Валидация названий колонок"""
        if not v:
            raise ValueError('Список колонок не может быть пустым')

        # Очищаем названия колонок от лишних пробелов
        cleaned = [str(col).strip() if col is not None else f'Колонка_{i}' for i, col in enumerate(v)]

        # Проверяем на дубликаты (с учетом регистра)
        seen = set()
        for i, col in enumerate(cleaned):
            lower_col = col.lower()
            if lower_col in seen:
                # Добавляем индекс для уникальности
                cleaned[i] = f"{col}_{i}"
            seen.add(lower_col)

        return cleaned

    @field_validator('sheet_data')
    @classmethod
    def validate_sheet_data(cls, v: Optional[List[List[Any]]]) -> Optional[List[List[Any]]]:
        """Валидация данных таблицы"""
        if v is None:
            return v

        # Ограничиваем количество строк для предотвращения перегрузки
        MAX_ROWS = 1000
        if len(v) > MAX_ROWS:
            v = v[:MAX_ROWS]

        # Ограничиваем количество колонок
        MAX_COLS = 100
        if v and len(v[0]) > MAX_COLS:
            v = [row[:MAX_COLS] for row in v]

        return v

    @field_validator('selected_range', 'active_cell')
    @classmethod
    def validate_cell_reference(cls, v: Optional[str]) -> Optional[str]:
        """Валидация ссылок на ячейки"""
        if v is None:
            return v

        # Паттерн для ячеек и диапазонов: A1, B2:C10, $A$1, и т.д.
        cell_pattern = r'^[$]?[A-Za-z]+[$]?[0-9]+(:[A-Za-z]+[$]?[0-9]+)?$'
        if not re.match(cell_pattern, v.strip()):
            # Возвращаем None вместо ошибки, чтобы не ломать запрос
            return None

        return v.strip().upper()

    @model_validator(mode='after')
    def validate_data_consistency(self):
        """Проверка консистентности данных"""
        if self.sheet_data and self.column_names:
            # Проверяем что количество колонок соответствует данным
            expected_cols = len(self.column_names)
            for i, row in enumerate(self.sheet_data):
                if len(row) != expected_cols:
                    # Выравниваем строку под количество колонок
                    if len(row) < expected_cols:
                        self.sheet_data[i] = row + [None] * (expected_cols - len(row))
                    else:
                        self.sheet_data[i] = row[:expected_cols]
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Сумма продаж где сумма больше 500000",
                "column_names": ["Дата", "Продажи", "Менеджер"],
                "sheet_data": [
                    ["2024-01-01", 600000, "Иванов"],
                    ["2024-01-02", 400000, "Петров"]
                ],
                "history": [
                    {"query": "создай круговую диаграмму", "actions": [{"type": "create_chart", "config": {"type": "pie"}}]}
                ]
            }
        }


class AnalyzeRequest(BaseModel):
    """Запрос на анализ данных"""
    query: str = Field(..., description="Аналитический вопрос")
    sheet_data: List[List[Any]] = Field(..., description="Данные таблицы (макс 1000 строк)")
    column_names: List[str] = Field(..., description="Названия колонок")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Почему продажи упали в октябре?",
                "sheet_data": [
                    ["2024-09-15", 150000, "Иванов"],
                    ["2024-10-15", 100000, "Иванов"]
                ],
                "column_names": ["Дата", "Продажи", "Менеджер"]
            }
        }


class ReportRequest(BaseModel):
    """Запрос на создание отчета"""
    query: str = Field(..., description="Описание нужного отчета")
    sheet_data: List[List[Any]] = Field(..., description="Данные для отчета")
    report_type: Optional[str] = Field("weekly", description="Тип отчета: weekly, monthly, custom")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Создай еженедельный отчет по продажам",
                "sheet_data": [["Менеджер", "Продажи"], ["Иванов", 500000]],
                "report_type": "weekly"
            }
        }
