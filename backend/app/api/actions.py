"""
API endpoints для Interactive Builder (actions с clarification)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api/v1/actions", tags=["actions"])


class ActionRequest(BaseModel):
    """Запрос на создание action"""
    query: str
    columns: List[str]
    sample_data: Optional[List[List[Any]]] = None
    row_count: Optional[int] = None
    sheet_id: Optional[str] = None


class ClarificationRequest(BaseModel):
    """Ответы на clarification вопросы"""
    intent_id: str
    answers: Dict[str, Any]


@router.post(
    "/generate",
    summary="Генерация action с Interactive Builder",
    description="""
    Создает action из запроса пользователя используя Interactive Builder.

    Если certainty высокая - сразу возвращает action.
    Если certainty низкая - возвращает clarification вопросы.
    """
)
async def generate_action(request: ActionRequest):
    """
    Генерирует action через Interactive Builder

    **Пример 1: Высокая certainty (сразу action)**
    ```json
    {
      "query": "Посчитай сумму продаж",
      "columns": ["Товар", "Продажи", "Регион"],
      "row_count": 10
    }
    ```

    **Ответ:**
    ```json
    {
      "success": true,
      "actions": [{
        "type": "insert_formula",
        "config": {
          "cell": "A1",
          "formula": "=СУММ(B2:B10)"
        },
        "confidence": 0.92
      }],
      "source": "interactive_builder"
    }
    ```

    **Пример 2: Низкая certainty (вопросы)**
    ```json
    {
      "query": "Найди цену товара",
      "columns": ["Товар", "Цена", "Количество"]
    }
    ```

    **Ответ:**
    ```json
    {
      "success": false,
      "needs_clarification": true,
      "intent_id": "uuid-here",
      "questions": [
        {
          "parameter": "lookup_column",
          "text": "В какой колонке искать значение?",
          "type": "select",
          "options": [
            {"value": "Товар", "label": "A: Товар"},
            {"value": "Цена", "label": "B: Цена"}
          ]
        }
      ]
    }
    ```
    """

    try:
        # Валидация
        if not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail="Query cannot be empty"
            )

        if not request.columns:
            raise HTTPException(
                status_code=400,
                detail="Columns are required"
            )

        # Формируем sheet_data для AIService
        sheet_data = {
            "columns": request.columns,
            "sample_data": request.sample_data or [],
            "row_count": request.row_count or 100,
            "sheet_id": request.sheet_id or "unknown"
        }

        # Генерируем action через Interactive Builder
        result = await ai_service.generate_actions(request.query, sheet_data)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.post(
    "/clarify",
    summary="Отправка ответов на clarification вопросы",
    description="""
    Применяет ответы пользователя на вопросы и создает проверенный action.
    """
)
async def clarify_action(request: ClarificationRequest):
    """
    Обрабатывает ответы на clarification вопросы

    **Пример:**
    ```json
    {
      "intent_id": "uuid-from-previous-request",
      "answers": {
        "lookup_column": "Товар",
        "result_column": "Цена"
      }
    }
    ```

    **Ответ:**
    ```json
    {
      "success": true,
      "actions": [{
        "type": "insert_formula",
        "config": {
          "cell": "A1",
          "formula": "=ЕСЛИОШИБКА(ВПР(A2,A1:B10,2,ЛОЖЬ),\"\")"
        },
        "confidence": 0.93
      }],
      "source": "interactive_builder"
    }
    ```
    """

    try:
        # Валидация
        if not request.intent_id:
            raise HTTPException(
                status_code=400,
                detail="intent_id is required"
            )

        if not request.answers:
            raise HTTPException(
                status_code=400,
                detail="answers cannot be empty"
            )

        # Применяем ответы и создаем action
        result = await ai_service.apply_clarification(
            intent_id=request.intent_id,
            answers=request.answers
        )

        # Проверяем результат
        if not result.get("success"):
            error_type = result.get("error_type", "unknown")

            if error_type == "intent_expired":
                raise HTTPException(
                    status_code=404,
                    detail=result.get("error", "Intent not found or expired")
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=result.get("error", "Cannot create action")
                )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )
