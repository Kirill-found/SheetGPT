from pydantic import BaseModel, Field
from typing import Optional, List, Any


class FormulaResponse(BaseModel):
    """Универсальный ответ - формула или анализ"""
    formula: Optional[str] = Field(None, description="Готовая Google Sheets формула (если тип=formula)")
    explanation: str = Field(..., description="Объяснение на русском или детальный ответ")
    target_cell: Optional[str] = Field(None, description="Рекомендуемая ячейка для вставки")
    confidence: float = Field(..., description="Уверенность модели (0-1)")
    response_type: str = Field("formula", description="Тип ответа: formula | analysis | action")
    insights: Optional[List[Any]] = Field(None, description="Инсайты для анализа или action plan")
    suggested_actions: Optional[List[str]] = Field(None, description="Рекомендации")

    class Config:
        json_schema_extra = {
            "example": {
                "formula": "=SORT(FILTER(A2:G,C2:C>500000),3,FALSE)",
                "explanation": "Фильтрует данные где значение в колонке C больше 500000 и сортирует по 3 колонке",
                "target_cell": "I2",
                "confidence": 0.98,
                "response_type": "formula"
            }
        }


class AnalyzeResponse(BaseModel):
    """Ответ с анализом данных"""
    answer: str = Field(..., description="Детальный ответ на вопрос")
    insights: Optional[List[dict]] = Field(None, description="Структурированные инсайты")
    processing_time: float = Field(..., description="Время обработки в секундах")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "📉 Продажи упали на 15%...",
                "insights": [
                    {"type": "decrease", "factor": "Manager Ivanov", "impact": -50000}
                ],
                "processing_time": 2.3
            }
        }


class ReportResponse(BaseModel):
    """Ответ с данными отчета"""
    report_title: str = Field(..., description="Заголовок отчета")
    report_data: List[List[Any]] = Field(..., description="Данные для вставки в новый лист")
    chart_config: Optional[dict] = Field(None, description="Конфигурация графика")

    class Config:
        json_schema_extra = {
            "example": {
                "report_title": "Weekly Sales Report - Nov 4-10",
                "report_data": [["Metric", "Value"], ["Total Sales", "1,240,000₽"]],
                "chart_config": {"type": "column", "data_range": "A2:B10"}
            }
        }


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    error: str = Field(..., description="Описание ошибки")
    detail: Optional[str] = Field(None, description="Детали ошибки")
