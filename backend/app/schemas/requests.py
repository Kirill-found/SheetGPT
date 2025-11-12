from pydantic import BaseModel, Field
from typing import List, Optional, Any


class FormulaRequest(BaseModel):
    """Запрос на генерацию формулы"""
    query: str = Field(..., description="Запрос пользователя на естественном языке")
    column_names: List[str] = Field(..., description="Названия колонок в таблице")
    sheet_data: Optional[List[List[Any]]] = Field(None, description="Первые 5 строк для контекста")
    history: Optional[List[dict]] = Field(None, description="История предыдущих действий для контекста")
    selected_range: Optional[str] = Field(None, description="Выделенный диапазон (например 'H5:H17')")
    active_cell: Optional[str] = Field(None, description="Активная ячейка (например 'H5')")
    conversation_id: Optional[str] = Field(None, description="ID разговора для поддержки контекстных запросов")
    custom_context: Optional[str] = Field(None, max_length=2000, description="Персонализированная роль AI (например, 'Ты финансовый директор...')")

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
