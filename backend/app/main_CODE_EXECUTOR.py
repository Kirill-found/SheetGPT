"""
SheetGPT API с AI Code Executor
Работает как Formula Bot:
1. AI понимает запрос
2. AI генерирует Python код
3. Python выполняет код
4. Возвращает 100% точный результат
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas.requests import FormulaRequest
from app.services.ai_code_executor import get_ai_executor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SheetGPT Code Executor API",
    version="5.0.0",
    description="AI generates Python code → Executes it → Returns accurate results"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "status": "operational",
        "version": "5.0.0",
        "engine": "AI + Python Code Execution",
        "accuracy": "99%+ (математически точные вычисления)",
        "approach": "AI генерирует код → Python выполняет → Точный результат"
    }

@app.post("/api/v1/formula")
async def process_formula(request: FormulaRequest):
    """
    Обрабатывает запрос через генерацию и выполнение Python кода
    """
    try:
        logger.info(f"Processing query: {request.query}")
        logger.info(f"Data shape: {len(request.sheet_data)} rows x {len(request.column_names)} columns")

        # Используем AI Code Executor
        executor = get_ai_executor()
        result = executor.process_with_code(
            query=request.query,
            column_names=request.column_names,
            sheet_data=request.sheet_data,
            history=request.history or []
        )

        logger.info(f"Result: {result.get('summary', '')[:100]}")
        logger.info(f"Code executed: {result.get('python_executed', False)}")

        return result

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            "error": str(e),
            "summary": f"Ошибка: {str(e)}",
            "methodology": "Ошибка при обработке",
            "confidence": 0.0,
            "response_type": "error"
        }

@app.get("/api/v1/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "engine": "AI Code Executor",
        "capabilities": [
            "Aggregation (GROUP BY, SUM)",
            "Filtering (WHERE conditions)",
            "Calculations (AVG, MIN, MAX, etc)",
            "Complex analytics",
            "Formula generation",
            "Multi-language support"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)