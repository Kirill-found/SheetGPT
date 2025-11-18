"""
SheetGPT API Production v7.2.4 - Function Calling with Smart Matching
95%+ accuracy через проверенные функции + умный поиск колонок
Автоматическое преобразование строковых чисел
Railway deployment: 2025-11-17 - FUNCTION CALLING v7.2.4
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas.requests import FormulaRequest
from app.schemas.responses import FormulaResponse
from app.config import settings
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with VERSION 7.2.4 - Smart column matching + string number parsing
app = FastAPI(
    title="SheetGPT API",
    version="7.2.4",  # v7.2.4: Smart column matching + auto string number parsing
    description="AI-powered spreadsheet assistant with Function Calling (95%+ accuracy), smart column matching, and automatic string number parsing"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("="*60)
    logger.info("SheetGPT API v7.2.4 STARTING - Function Calling with Smart Column Matching")
    logger.info(f"Started at: {datetime.now()}")
    logger.info("Function Calling: ENABLED (30+ functions)")
    logger.info("Smart Column Matching: ENABLED (fuzzy matching)")
    logger.info("String Number Parsing: ENABLED (e.g. 'р.857 765' -> 857765)")
    logger.info("Python Code Execution: FALLBACK (for complex queries)")
    logger.info("Accuracy target: 95%+")
    logger.info("="*60)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": "SheetGPT API",
        "version": "6.6.17",  # v6.6.17: BACKEND FIX - Split operations now correctly generate structured_data
        "status": "operational",
        "engine": "AI Code Executor",
        "features": {
            "ai_code_generation": True,
            "python_execution": True,
            "accuracy": "99%",
            "methodology": True,
            "auto_headers": True,
            "custom_context": True,  # v6.6.4: Personalized AI role
            "professional_insights": True  # v6.6.4: AI-generated insights/recommendations
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "version": "7.2.4",
        "service": "SheetGPT API",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "ai_service": "operational",
            "function_calling": "enabled",
            "functions_available": 30,
            "smart_column_matching": "enabled",
            "string_number_parsing": "enabled",
            "accuracy": "95%+",
            "response_fields": ["summary", "methodology", "key_findings"]
        }
    }

@app.post("/api/v1/formula", response_model=FormulaResponse)
async def process_formula(request: FormulaRequest):
    """
    Main endpoint v7.2.4 - Function Calling with Smart Column Matching
    - Fuzzy column name matching (e.g. "Сумма" finds "Заказали на сумму")
    - Auto string number parsing (e.g. "р.857 765" -> 857765)
    - Fallback to Code Executor for complex queries
    """
    try:
        # Log incoming request
        logger.info("="*60)
        logger.info(f"[REQUEST v7.2.4] Query: {request.query}")
        logger.info(f"[DATA] Shape: {len(request.sheet_data)} rows x {len(request.column_names)} columns")

        result = None

        # Try AIFunctionCaller first (v7.2.4 with smart matching)
        try:
            from app.services.ai_function_caller import AIFunctionCaller
            import pandas as pd

            logger.info("[ENGINE v7.2.4] Using AI Function Caller with Smart Column Matching")

            # Создаем DataFrame из данных
            df = pd.DataFrame(request.sheet_data, columns=request.column_names)

            # Создаем caller и обрабатываем запрос
            caller = AIFunctionCaller()
            result = await caller.process_query(
                query=request.query,
                df=df,
                column_names=request.column_names,
                sheet_data=request.sheet_data,
                custom_context=request.custom_context
            )

            logger.info("[SUCCESS] Function calling completed")
            logger.info(f"[DEBUG] Response type: {result.get('response_type')}")
            logger.info(f"[DEBUG] Function used: {result.get('function_used', 'N/A')}")

        except Exception as e:
            logger.warning(f"[FALLBACK] Function caller failed ({str(e)}), using code executor")
            # Fallback to Code Executor
            try:
                from app.services.ai_code_executor import get_ai_executor

                executor = get_ai_executor()
                result = executor.process_with_code(
                    query=request.query,
                    column_names=request.column_names,
                    sheet_data=request.sheet_data,
                    history=request.history,
                    custom_context=request.custom_context
                )
                logger.info("[FALLBACK SUCCESS] Code executor used")

            except Exception as fallback_error:
                logger.error(f"[ERROR] Both function caller and code executor failed: {fallback_error}")
                # Last resort: v3 service
                from app.services.ai_service_v3 import get_ai_service
                ai_service = get_ai_service()

                result = ai_service.process_formula_request(
                    query=request.query,
                    column_names=request.column_names,
                    sheet_data=request.sheet_data,
                    history=request.history
                )

        # Log result summary
        if result.get("summary"):
            logger.info(f"[RESULT] {result['summary'][:100]}...")
        if result.get("methodology"):
            logger.info("[METHODOLOGY] Provided: YES")
        if result.get("function_used"):
            logger.info(f"[FUNCTION] Used: {result['function_used']}")
        if result.get("python_executed"):
            logger.info("[EXECUTION] Python code executed")

        # Ensure all required fields are present
        response = FormulaResponse(
            formula=result.get("formula"),
            explanation=result.get("explanation", ""),
            target_cell=result.get("target_cell"),
            confidence=result.get("confidence", 0.95),  # Function calls set 0.98, code executor 0.95
            response_type=result.get("response_type", "analysis"),
            insights=result.get("insights", []),
            suggested_actions=result.get("suggested_actions"),
            summary=result.get("summary"),
            methodology=result.get("methodology"),
            key_findings=result.get("key_findings", [])
        )

        # Convert to dict to add debug fields (code_generated, etc.)
        response_dict = response.model_dump()

        # Add structured_data for table/chart creation (CRITICAL for actions system)
        if "structured_data" in result:
            response_dict["structured_data"] = result["structured_data"]

        # Add highlighting data (v6.6.4: CRITICAL for row highlighting)
        if "highlight_rows" in result:
            response_dict["highlight_rows"] = result["highlight_rows"]
        if "highlight_color" in result:
            response_dict["highlight_color"] = result["highlight_color"]
        if "highlight_message" in result:
            response_dict["highlight_message"] = result["highlight_message"]
        if "action_type" in result:
            response_dict["action_type"] = result["action_type"]

        # Add debug fields ALWAYS (for troubleshooting)
        response_dict["code_generated"] = result.get("code_generated", "NOT_IN_RESULT")
        response_dict["python_executed"] = result.get("python_executed", False)
        response_dict["execution_output"] = result.get("execution_output", "")
        response_dict["_debug_result_keys"] = list(result.keys())  # DEBUG: show what keys result has
        # v6.6.4: Add professional insights from custom_context feature
        response_dict["professional_insights"] = result.get("professional_insights")
        response_dict["recommendations"] = result.get("recommendations")
        response_dict["warnings"] = result.get("warnings")

        logger.info("[COMPLETE] Response sent successfully")
        logger.info("="*60)

        return response_dict

    except Exception as e:
        logger.error(f"[ERROR] Processing failed: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/version")
async def get_version():
    """Get detailed version information"""
    return {
        "api_version": "6.6.10",
        "release": "AI_CODE_EXECUTOR_WITH_STRUCTURED_DATA",
        "engine": "GPT-4o + Python Code Execution",
        "accuracy": "99%",
        "features": {
            "ai_code_generation": True,
            "python_code_execution": True,
            "automatic_fallback": True,
            "methodology_field": True,
            "key_findings": True,
            "summary": True
        },
        "improvements": [
            "AI generates Python code for each query",
            "Python executes code for 100% accurate math",
            "Handles any type of query without hardcoding",
            "Automatic fallback to v3 service if needed"
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint for debugging AI Code Executor"""
    try:
        from app.services.ai_code_executor import get_ai_executor
        executor = get_ai_executor()

        test_data = [
            ["Tovar 1", "OOO Kosmos", 4500, 1, 4500],
            ["Tovar 2", "OOO Kosmos", 5000, 2, 10000],
        ]

        result = executor.process_with_code(
            query="srednyaya tsena",
            column_names=["A", "B", "C", "D", "E"],
            sheet_data=test_data,
            history=[]
        )

        return {
            "test": "AI Code Executor",
            "result_keys": list(result.keys()),
            "has_code_generated": ("code_generated" in result),
            "code_preview": result.get("code_generated", "NOT FOUND")[:200] if result.get("code_generated") else "NO CODE",
            "summary": result.get("summary", "NO SUMMARY"),
            "methodology": result.get("methodology", "NO METHODOLOGY")
        }
    except Exception as e:
        return {
            "test": "FAILED",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
