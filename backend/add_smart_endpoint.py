# -*- coding: utf-8 -*-
"""Add SmartAnalyst v2 endpoint"""

file_path = "app/main.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already added
if "SmartAnalyst" in content or "/api/v2/analyze" in content:
    print("SmartAnalyst endpoint already exists!")
    exit(0)

# Find insertion point
old_code = '''    except Exception as e:
        logger.error(f"[CleanAnalyst] Fatal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "message": "Ошибка анализа"}
        )


def classify_backend_error(error_msg: str) -> dict:'''

new_code = '''    except Exception as e:
        logger.error(f"[CleanAnalyst] Fatal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "message": "Ошибка анализа"}
        )


# =============================================================================
# NEW: SmartAnalyst v2 - GPT планирует, Pandas считает
# =============================================================================
@app.post("/api/v2/analyze")
async def analyze_smart(
    request: FormulaRequest,
    x_api_token: Optional[str] = Header(None, alias="X-API-Token"),
    x_license_key: Optional[str] = Header(None, alias="X-License-Key")
):
    """
    SmartAnalyst v1.0 - Двухфазный подход:
    1. GPT понимает запрос и генерирует спецификацию
    2. Pandas выполняет ТОЧНЫЕ расчёты
    3. GPT форматирует результат
    """
    try:
        logger.info("="*60)
        logger.info(f"[SmartAnalyst] Query: {request.query}")
        logger.info(f"[SmartAnalyst] Data: {len(request.sheet_data)} rows x {len(request.column_names)} cols")

        import pandas as pd
        from app.services.smart_analyst import SmartAnalyst

        # Создаем DataFrame
        num_cols = len(request.column_names)
        padded_data = []
        for row in request.sheet_data:
            if len(row) < num_cols:
                row = list(row) + [None] * (num_cols - len(row))
            padded_data.append(row[:num_cols])

        df = pd.DataFrame(padded_data, columns=request.column_names)

        # Конвертируем числовые колонки
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            except:
                pass

        # Инициализируем SmartAnalyst
        analyst = SmartAnalyst(api_key=settings.OPENAI_API_KEY)

        # Анализируем
        result = await analyst.analyze(
            query=request.query,
            df=df,
            column_names=request.column_names,
            context=request.custom_context,
            history=request.history
        )

        if not result.get("success"):
            logger.error(f"[SmartAnalyst] Error: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error"),
                "response_type": "error",
                "summary": f"Ошибка: {result.get('error')}"
            }

        response = result["gpt_response"]
        response["success"] = True
        response["processor_version"] = "SmartAnalyst v1.0"

        logger.info(f"[SmartAnalyst] Success! python_executed: {response.get('python_executed')}")
        logger.info("="*60)

        return sanitize_for_json(response)

    except Exception as e:
        logger.error(f"[SmartAnalyst] Fatal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "message": "Ошибка анализа"}
        )


def classify_backend_error(error_msg: str) -> dict:'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Added SmartAnalyst v2 endpoint")
else:
    print("ERROR: Pattern not found")
