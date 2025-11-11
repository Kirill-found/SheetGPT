"""
SheetGPT API Production v5.0 - AI Code Executor
Генерирует Python код для точных вычислений
Supports structured_data for table/chart creation
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

# Create FastAPI app with VERSION 5.0.0 - AI Code Executor
app = FastAPI(
    title="SheetGPT API",
    version="5.0.0",  # AI Code Executor версия
    description="AI-powered spreadsheet assistant with Python code execution for 99% accuracy"
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
    logger.info("SheetGPT API v5.0.0 STARTING - AI CODE EXECUTOR")
    logger.info(f"Started at: {datetime.now()}")
    logger.info("AI Code Generation: ENABLED")
    logger.info("Python Code Execution: ENABLED")
    logger.info("Accuracy target: 99%")
    logger.info("="*60)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": "SheetGPT API",
        "version": "5.0.0",
        "status": "operational",
        "engine": "AI Code Executor",
        "features": {
            "ai_code_generation": True,
            "python_execution": True,
            "accuracy": "99%",
            "methodology": True,
            "auto_headers": True
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "service": "SheetGPT API",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "ai_service": "operational",
            "python_aggregation": "enabled",
            "response_fields": ["summary", "methodology", "key_findings"]
        }
    }

@app.post("/api/v1/formula", response_model=FormulaResponse)
async def process_formula(request: FormulaRequest):
    """
    Main endpoint - uses AI Code Executor for 99% accuracy
    Fallback to v3 service if Code Executor not available
    """
    try:
        # Log incoming request (без эмодзи для Railway)
        logger.info("="*60)
        logger.info(f"[REQUEST] Query: {request.query}")
        logger.info(f"[DATA] Shape: {len(request.sheet_data)} rows x {len(request.column_names)} columns")

        result = None
        executor_used = False

        # Try to use AI Code Executor first
        try:
            from app.services.ai_code_executor import get_ai_executor
            logger.info("[ENGINE] Using AI Code Executor")

            executor = get_ai_executor()
            result = executor.process_with_code(
                query=request.query,
                column_names=request.column_names,
                sheet_data=request.sheet_data,
                history=request.history
            )
            executor_used = True
            logger.info("[SUCCESS] Code executed successfully")
            logger.info(f"[DEBUG] Result keys: {list(result.keys())}")
            logger.info(f"[DEBUG] Has code_generated: {('code_generated' in result)}")

        except ImportError:
            logger.warning("[FALLBACK] AI Code Executor not found, using v3 service")
            # Fallback to v3 service
            from app.services.ai_service_v3 import get_ai_service
            ai_service = get_ai_service()

            result = ai_service.process_formula_request(
                query=request.query,
                column_names=request.column_names,
                sheet_data=request.sheet_data,
                history=request.history
            )

        except Exception as e:
            logger.error(f"[ERROR] Code Executor failed: {str(e)}")
            # Fallback to v3 service on any error
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
        if executor_used and result.get("python_executed"):
            logger.info("[EXECUTION] Python code executed")

        # Ensure all required fields are present
        response = FormulaResponse(
            formula=result.get("formula"),
            explanation=result.get("explanation", ""),
            target_cell=result.get("target_cell"),
            confidence=result.get("confidence", 0.95 if executor_used else 0.8),
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

        # Add debug fields ALWAYS (for troubleshooting)
        response_dict["code_generated"] = result.get("code_generated", "NOT_IN_RESULT")
        response_dict["python_executed"] = result.get("python_executed", False)
        response_dict["execution_output"] = result.get("execution_output", "")
        response_dict["_debug_result_keys"] = list(result.keys())  # DEBUG: show what keys result has

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
        "api_version": "5.0.0",
        "release": "AI_CODE_EXECUTOR",
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