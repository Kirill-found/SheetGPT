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

        # Обрабатываем запрос через AI
        # Если есть conversation_id - используем generate_actions (Interactive Builder с историей)
        # Иначе используем старый process_query
        if request.conversation_id:
            # Используем Interactive Builder с поддержкой conversation history
            sheet_data_dict = {
                "columns": request.column_names,
                "sample_data": request.sheet_data[1:] if request.sheet_data and len(request.sheet_data) > 1 else [],
                "row_count": len(request.sheet_data) if request.sheet_data else 0,
                "sheet_id": "default",
                "selected_range": request.selected_range,
                "active_cell": request.active_cell
            }
            result = await ai_service.generate_actions(
                query=request.query,
                sheet_data=sheet_data_dict,
                conversation_id=request.conversation_id
            )
        else:
            # v5.1.0: Use AI Code Executor via process_formula_request
            result = ai_service.process_formula_request(
                query=request.query,
                column_names=request.column_names,
                sheet_data=request.sheet_data,
                history=request.history or []
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
            # DEBUG: Log result from AI service
            print(f"📥 formula.py received result keys: {list(result.keys())}")
            print(f"📥 result has methodology: {('methodology' in result)}")
            if 'methodology' in result:
                print(f"📥 methodology value: {result['methodology']}")

            # Для анализа возвращаем структурированный ответ
            response_data = FormulaResponse(
                formula=None,  # Нет формулы
                explanation=result.get("answer", result.get("summary", "")),  # Fallback для совместимости
                insights=result.get("insights", []),
                suggested_actions=result.get("suggested_actions", []),
                target_cell=None,
                confidence=result["confidence"],
                response_type="analysis"
            )
            # Добавляем структурированные поля
            response_dict = response_data.model_dump()
            response_dict["summary"] = result.get("summary")
            response_dict["methodology"] = result.get("methodology")  # CRITICAL: Show which data was used
            response_dict["key_findings"] = result.get("key_findings", [])
            # DEBUG: Add generated Python code for troubleshooting
            response_dict["code_generated"] = result.get("code_generated")
            response_dict["python_executed"] = result.get("python_executed", False)
            response_dict["execution_output"] = result.get("execution_output", "")

            print(f"📦 response_dict keys before return: {list(response_dict.keys())}")
            print(f"📦 response_dict['methodology']: {response_dict.get('methodology')}")

            if result.get("conversation_id"):
                response_dict["conversation_id"] = result["conversation_id"]
            return response_dict
        elif response_type == "action":
            # ОПТИМИЗАЦИЯ: Если есть только одна формула (игнорируем format_cells и другие второстепенные действия)
            insights = result.get("insights", [])
            formula_actions = [a for a in insights if a.get("type") == "insert_formula"]

            # Если есть ровно ОДНА формула для вставки, возвращаем как простой formula response
            if len(formula_actions) == 1:
                formula_config = formula_actions[0].get("config", {})
                response_data = FormulaResponse(
                    formula=formula_config.get("formula"),
                    explanation=result.get("explanation", ""),
                    target_cell=formula_config.get("cell"),
                    confidence=result["confidence"],
                    response_type="formula"
                )
                response_dict = response_data.model_dump()
                if result.get("conversation_id"):
                    response_dict["conversation_id"] = result["conversation_id"]
                return response_dict

            # Для множественных actions возвращаем план действий
            response_data = FormulaResponse(
                formula=None,  # Нет формулы
                explanation=result.get("explanation", ""),
                insights=result.get("insights", []),  # Действия передаем в insights
                suggested_actions=None,
                target_cell=None,
                confidence=result["confidence"],
                response_type="action"
            )
            # Добавляем metadata из 2-step prompting
            response_dict = response_data.model_dump()
            response_dict["intent"] = result.get("intent")
            response_dict["depth"] = result.get("depth")
            if result.get("conversation_id"):
                response_dict["conversation_id"] = result["conversation_id"]
            return response_dict
        else:
            # Для формулы
            response_data = FormulaResponse(
                formula=result.get("formula"),
                explanation=result.get("explanation"),
                target_cell=result.get("target_cell"),
                confidence=result["confidence"],
                response_type="formula"
            )
            # Добавляем conversation_id если он есть в result
            response_dict = response_data.model_dump()
            if result.get("conversation_id"):
                response_dict["conversation_id"] = result["conversation_id"]
            return response_dict

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка генерации формулы: {str(e)}"
        )
