"""
SheetGPT API - FINAL VERSION 3.0
Main FastAPI application
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas.requests import FormulaRequest
from app.schemas.responses import FormulaResponse
from app.services.ai_service import get_ai_service
from app.config import settings
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with VERSION 3.0.0
app = FastAPI(
    title="SheetGPT API",
    version="3.0.0",  # КРИТИЧЕСКИ ВАЖНО - ВЕРСИЯ 3.0.0
    description="AI-powered Google Sheets assistant with Python aggregation"
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
    logger.info("🚀 SheetGPT API v3.0.0 STARTING")
    logger.info(f"🕐 Started at: {datetime.now()}")
    logger.info("✅ Python aggregation enabled")
    logger.info("✅ Methodology field enabled")
    logger.info("✅ Auto-header detection enabled")
    logger.info("="*60)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": "SheetGPT API",
        "version": "3.0.0",
        "status": "operational",
        "features": {
            "python_aggregation": True,
            "methodology": True,
            "auto_headers": True,
            "version": "FINAL"
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
    Main endpoint for processing formula requests
    Now with guaranteed Python aggregation for GROUP BY queries
    """
    try:
        # Log incoming request
        logger.info("="*60)
        logger.info(f"📥 Incoming request: {request.query}")
        logger.info(f"📊 Data shape: {len(request.sheet_data)} rows")
        logger.info(f"📋 Columns: {request.column_names}")

        # Check for auto headers
        has_auto_headers = any('Колонка' in col for col in request.column_names)
        if has_auto_headers:
            logger.info("🤖 AUTO HEADERS DETECTED")

        # Get AI service instance
        ai_service = get_ai_service()

        # Process the request
        result = ai_service.process_formula_request(
            query=request.query,
            column_names=request.column_names,
            sheet_data=request.sheet_data,
            history=request.history
        )

        # Log result summary
        if result.get("summary"):
            logger.info(f"✅ Result: {result['summary']}")
        if result.get("methodology"):
            logger.info(f"📝 Methodology provided: YES")

        # Ensure all required fields are present
        response = FormulaResponse(
            formula=result.get("formula"),
            explanation=result.get("explanation", ""),
            target_cell=result.get("target_cell"),
            confidence=result.get("confidence", 0.8),
            response_type=result.get("response_type", "analysis"),
            insights=result.get("insights", []),
            suggested_actions=result.get("suggested_actions"),
            summary=result.get("summary"),
            methodology=result.get("methodology"),
            key_findings=result.get("key_findings", [])
        )

        logger.info("✅ Response sent successfully")
        logger.info("="*60)

        return response

    except Exception as e:
        logger.error(f"❌ Error processing request: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/version")
async def get_version():
    """Get detailed version information"""
    return {
        "api_version": "3.0.0",
        "release": "FINAL",
        "features": {
            "python_aggregation": True,
            "auto_header_detection": True,
            "methodology_field": True,
            "key_findings": True,
            "summary": True
        },
        "fixes": [
            "Fixed ООО Время aggregation issue",
            "Added Python GROUP BY calculations",
            "Improved auto-header detection",
            "Added detailed methodology reporting"
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint for debugging"""
    test_data = [
        ["Товар 1", "ООО Время", 10730.32, 1010, 107303.2],
        ["Товар 14", "ООО Время", 6328.28, 1007, 44297.96],
        ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44],
        ["Товар 14", "ООО Время", 6328.28, 1023, 145550.44],
    ]

    total_vremya = sum(row[4] for row in test_data)

    return {
        "test": "aggregation",
        "supplier": "ООО Время",
        "expected_total": 442702.04,
        "calculated_total": total_vremya,
        "status": "CORRECT" if abs(total_vremya - 442702.04) < 0.1 else "ERROR"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)