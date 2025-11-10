from fastapi import APIRouter, HTTPException
from app.schemas.requests import FormulaRequest
from app.schemas.responses import FormulaResponse, ErrorResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api/v1", tags=["formula"])


@router.post(
    "/formula",
    response_model=FormulaResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    summary="Генерация Google Sheets формулы",
    description="Принимает запрос на естественном языке и возвращает готовую формулу"
)
async def generate_formula(request: FormulaRequest):
    """
    Генерирует Google Sheets формулу на основе запроса пользователя.

    **Пример запроса:**
    ```json
    {
      "query": "Сумма продаж где сумма больше 500000",
      "column_names": ["Дата", "Продажи", "Менеджер"],
      "sheet_data": [
        ["2024-01-01", 600000, "Иванов"],
        ["2024-01-02", 400000, "Петров"]
      ]
    }
    ```

    **Ответ:**
    ```json
    {
      "formula": "=SUMIF(B:B, \">500000\", B:B)",
      "explanation": "Суммирует все значения...",
      "target_cell": "D1",
      "confidence": 0.98
    }
    ```
    """

    try:
        # Валидация
        if not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail="Запрос не может быть пустым"
            )

        if not request.column_names:
            raise HTTPException(
                status_code=400,
                detail="Необходимо указать названия колонок"
            )

        # Обрабатываем запрос через AI (автоматически определяет тип)
        result = await ai_service.process_query(
            query=request.query,
            column_names=request.column_names,
            sample_data=request.sheet_data
        )

        # Проверяем confidence
        if result.get("confidence", 0) < 0.5:
            raise HTTPException(
                status_code=400,
                detail=f"Не удалось понять запрос: {result.get('explanation', result.get('answer', 'Неясный запрос'))}"
            )

        # Возвращаем ответ в зависимости от типа
        response_type = result.get("type", "formula")

        if response_type == "analysis" or response_type == "question":
            # Для анализа возвращаем ответ как explanation
            return FormulaResponse(
                formula=None,  # Нет формулы
                explanation=result.get("answer", ""),
                insights=result.get("insights", []),
                suggested_actions=result.get("suggested_actions", []),
                target_cell=None,
                confidence=result["confidence"],
                response_type="analysis"
            )
        else:
            # Для формулы
            return FormulaResponse(
                formula=result.get("formula"),
                explanation=result.get("explanation"),
                target_cell=result.get("target_cell"),
                confidence=result["confidence"],
                response_type="formula"
            )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка генерации формулы: {str(e)}"
        )
