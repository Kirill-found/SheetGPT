# v6.2.8 - Custom Context Debug
# v6.2.9 - Chart spec generation
# v6.2.10 - Fix: Don't skip first data row (frontend already separates headers)
from fastapi import APIRouter, HTTPException
from app.schemas.requests import FormulaRequest
from app.schemas.responses import FormulaResponse, ErrorResponse
from app.services.ai_service import ai_service
import logging
import pandas as pd
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/v1", tags=["formula"])
logger = logging.getLogger(__name__)

CHART_KEYWORDS = ["диаграмм", "график", "chart", "построй", "визуализ", "plot", "гистограмм"]
CHART_TYPES = {
    "линейн": "LINE", "line": "LINE", "график": "LINE",
    "столбч": "COLUMN", "column": "COLUMN", "bar": "BAR",
    "гистограмм": "COLUMN",
    "круг": "PIE", "pie": "PIE", "пирог": "PIE", "долев": "PIE",
    "област": "AREA", "area": "AREA",
    "точечн": "SCATTER", "scatter": "SCATTER",
    "комбинир": "COMBO", "combo": "COMBO"
}

def detect_chart_request(query: str, column_names: List[str], sheet_data: List[List]) -> Optional[Dict[str, Any]]:
    query_lower = query.lower()
    is_chart_query = any(kw in query_lower for kw in CHART_KEYWORDS)
    if not is_chart_query:
        return None

    logger.info(f"[ChartDetect] Chart request detected: {query}")

    chart_type = "COLUMN"
    for type_keyword, type_value in CHART_TYPES.items():
        if type_keyword in query_lower:
            chart_type = type_value
            break

    try:
        if sheet_data and len(sheet_data) > 0:
            num_cols = len(sheet_data[0]) if sheet_data[0] else len(column_names)
            df = pd.DataFrame(sheet_data, columns=column_names[:num_cols])
        else:
            df = pd.DataFrame(columns=column_names)
    except Exception as e:
        logger.warning(f"[ChartDetect] DataFrame error: {e}")
        df = pd.DataFrame()

    numeric_cols = []
    categorical_cols = []
    date_cols = []

    for idx, col in enumerate(column_names):
        if idx >= len(df.columns):
            continue
        col_data = df.iloc[:, idx] if len(df) > 0 else pd.Series()
        try:
            numeric_data = pd.to_numeric(col_data, errors="coerce")
            non_null_ratio = numeric_data.notna().sum() / len(numeric_data) if len(numeric_data) > 0 else 0
            if non_null_ratio > 0.5:
                numeric_cols.append({"name": col, "index": idx})
                continue
        except:
            pass
        col_lower = col.lower()
        if any(d in col_lower for d in ["дата", "date", "месяц", "month", "год", "year"]):
            date_cols.append({"name": col, "index": idx})
            continue
        categorical_cols.append({"name": col, "index": idx})

    mentioned_cols = []
    for idx, col in enumerate(column_names):
        col_lower = col.lower()
        if col_lower in query_lower or col in query:
            mentioned_cols.append({"name": col, "index": idx})
        else:
            for word in col_lower.split():
                if len(word) > 2 and word in query_lower:
                    mentioned_cols.append({"name": col, "index": idx})
                    break

    x_column = None
    y_columns = []

    for cat in categorical_cols:
        if cat in mentioned_cols:
            x_column = cat
            break
    if not x_column and date_cols:
        x_column = date_cols[0]
    if not x_column and categorical_cols:
        x_column = categorical_cols[0]

    for num in numeric_cols:
        if num in mentioned_cols:
            y_columns.append(num)
    if not y_columns and numeric_cols:
        y_columns = numeric_cols[:3]
    if chart_type == "PIE" and y_columns:
        y_columns = [y_columns[0]]

    title = ""
    if y_columns and x_column:
        y_names = ", ".join([c["name"] for c in y_columns])
        title = f"{y_names} по {x_column['name']}"
    elif y_columns:
        title = ", ".join([c["name"] for c in y_columns])

    chart_spec = {
        "chart_type": chart_type,
        "title": title,
        "x_column_index": x_column["index"] if x_column else 0,
        "x_column_name": x_column["name"] if x_column else column_names[0] if column_names else "",
        "y_column_indices": [c["index"] for c in y_columns] if y_columns else [1] if len(column_names) > 1 else [0],
        "y_column_names": [c["name"] for c in y_columns] if y_columns else [column_names[1] if len(column_names) > 1 else column_names[0]] if column_names else [],
        "row_count": len(df),
        "col_count": len(column_names)
    }

    chart_type_names = {
        "LINE": "линейный график",
        "BAR": "горизонтальную гистограмму",
        "COLUMN": "столбчатую диаграмму",
        "PIE": "круговую диаграмму",
        "AREA": "диаграмму с областями",
        "SCATTER": "точечную диаграмму",
        "COMBO": "комбинированный график"
    }

    message = f"Создаю {chart_type_names.get(chart_type, 'диаграмму')}: {title}"
    logger.info(f"[ChartDetect] chart_spec: {chart_spec}")

    return {
        "action_type": "chart",
        "chart_spec": chart_spec,
        "summary": message
    }


@router.post("/debug-request", include_in_schema=False)
async def debug_request(request: FormulaRequest):
    return {
        "query": request.query,
        "custom_context": request.custom_context,
        "custom_context_type": str(type(request.custom_context)),
        "custom_context_len": len(request.custom_context) if request.custom_context else 0,
        "has_custom_context": bool(request.custom_context)
    }


@router.post(
    "/formula",
    response_model=FormulaResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Генерация Google Sheets формулы"
)
async def generate_formula(request: FormulaRequest):
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Запрос не может быть пустым")
        if not request.column_names:
            raise HTTPException(status_code=400, detail="Необходимо указать названия колонок")

        # v6.2.9: Check for chart request FIRST
        chart_result = detect_chart_request(request.query, request.column_names, request.sheet_data or [])
        if chart_result:
            logger.info("[FORMULA] Chart request detected, returning chart response")
            return {
                "formula": None,
                "explanation": "",
                "target_cell": None,
                "confidence": 0.98,
                "response_type": "analysis",
                "insights": [],
                "suggested_actions": None,
                "summary": chart_result["summary"],
                "action_type": chart_result["action_type"],
                "chart_spec": chart_result["chart_spec"]
            }

        if request.conversation_id:
            sheet_data_dict = {
                "columns": request.column_names,
                "sample_data": request.sheet_data if request.sheet_data else [],  # v6.2.10: Don't skip first row - frontend already separates headers
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
            result = ai_service.process_formula_request(
                query=request.query,
                column_names=request.column_names,
                sheet_data=request.sheet_data,
                history=request.history or [],
                custom_context=request.custom_context
            )

        if result.get("confidence", 0) < 0.5:
            raise HTTPException(status_code=400, detail="Не удалось понять запрос")

        response_type = result.get("response_type", result.get("result_type", result.get("type", "formula")))

        # Debug logging for VLOOKUP
        logger.info(f"[Formula API] Result keys: {list(result.keys())}")
        logger.info(f"[Formula API] action_type: {result.get('action_type')}, write_data present: {'write_data' in result}")

        if response_type in ("analysis", "question", "chat"):
            response_data = FormulaResponse(
                formula=None,
                explanation=result.get("answer", result.get("summary", "")),
                insights=result.get("insights", []),
                suggested_actions=result.get("suggested_actions", []),
                target_cell=None,
                confidence=result["confidence"],
                response_type="analysis"
            )
            response_dict = response_data.model_dump()
            response_dict["summary"] = result.get("summary")
            response_dict["methodology"] = result.get("methodology")
            response_dict["key_findings"] = result.get("key_findings", [])
            if "structured_data" in result:
                response_dict["structured_data"] = result["structured_data"]
            if "highlight_rows" in result and result["highlight_rows"]:
                response_dict["highlight_rows"] = result["highlight_rows"]
                response_dict["highlight_color"] = result.get("highlight_color", "#FFFF00")
                response_dict["highlight_message"] = result.get("highlight_message", "Строки выделены")
            # v9.3.2: VLOOKUP write_data fields
            if "action_type" in result:
                response_dict["action_type"] = result["action_type"]
            # v10.0.2: Chat message for clarification
            if "message" in result:
                response_dict["message"] = result["message"]
            if "write_data" in result:
                response_dict["write_data"] = result["write_data"]
            if "write_headers" in result:
                response_dict["write_headers"] = result["write_headers"]
            # v9.3.3: Clean data fields
            if "cleaned_data" in result:
                response_dict["cleaned_data"] = result["cleaned_data"]
            if "original_rows" in result:
                response_dict["original_rows"] = result["original_rows"]
            if "final_rows" in result:
                response_dict["final_rows"] = result["final_rows"]
            if "operations" in result:
                response_dict["operations"] = result["operations"]
            if "changes" in result:
                response_dict["changes"] = result["changes"]
            if result.get("conversation_id"):
                response_dict["conversation_id"] = result["conversation_id"]
            return response_dict
        elif response_type == "action":
            insights = result.get("insights", [])
            formula_actions = [a for a in insights if a.get("type") == "insert_formula"]
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
            response_data = FormulaResponse(
                formula=None,
                explanation=result.get("explanation", result.get("summary", "")),
                insights=result.get("insights", []),
                suggested_actions=None,
                target_cell=None,
                confidence=result["confidence"],
                response_type="action"
            )
            response_dict = response_data.model_dump()
            response_dict["summary"] = result.get("summary")
            # v9.3.3: Pass through all action-specific fields
            if "action_type" in result:
                response_dict["action_type"] = result["action_type"]
            if "message" in result:
                response_dict["message"] = result["message"]
            if "cleaned_data" in result:
                response_dict["cleaned_data"] = result["cleaned_data"]
            if "original_rows" in result:
                response_dict["original_rows"] = result["original_rows"]
            if "final_rows" in result:
                response_dict["final_rows"] = result["final_rows"]
            if "operations" in result:
                response_dict["operations"] = result["operations"]
            if "changes" in result:
                response_dict["changes"] = result["changes"]
            if result.get("conversation_id"):
                response_dict["conversation_id"] = result["conversation_id"]
            return response_dict
        else:
            response_data = FormulaResponse(
                formula=result.get("formula"),
                explanation=result.get("explanation"),
                target_cell=result.get("target_cell"),
                confidence=result["confidence"],
                response_type="formula"
            )
            response_dict = response_data.model_dump()
            if result.get("conversation_id"):
                response_dict["conversation_id"] = result["conversation_id"]
            return response_dict

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации формулы: {str(e)}")
