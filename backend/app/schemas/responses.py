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
    # Analysis fields (for response_type='analysis')
    summary: Optional[str] = Field(None, description="Краткий вывод анализа")
    methodology: Optional[str] = Field(None, description="Объяснение какие данные использовались для расчёта")
    key_findings: Optional[List[str]] = Field(None, description="Ключевые находки с цифрами")
    # Professional insights (new - v6.2.0)
    professional_insights: Optional[str] = Field(None, description="Профессиональные инсайты от AI с учетом роли")
    recommendations: Optional[List[str]] = Field(None, description="Рекомендации по улучшению")
    warnings: Optional[List[str]] = Field(None, description="Предупреждения о потенциальных проблемах")
    # Table/Chart creation field (CRITICAL for actions system)
    structured_data: Optional[dict] = Field(None, description="Структурированные данные для создания таблиц/графиков")
    # Highlight action fields
    action_type: Optional[str] = Field(None, description="Тип действия: highlight | none")
    highlight_rows: Optional[List[int]] = Field(None, description="Номера строк для выделения (1-indexed)")
    highlight_color: Optional[str] = Field(None, description="Цвет выделения (hex, например #FFFF00)")
    highlight_message: Optional[str] = Field(None, description="Сообщение о выделенных строках")
    # v7.4.0: Function calling metadata
    function_used: Optional[str] = Field(None, description="Название использованной функции")
    parameters: Optional[dict] = Field(None, description="Параметры вызванной функции")
    # v6.2.9: Chart creation field
    chart_spec: Optional[dict] = Field(None, description="Спецификация диаграммы для создания")
    # Freeze rows/columns fields
    freeze_rows: Optional[int] = Field(None, description="Количество строк для закрепления")
    freeze_columns: Optional[int] = Field(None, description="Количество колонок для закрепления")
    # Sort fields
    sort_column: Optional[str] = Field(None, description="Название колонки для сортировки")
    sort_column_index: Optional[int] = Field(None, description="Индекс колонки для сортировки")
    sort_order: Optional[str] = Field(None, description="Порядок сортировки: asc | desc")
    # Format fields
    format_type: Optional[str] = Field(None, description="Тип форматирования")
    target_row: Optional[int] = Field(None, description="Целевая строка для форматирования")
    bold: Optional[bool] = Field(None, description="Жирный текст")
    background_color: Optional[str] = Field(None, description="Цвет фона")
    # Value field (for simple calculations)
    value: Optional[Any] = Field(None, description="Вычисленное значение")
    # Pivot table fields
    pivot_data: Optional[dict] = Field(None, description="Данные сводной таблицы {headers, rows}")
    group_column: Optional[str] = Field(None, description="Колонка группировки")
    value_column: Optional[str] = Field(None, description="Колонка значений")
    agg_func: Optional[str] = Field(None, description="Функция агрегации (sum, mean, count...)")
    # Color scale / conditional formatting fields
    color_scale_rule: Optional[dict] = Field(None, description="Правило цветовой шкалы (градиента)")
    conditional_rule: Optional[dict] = Field(None, description="Правило условного форматирования")
    convert_rule: Optional[dict] = Field(None, description="Правило конвертации колонки в числа")
    # v9.3.2: VLOOKUP write_data fields
    write_data: Optional[List[List[Any]]] = Field(None, description="Данные для записи в текущий лист (VLOOKUP)")
    write_headers: Optional[List[str]] = Field(None, description="Заголовки для записываемых данных")
    # Processor metadata
    processor_version: Optional[str] = Field(None, description="Версия процессора")
    complexity: Optional[str] = Field(None, description="Сложность запроса")
    strategy: Optional[str] = Field(None, description="Стратегия обработки")
    processing_time: Optional[str] = Field(None, description="Время обработки")
    retry_count: Optional[int] = Field(None, description="Количество повторов")
    # Debug fields
    code_generated: Optional[str] = Field(None, description="Сгенерированный Python код")
    python_executed: Optional[bool] = Field(None, description="Был ли выполнен Python код")

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
