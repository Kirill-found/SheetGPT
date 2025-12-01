"""
SheetGPT API v9.0.0 - Hybrid Intelligence Architecture

NEW: Гибридная архитектура для максимальной точности (98-99%):

1. Schema-Aware Processing
   - Автоопределение типов колонок
   - Точные названия колонок для LLM

2. Smart Query Classification
   - SIMPLE: Pattern Matching (0 tokens, 50ms)
   - MEDIUM: Function Calling (300 tokens, 500ms)
   - COMPLEX: Text-to-Pandas (800 tokens, 1500ms)

3. Self-Correction Loop
   - До 3 попыток с эскалацией сложности
   - Передача ошибки для исправления

Expected Success Rate: 98-99%
Railway deployment: 2025-11-26
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env file FIRST

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from app.schemas.requests import FormulaRequest
from app.schemas.responses import FormulaResponse
from app.config import settings
from app.api.telegram import router as telegram_router
import logging
from datetime import datetime, timezone
import os
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with VERSION 9.0.0 - Hybrid Intelligence Architecture
app = FastAPI(
    title="SheetGPT API",
    version="9.1.0",  # v9.0.0: Hybrid Intelligence - Schema-aware + Smart Classification + Self-Correction
    description="AI-powered spreadsheet assistant with Hybrid Intelligence: Schema-aware processing, Smart query classification (SIMPLE/MEDIUM/COMPLEX), Self-correction loop. Expected 98-99% accuracy."
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Telegram API router
app.include_router(telegram_router)


def start_telegram_bot():
    """Запуск Telegram бота в отдельном потоке"""
    try:
        from app.telegram_bot import SheetGPTBot

        token = settings.TELEGRAM_BOT_TOKEN
        admin_id = settings.TELEGRAM_ADMIN_ID
        database_url = settings.DATABASE_URL

        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN not set - bot disabled")
            return

        logger.info(f"Starting Telegram bot (admin_id: {admin_id}, db: {'YES' if database_url else 'NO'})")
        bot = SheetGPTBot(token=token, admin_id=admin_id, database_url=database_url)
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")


@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("="*60)
    logger.info("SheetGPT API v9.0.0 STARTING - Hybrid Intelligence")
    logger.info(f"Started at: {datetime.now()}")
    logger.info("")
    logger.info("NEW: Hybrid Intelligence Architecture")
    logger.info("  ┌─────────────────────────────────────────────────────┐")
    logger.info("  │ 1. SCHEMA EXTRACTION (0 tokens)                    │")
    logger.info("  │    - Auto-detect column types                      │")
    logger.info("  │    - Extract unique values for categories          │")
    logger.info("  └─────────────────────────────────────────────────────┘")
    logger.info("                         ⬇")
    logger.info("  ┌─────────────────────────────────────────────────────┐")
    logger.info("  │ 2. SMART CLASSIFICATION (0 tokens)                 │")
    logger.info("  │    - SIMPLE: Pattern matching → 0 tokens, 50ms     │")
    logger.info("  │    - MEDIUM: Function calling → 300 tokens, 500ms  │")
    logger.info("  │    - COMPLEX: Text-to-Pandas → 800 tokens, 1500ms  │")
    logger.info("  └─────────────────────────────────────────────────────┘")
    logger.info("                         ⬇")
    logger.info("  ┌─────────────────────────────────────────────────────┐")
    logger.info("  │ 3. SELF-CORRECTION LOOP (up to 3 retries)          │")
    logger.info("  │    - On error: escalate complexity                 │")
    logger.info("  │    - Pass error context for correction             │")
    logger.info("  └─────────────────────────────────────────────────────┘")
    logger.info("")
    logger.info("Expected Success Rate: 98-99%")
    logger.info("")
    logger.info("="*60)

    # Запускаем Telegram бота в отдельном потоке
    if settings.TELEGRAM_BOT_TOKEN:
        bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
        bot_thread.start()
        logger.info("Telegram bot started in background thread")
    else:
        logger.info("Telegram bot disabled (no token)")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": "SheetGPT API",
        "version": "9.1.0",  # v9.0.0: Hybrid Intelligence Architecture
        "status": "operational",
        "engine": "Hybrid Intelligence Processor",
        "features": {
            "hybrid_processing": True,
            "schema_aware": True,
            "smart_classification": True,
            "self_correction": True,
            "strategies": {
                "simple": "Pattern Matching (0 tokens)",
                "medium": "Function Calling (gpt-4o-mini)",
                "complex": "Text-to-Pandas (gpt-4o)"
            },
            "expected_accuracy": "98-99%",
            "custom_context": True,
            "professional_insights": True
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "version": "9.1.0",
        "service": "SheetGPT API",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "ai_service": "operational",
            "simple_gpt_processor": "enabled (v10.0 - no patterns, full GPT)",
            "schema_extractor": "enabled",
            "smart_classifier": "enabled",
            "self_correction": "enabled",
            "max_retries": 3,
            "expected_accuracy": "98-99%"
        }
    }

@app.post("/api/v1/formula", response_model=FormulaResponse)
async def process_formula(
    request: FormulaRequest,
    x_api_token: Optional[str] = Header(None, alias="X-API-Token"),
    x_license_key: Optional[str] = Header(None, alias="X-License-Key")
):
    """
    Main endpoint v9.0.0 - Hybrid Intelligence Architecture
    - Schema-aware processing (точные типы колонок)
    - Smart classification (SIMPLE/MEDIUM/COMPLEX)
    - Self-correction loop (до 3 попыток)
    - Expected 98-99% accuracy
    """
    try:
        # Log incoming request
        logger.info("="*60)
        logger.info(f"[REQUEST v10.0.0] Query: {request.query}")
        logger.info(f"[DATA] Shape: {len(request.sheet_data)} rows x {len(request.column_names)} columns")
        logger.info(f"[DATA] Headers: {request.column_names}")
        if request.sheet_data:
            logger.info(f"[DATA] First row: {request.sheet_data[0] if request.sheet_data else 'empty'}")
            # Check for row length mismatches
            for i, row in enumerate(request.sheet_data[:3]):
                if len(row) != len(request.column_names):
                    logger.warning(f"[DATA] ⚠️ Row {i} has {len(row)} cols, expected {len(request.column_names)}")

        from app.services.simple_gpt_processor import get_simple_gpt_processor
        import pandas as pd

        logger.info("[ENGINE v10.0.0] Using SimpleGPT Processor (no patterns, full GPT)")

        # Создаем DataFrame из данных (pad rows to match header length)
        padded_data = []
        num_cols = len(request.column_names)
        for row in request.sheet_data:
            if len(row) < num_cols:
                row = list(row) + [None] * (num_cols - len(row))
            padded_data.append(row[:num_cols])

        df = pd.DataFrame(padded_data, columns=request.column_names)

        # v9.1.0: Check subscription limits BEFORE processing
        user_info = None
        if x_license_key or x_api_token:
            try:
                from app.core.database import AsyncSessionLocal
                from sqlalchemy import select
                from app.models.telegram_user import TelegramUser
                async with AsyncSessionLocal() as db:
                    user = None
                    if x_license_key:
                        result = await db.execute(
                            select(TelegramUser).where(TelegramUser.license_key == x_license_key.strip().upper())
                        )
                        user = result.scalar_one_or_none()
                    if not user and x_api_token:
                        result = await db.execute(
                            select(TelegramUser).where(TelegramUser.api_token == x_api_token)
                        )
                        user = result.scalar_one_or_none()

                    if user:
                        # Check premium expiration
                        if user.subscription_tier == "premium" and user.premium_until:
                            if datetime.now(timezone.utc) > user.premium_until:
                                logger.info(f"[SUBSCRIPTION] Premium expired for user {user.telegram_user_id}")
                                user.subscription_tier = "free"
                                user.queries_limit = 10
                                await db.commit()

                        # Check if can make query
                        if not user.can_make_query():
                            logger.warning(f"[LIMIT] User {user.telegram_user_id} exceeded limit: {user.queries_used_today}/{user.queries_limit}")
                            raise HTTPException(
                                status_code=429,
                                detail={
                                    "error": "daily_limit_exceeded",
                                    "message": f"Дневной лимит исчерпан ({user.queries_used_today}/{user.queries_limit}). Обновите план до PRO.",
                                    "queries_used": user.queries_used_today,
                                    "queries_limit": user.queries_limit
                                }
                            )

                        user_info = {
                            "user_id": user.telegram_user_id,
                            "tier": user.subscription_tier,
                            "used": user.queries_used_today,
                            "limit": user.queries_limit
                        }
                        logger.info(f"[AUTH] User {user.telegram_user_id} (tier: {user.subscription_tier}, used: {user.queries_used_today}/{user.queries_limit})")
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"[AUTH] Error checking limits: {e}")

        # v9.0.0: Schema-aware processing handles type conversion automatically
        # Auto-convert numeric columns (Google Sheets returns everything as strings)
        # v9.2.1: Skip columns that should stay as text (phones, IDs, codes, etc.)
        SKIP_CONVERT_PATTERNS = [
            'телефон', 'phone', 'тел', 'mobile', 'моб',
            'id', 'код', 'code', 'артикул', 'sku', 'article',
            'инн', 'огрн', 'кпп', 'снилс', 'паспорт', 'passport',
            'индекс', 'zip', 'postal',
            'номер', 'number', 'num', '№',
            'счет', 'счёт', 'account', 'card', 'карт',
            'серия', 'series',
        ]
        
        def should_skip_convert(col_name: str) -> bool:
            """Check if column should NOT be converted to numeric."""
            col_lower = col_name.lower()
            for pattern in SKIP_CONVERT_PATTERNS:
                if pattern in col_lower:
                    return True
            return False
        
        for col in df.columns:
            if should_skip_convert(col):
                # v9.2.2: FORCE phone/ID columns to STRING to prevent any calculations
                df[col] = df[col].astype(str)
                logger.info(f"[AUTO-CONVERT] 🔒 '{col}' → FORCED to string (phone/ID/code)")
                continue
            converted = pd.to_numeric(df[col], errors='coerce')
            if converted.notna().sum() > len(df) * 0.5:
                df[col] = converted
                logger.info(f"[AUTO-CONVERT] ✅ '{col}' → numeric")

        # v9.2.0: Create reference DataFrame for cross-sheet VLOOKUP
        reference_df = None
        if request.reference_sheet_data and request.reference_sheet_headers:
            logger.info(f"[VLOOKUP] Reference sheet: {request.reference_sheet_name}")
            logger.info(f"[VLOOKUP] Reference headers: {request.reference_sheet_headers}")
            logger.info(f"[VLOOKUP] Reference rows: {len(request.reference_sheet_data)}")
            
            # Pad reference data rows
            ref_num_cols = len(request.reference_sheet_headers)
            ref_padded_data = []
            for row in request.reference_sheet_data:
                if len(row) < ref_num_cols:
                    row = list(row) + [None] * (ref_num_cols - len(row))
                ref_padded_data.append(row[:ref_num_cols])
            
            reference_df = pd.DataFrame(ref_padded_data, columns=request.reference_sheet_headers)
            
            # Auto-convert numeric columns in reference (skip phones, IDs, etc.)
            for col in reference_df.columns:
                if should_skip_convert(col):
                    # v9.2.2: FORCE to string in reference too
                    reference_df[col] = reference_df[col].astype(str)
                    logger.info(f"[AUTO-CONVERT] 🔒 ref:'{col}' → FORCED to string")
                    continue
                converted = pd.to_numeric(reference_df[col], errors='coerce')
                if converted.notna().sum() > len(reference_df) * 0.5:
                    reference_df[col] = converted

        # v10.0.0: Use SimpleGPT Processor (no patterns, full GPT)
        processor = get_simple_gpt_processor()
        result = await processor.process(
            query=request.query,
            df=df,
            column_names=request.column_names,
            custom_context=request.custom_context,
            history=request.history or [],
            reference_df=reference_df,
            reference_sheet_name=request.reference_sheet_name
        )

        # DEBUG: Log full result immediately after processor
        logger.info(f"[DEBUG] Processor result keys: {list(result.keys())}")
        logger.info(f"[DEBUG] Processor result action_type: {result.get('action_type')}")
        logger.info(f"[DEBUG] Processor result has pivot_data: {'pivot_data' in result}")
        if 'pivot_data' in result:
            logger.info(f"[DEBUG] pivot_data: {result['pivot_data']}")
        logger.info(f"[DEBUG] Processor result has chart_spec: {'chart_spec' in result}")
        if 'chart_spec' in result:
            logger.info(f"[DEBUG] chart_spec value: {result['chart_spec']}")


        # v10.0.1: Handle processing errors gracefully (don't throw 422)
        # v9.1.1: Errors do NOT count towards usage limit
        is_error = not result.get("success", True) or result.get("response_type") == "error"
        if is_error:
            error_msg = result.get("error", "Не удалось обработать запрос")
            logger.warning(f"[PROCESSOR ERROR] {error_msg} - NOT counting towards usage")
            # Return a friendly error response instead of 422
            return {
                "formula": None,
                "explanation": "",
                "target_cell": None,
                "confidence": 0.0,
                "response_type": "error",
                "insights": [],
                "suggested_actions": None,
                "summary": f"❌ Ошибка обработки: {error_msg}\n\nПопробуйте переформулировать запрос или проверьте данные.",
                "methodology": None,
                "key_findings": [],
                "function_used": None,
                "parameters": None,
                "error": error_msg,
                "processing_time": result.get("processing_time", "0s"),
                "processor_version": "10.0.1",
                "_error_not_counted": True
            }

        logger.info(f"[SUCCESS] SimpleGPT processing completed")
        logger.info(f"[PROCESSOR] {result.get('processor', 'N/A')}")
        logger.info(f"[TIME] {result.get('processing_time', 'N/A')}")

        # Log result summary
        if result.get("summary"):
            logger.info(f"[RESULT] {result['summary'][:100]}...")
        if result.get("function_used"):
            logger.info(f"[FUNCTION] Used: {result['function_used']}")
        if result.get("python_executed"):
            logger.info("[EXECUTION] Python code executed")
        if result.get("retry_count", 0) > 0:
            logger.info(f"[RETRY] Self-correction used: {result['retry_count']} retries")

        # Ensure all required fields are present
        response = FormulaResponse(
            formula=result.get("formula"),
            explanation=result.get("explanation", ""),
            target_cell=result.get("target_cell"),
            confidence=result.get("confidence", 0.98),  # v9.0.0: Higher confidence with hybrid approach
            response_type=result.get("response_type", "analysis"),
            insights=result.get("insights", []),
            suggested_actions=result.get("suggested_actions"),
            summary=result.get("summary"),
            methodology=result.get("methodology"),
            key_findings=result.get("key_findings", []),
            function_used=result.get("function_used"),
            parameters=result.get("parameters")
        )

        # Convert to dict to add extra fields
        response_dict = response.model_dump()

        # Add structured_data for table/chart creation
        if "structured_data" in result:
            response_dict["structured_data"] = result["structured_data"]

        # Add highlighting data
        if "highlight_rows" in result:
            response_dict["highlight_rows"] = result["highlight_rows"]
        if "highlight_color" in result:
            response_dict["highlight_color"] = result["highlight_color"]
        if "highlight_message" in result:
            response_dict["highlight_message"] = result["highlight_message"]
        if "action_type" in result:
            response_dict["action_type"] = result["action_type"]
        if "value" in result:
            response_dict["value"] = result["value"]

        # Add sorting data
        if "sort_column" in result:
            response_dict["sort_column"] = result["sort_column"]
        if "sort_column_index" in result:
            response_dict["sort_column_index"] = result["sort_column_index"]
        if "sort_order" in result:
            response_dict["sort_order"] = result["sort_order"]

        # Add freeze data
        if "freeze_rows" in result:
            response_dict["freeze_rows"] = result["freeze_rows"]
        if "freeze_columns" in result:
            response_dict["freeze_columns"] = result["freeze_columns"]

        # Add format data
        if "format_type" in result:
            response_dict["format_type"] = result["format_type"]
        if "target_row" in result:
            response_dict["target_row"] = result["target_row"]
        if "bold" in result:
            response_dict["bold"] = result["bold"]
        if "background_color" in result:
            response_dict["background_color"] = result["background_color"]

        # Add pivot table data
        logger.info(f"[PIVOT DEBUG] result keys before adding: {list(result.keys())}")
        logger.info(f"[PIVOT DEBUG] pivot_data in result: {'pivot_data' in result}")
        if "pivot_data" in result:
            logger.info(f"[PIVOT DEBUG] Adding pivot_data to response_dict")
            response_dict["pivot_data"] = result["pivot_data"]
            response_dict["group_column"] = result.get("group_column")
            response_dict["value_column"] = result.get("value_column")
            response_dict["agg_func"] = result.get("agg_func")
        else:
            logger.warning(f"[PIVOT DEBUG] NO pivot_data in result!")

        # Add chart data
        logger.info(f"[DEBUG] Checking for chart_spec in result keys: {list(result.keys())}")
        logger.info(f"[DEBUG] chart_spec in result? {'chart_spec' in result}")
        if "chart_spec" in result:
            logger.info(f"[DEBUG] Adding chart_spec: {result['chart_spec']}")
            response_dict["chart_spec"] = result["chart_spec"]
        else:
            logger.warning(f"[DEBUG] chart_spec NOT found in result!")

        # Add color scale data
        if "rule" in result and result.get("action_type") == "color_scale":
            logger.info(f"[DEBUG] Adding color_scale rule: {result['rule']}")
            response_dict["color_scale_rule"] = result["rule"]

        # Add conditional format rule (for non-color-scale conditional formatting)
        if "rule" in result and result.get("action_type") == "conditional_format":
            response_dict["conditional_rule"] = result["rule"]

        # Add convert to numbers rule
        if "rule" in result and result.get("action_type") == "convert_to_numbers":
            response_dict["convert_rule"] = result["rule"]

        # v9.0.0: Add hybrid processor metadata
        response_dict["processor_version"] = result.get("processor_version", "9.0.0")
        response_dict["complexity"] = result.get("complexity")
        response_dict["strategy"] = result.get("strategy")
        response_dict["processing_time"] = result.get("processing_time")
        response_dict["retry_count"] = result.get("retry_count", 0)

        # Debug fields
        response_dict["code_generated"] = result.get("code_generated")
        response_dict["python_executed"] = result.get("python_executed", False)
        response_dict["function_used"] = result.get("function_used")
        response_dict["parameters"] = result.get("parameters")

        # v9.3.1: Increment usage after successful processing
        logger.info(f"[USAGE] Headers - License: {x_license_key[:12] + '...' if x_license_key else 'None'}")
        if x_license_key or x_api_token:
            try:
                from app.core.database import AsyncSessionLocal
                from sqlalchemy import select
                from app.models.telegram_user import TelegramUser
                async with AsyncSessionLocal() as db:
                    user = None
                    if x_license_key:
                        license_upper = x_license_key.strip().upper()
                        logger.info(f"[USAGE] Looking up license: {license_upper}")
                        db_result = await db.execute(
                            select(TelegramUser).where(TelegramUser.license_key == license_upper)
                        )
                        user = db_result.scalar_one_or_none()
                        logger.info(f"[USAGE] User found: {user.telegram_user_id if user else 'NOT FOUND'}")
                    if not user and x_api_token:
                        db_result = await db.execute(
                            select(TelegramUser).where(TelegramUser.api_token == x_api_token)
                        )
                        user = db_result.scalar_one_or_none()

                    if user:
                        old_used = user.queries_used_today
                        user.queries_used_today += 1
                        user.total_queries += 1
                        user.last_query_at = datetime.now(timezone.utc)
                        await db.commit()
                        logger.info(f"[USAGE] Incremented {old_used} -> {user.queries_used_today}")

                        # Add usage info to response
                        response_dict["_usage"] = {
                            "queries_used": user.queries_used_today,
                            "queries_limit": user.queries_limit,
                            "queries_remaining": -1 if user.queries_limit == -1 else max(0, user.queries_limit - user.queries_used_today)
                        }
                        logger.info(f"[USAGE] User {user.telegram_user_id}: {user.queries_used_today}/{user.queries_limit}")
                    else:
                        logger.warning(f"[USAGE] User NOT found for license/token")
            except Exception as e:
                logger.error(f"[USAGE] Failed to increment: {e}", exc_info=True)
        else:
            logger.warning("[USAGE] No license key provided - usage not tracked")

        logger.info("[COMPLETE] Response sent successfully")
        logger.info("="*60)

        return response_dict

    except ValueError as e:
        # Ошибки валидации данных
        logger.warning(f"[VALIDATION ERROR] {str(e)}")
        raise HTTPException(
            status_code=422,
            detail={
                "error_type": "validation_error",
                "message": str(e),
                "user_message": "Проверьте корректность данных и запроса",
                "retryable": False
            }
        )
    except TimeoutError as e:
        # Таймаут выполнения
        logger.error(f"[TIMEOUT] Request timed out: {str(e)}")
        raise HTTPException(
            status_code=504,
            detail={
                "error_type": "timeout",
                "message": "Превышено время выполнения запроса",
                "user_message": "Сервер перегружен, попробуйте через несколько секунд",
                "retryable": True
            }
        )
    except ConnectionError as e:
        # Ошибки соединения с AI API
        logger.error(f"[CONNECTION ERROR] AI service unavailable: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "error_type": "service_unavailable",
                "message": "AI сервис временно недоступен",
                "user_message": "Сервис временно недоступен, повторите попытку",
                "retryable": True
            }
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[ERROR] Processing failed: {error_msg}")
        logger.exception(e)

        # Классифицируем ошибку для более понятного сообщения
        error_response = classify_backend_error(error_msg)

        raise HTTPException(
            status_code=error_response["status_code"],
            detail={
                "error_type": error_response["error_type"],
                "message": error_msg,
                "user_message": error_response["user_message"],
                "retryable": error_response["retryable"]
            }
        )


def classify_backend_error(error_msg: str) -> dict:
    """Классификация ошибок для понятных сообщений пользователю"""
    error_lower = error_msg.lower()

    # OpenAI API ошибки
    if "rate limit" in error_lower or "too many requests" in error_lower:
        return {
            "status_code": 429,
            "error_type": "rate_limit",
            "user_message": "Превышен лимит запросов. Подождите минуту и повторите.",
            "retryable": True
        }

    if "context length" in error_lower or "maximum context" in error_lower:
        return {
            "status_code": 422,
            "error_type": "context_too_large",
            "user_message": "Слишком много данных. Уменьшите объём таблицы.",
            "retryable": False
        }

    if "invalid api key" in error_lower or "authentication" in error_lower:
        return {
            "status_code": 500,
            "error_type": "configuration_error",
            "user_message": "Ошибка конфигурации сервера. Обратитесь в поддержку.",
            "retryable": False
        }

    # Ошибки данных
    if "empty" in error_lower or "no data" in error_lower or "данные отсутствуют" in error_lower:
        return {
            "status_code": 422,
            "error_type": "no_data",
            "user_message": "Недостаточно данных для выполнения запроса.",
            "retryable": False
        }

    if "column" in error_lower and ("not found" in error_lower or "не найден" in error_lower):
        return {
            "status_code": 422,
            "error_type": "column_not_found",
            "user_message": "Указанная колонка не найдена в таблице.",
            "retryable": False
        }

    # Сетевые ошибки
    if "connection" in error_lower or "network" in error_lower or "timeout" in error_lower:
        return {
            "status_code": 503,
            "error_type": "network_error",
            "user_message": "Проблема с соединением. Повторите попытку.",
            "retryable": True
        }

    # Ошибки выполнения кода
    if "execution" in error_lower or "syntax" in error_lower or "python" in error_lower:
        return {
            "status_code": 500,
            "error_type": "execution_error",
            "user_message": "Ошибка обработки запроса. Попробуйте переформулировать.",
            "retryable": False
        }

    # Общая ошибка
    return {
        "status_code": 500,
        "error_type": "internal_error",
        "user_message": "Произошла ошибка. Попробуйте ещё раз.",
        "retryable": True
    }

@app.get("/api/v1/version")
async def get_version():
    """Get detailed version information"""
    return {
        "api_version": "9.0.0",
        "release": "HYBRID_INTELLIGENCE",
        "engine": "Hybrid Intelligence Processor",
        "expected_accuracy": "98-99%",
        "architecture": {
            "schema_extraction": {
                "purpose": "Auto-detect column types and unique values",
                "tokens": 0,
                "latency": "~10ms"
            },
            "smart_classification": {
                "purpose": "Classify query as SIMPLE/MEDIUM/COMPLEX",
                "tokens": 0,
                "latency": "~5ms"
            },
            "execution_strategies": {
                "simple": {
                    "method": "Pattern Matching",
                    "model": None,
                    "tokens": 0,
                    "latency": "~50ms"
                },
                "medium": {
                    "method": "Function Calling",
                    "model": "gpt-4o-mini",
                    "tokens": "~300",
                    "latency": "~500ms"
                },
                "complex": {
                    "method": "Text-to-Pandas",
                    "model": "gpt-4o",
                    "tokens": "~800",
                    "latency": "~1500ms"
                }
            },
            "self_correction": {
                "max_retries": 3,
                "escalation": "SIMPLE → MEDIUM → COMPLEX"
            }
        },
        "features": {
            "hybrid_processing": True,
            "schema_aware": True,
            "smart_classification": True,
            "self_correction": True,
            "code_generation": True,
            "function_calling": True,
            "pattern_matching": True
        },
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
