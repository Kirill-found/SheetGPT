"""
API endpoints для Telegram бота
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.telegram_user import TelegramUser
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/telegram", tags=["telegram"])


# Request/Response модели
class TelegramUserRegister(BaseModel):
    telegram_user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class TelegramUserResponse(BaseModel):
    telegram_user_id: int
    username: Optional[str]
    api_token: str
    subscription_tier: str
    queries_used_today: int
    queries_limit: int
    total_queries: int
    is_active: bool


class QueryRequest(BaseModel):
    query: str
    column_names: List[str]
    sheet_data: List[List]


class QueryResponse(BaseModel):
    success: bool
    data: dict
    queries_remaining: int
    message: Optional[str] = None


class SubscriptionStatus(BaseModel):
    subscription_tier: str
    queries_used_today: int
    queries_limit: int
    total_queries: int
    is_premium: bool
    premium_until: Optional[datetime] = None


async def get_telegram_user_by_token(api_token: str, db: AsyncSession) -> TelegramUser:
    """Получить пользователя по API токену"""
    result = await db.execute(
        select(TelegramUser).where(TelegramUser.api_token == api_token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid API token")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    return user


@router.post("/register", response_model=TelegramUserResponse)
async def register_telegram_user(
    user_data: TelegramUserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Регистрация нового Telegram пользователя или получение существующего
    """
    logger.info(f"Registering Telegram user: {user_data.telegram_user_id}")

    # Проверяем, существует ли пользователь
    result = await db.execute(
        select(TelegramUser).where(TelegramUser.telegram_user_id == user_data.telegram_user_id)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Обновляем информацию о пользователе
        if user_data.username:
            existing_user.username = user_data.username
        if user_data.first_name:
            existing_user.first_name = user_data.first_name
        if user_data.last_name:
            existing_user.last_name = user_data.last_name
        existing_user.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(existing_user)

        logger.info(f"Updated existing user: {existing_user.telegram_user_id}")
        return TelegramUserResponse(
            telegram_user_id=existing_user.telegram_user_id,
            username=existing_user.username,
            api_token=existing_user.api_token,
            subscription_tier=existing_user.subscription_tier,
            queries_used_today=existing_user.queries_used_today,
            queries_limit=existing_user.queries_limit,
            total_queries=existing_user.total_queries,
            is_active=existing_user.is_active
        )

    # Создаем нового пользователя
    new_user = TelegramUser(
        telegram_user_id=user_data.telegram_user_id,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        api_token=TelegramUser.generate_api_token(),
        subscription_tier="free",
        queries_used_today=0,
        queries_limit=10,
        total_queries=0,
        is_active=True
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"Created new user: {new_user.telegram_user_id}")

    return TelegramUserResponse(
        telegram_user_id=new_user.telegram_user_id,
        username=new_user.username,
        api_token=new_user.api_token,
        subscription_tier=new_user.subscription_tier,
        queries_used_today=new_user.queries_used_today,
        queries_limit=new_user.queries_limit,
        total_queries=new_user.total_queries,
        is_active=new_user.is_active
    )


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    api_token: str = Header(..., alias="X-API-Token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статус подписки пользователя
    """
    user = await get_telegram_user_by_token(api_token, db)

    is_premium = user.subscription_tier == "premium"
    if is_premium and user.premium_until:
        # Проверяем, не истекла ли подписка
        if datetime.now(timezone.utc) > user.premium_until:
            is_premium = False
            user.subscription_tier = "free"
            user.queries_limit = 10
            await db.commit()

    return SubscriptionStatus(
        subscription_tier=user.subscription_tier,
        queries_used_today=user.queries_used_today,
        queries_limit=user.queries_limit,
        total_queries=user.total_queries,
        is_premium=is_premium,
        premium_until=user.premium_until
    )


@router.post("/query", response_model=QueryResponse)
async def process_query(
    query_request: QueryRequest,
    api_token: str = Header(..., alias="X-API-Token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Обработка запроса к таблице через SheetGPT API
    Проверяет лимиты и отправляет запрос в основной API
    """
    user = await get_telegram_user_by_token(api_token, db)

    # Проверяем лимиты
    if not user.can_make_query():
        queries_limit = "unlimited" if user.subscription_tier == "premium" else user.queries_limit
        raise HTTPException(
            status_code=429,
            detail=f"Query limit exceeded. Used: {user.queries_used_today}/{queries_limit}. "
                   f"Upgrade to Premium for unlimited queries."
        )

    # Отправляем запрос в основной SheetGPT API
    try:
        import requests

        sheetgpt_api_url = "http://localhost:8080/api/v1/formula"

        response = requests.post(
            sheetgpt_api_url,
            json={
                "query": query_request.query,
                "column_names": query_request.column_names,
                "sheet_data": query_request.sheet_data
            },
            timeout=60
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"SheetGPT API error: {response.status_code}"
            )

        result_data = response.json()

        # Увеличиваем счетчик использования
        user.increment_usage()
        await db.commit()

        queries_remaining = -1  # Unlimited for premium
        if user.subscription_tier == "free":
            queries_remaining = user.queries_limit - user.queries_used_today

        logger.info(f"Query processed for user {user.telegram_user_id}. "
                   f"Remaining: {queries_remaining}")

        return QueryResponse(
            success=True,
            data=result_data,
            queries_remaining=queries_remaining,
            message="Query processed successfully"
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling SheetGPT API: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )


@router.post("/upgrade-premium")
async def upgrade_to_premium(
    api_token: str = Header(..., alias="X-API-Token"),
    duration_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Upgrade пользователя до Premium подписки
    (В MVP вызывается вручную админом)
    """
    user = await get_telegram_user_by_token(api_token, db)

    from datetime import timedelta

    user.subscription_tier = "premium"
    user.queries_limit = -1  # Unlimited
    user.premium_until = datetime.now(timezone.utc) + timedelta(days=duration_days)

    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user.telegram_user_id} upgraded to premium until {user.premium_until}")

    return {
        "success": True,
        "message": f"Upgraded to Premium for {duration_days} days",
        "premium_until": user.premium_until
    }


@router.post("/admin/set-premium")
async def admin_set_premium(
    telegram_user_id: int,
    admin_key: str = Header(...),
    duration_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Админский endpoint для установки Premium подписки по telegram_user_id
    """
    if admin_key != "sheetgpt_admin_2025":
        raise HTTPException(status_code=403, detail="Invalid admin key")

    result = await db.execute(
        select(TelegramUser).where(TelegramUser.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {telegram_user_id} not found")

    # Используем метод модели для корректного обновления всех полей
    user.upgrade_to_premium(duration_days=duration_days)

    await db.commit()
    await db.refresh(user)

    logger.info(f"[ADMIN] User {telegram_user_id} set to premium until {user.premium_until}")

    return {
        "success": True,
        "message": f"User {telegram_user_id} upgraded to Premium for {duration_days} days",
        "user": {
            "telegram_user_id": user.telegram_user_id,
            "username": user.username,
            "subscription_tier": user.subscription_tier,
            "premium_until": user.premium_until
        }
    }


@router.post("/reset-daily-limits")
async def reset_daily_limits(
    admin_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Сброс дневных лимитов для всех пользователей
    (Вызывается ежедневно через cron)
    """
    # Простая проверка админского ключа
    if admin_key != "sheetgpt_admin_2025":  # TODO: Использовать env variable
        raise HTTPException(status_code=403, detail="Invalid admin key")

    result = await db.execute(select(TelegramUser))
    users = result.scalars().all()

    for user in users:
        user.reset_daily_usage()

    await db.commit()

    logger.info(f"Reset daily limits for {len(users)} users")

    return {
        "success": True,
        "message": f"Reset daily limits for {len(users)} users"
    }


# ==================== LICENSE ENDPOINTS ====================

class LicenseGenerateRequest(BaseModel):
    telegram_user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None


class LicenseResponse(BaseModel):
    success: bool
    license_key: Optional[str] = None
    message: str
    telegram_user_id: Optional[int] = None
    subscription_tier: Optional[str] = None
    # Дополнительные данные для Chrome Extension
    username: Optional[str] = None
    first_name: Optional[str] = None
    queries_used_today: Optional[int] = None
    queries_limit: Optional[int] = None
    total_queries: Optional[int] = None
    premium_until: Optional[datetime] = None  # v9.1.0: Premium subscription expiration


@router.post("/license/generate", response_model=LicenseResponse)
async def generate_license_key(
    request: LicenseGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Генерация лицензионного ключа для пользователя.
    Вызывается из Telegram бота при нажатии "Сгенерировать ключ".
    """
    logger.info(f"Generating license for user: {request.telegram_user_id}")

    # Ищем или создаём пользователя
    result = await db.execute(
        select(TelegramUser).where(TelegramUser.telegram_user_id == request.telegram_user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Создаём нового пользователя
        user = TelegramUser(
            telegram_user_id=request.telegram_user_id,
            username=request.username,
            first_name=request.first_name,
            api_token=TelegramUser.generate_api_token(),
            license_key=TelegramUser.generate_license_key(),
            subscription_tier="free",
            queries_used_today=0,
            queries_limit=10,
            total_queries=0,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Created new user with license: {user.license_key}")
    else:
        # Генерируем новый ключ для существующего пользователя
        user.license_key = TelegramUser.generate_license_key()
        user.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Updated license for user: {user.license_key}")

    return LicenseResponse(
        success=True,
        license_key=user.license_key,
        message="License key generated successfully",
        telegram_user_id=user.telegram_user_id,
        subscription_tier=user.subscription_tier
    )


@router.get("/license/validate/{license_key}", response_model=LicenseResponse)
async def validate_license_key(
    license_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Проверка лицензионного ключа.
    Вызывается из Chrome Extension при активации.
    """
    logger.info(f"Validating license: {license_key}")

    # Нормализуем ключ (убираем пробелы, приводим к верхнему регистру)
    license_key = license_key.strip().upper()

    result = await db.execute(
        select(TelegramUser).where(TelegramUser.license_key == license_key)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"License not found: {license_key}")
        return LicenseResponse(
            success=False,
            license_key=license_key,
            message="License key not found"
        )

    if not user.is_active:
        logger.warning(f"License inactive: {license_key}")
        return LicenseResponse(
            success=False,
            license_key=license_key,
            message="License key is inactive"
        )

    # v9.1.0: Check premium expiration
    if user.subscription_tier == "premium" and user.premium_until:
        if datetime.now(timezone.utc) > user.premium_until:
            logger.info(f"Premium expired for user {user.telegram_user_id}")
            user.subscription_tier = "free"
            user.queries_limit = 10
            await db.commit()

    logger.info(f"License valid: {license_key} for user {user.telegram_user_id}, used={user.queries_used_today}/{user.queries_limit}")
    return LicenseResponse(
        success=True,
        license_key=license_key,
        message="License key is valid",
        telegram_user_id=user.telegram_user_id,
        subscription_tier=user.subscription_tier,
        username=user.username,
        first_name=user.first_name,
        queries_used_today=user.queries_used_today,
        queries_limit=user.queries_limit,
        total_queries=user.total_queries,
        premium_until=user.premium_until
    )


class ActivateLicenseRequest(BaseModel):
    license_key: str


@router.post("/activate-license", response_model=LicenseResponse)
async def activate_license(
    request: ActivateLicenseRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Активация лицензионного ключа (POST версия для Chrome Extension).
    Принимает JSON: {"license_key": "XXXX-XXXX-XXXX-XXXX"}
    """
    license_key = request.license_key.strip().upper()
    logger.info(f"Activating license (POST): {license_key}")

    result = await db.execute(
        select(TelegramUser).where(TelegramUser.license_key == license_key)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"License not found: {license_key}")
        return LicenseResponse(
            success=False,
            license_key=license_key,
            message="License key not found"
        )

    if not user.is_active:
        logger.warning(f"License inactive: {license_key}")
        return LicenseResponse(
            success=False,
            license_key=license_key,
            message="License key is inactive"
        )

    # v9.1.0: Check premium expiration
    if user.subscription_tier == "premium" and user.premium_until:
        if datetime.now(timezone.utc) > user.premium_until:
            user.subscription_tier = "free"
            user.queries_limit = 10
            await db.commit()

    logger.info(f"License activated: {license_key} for user {user.telegram_user_id}")
    return LicenseResponse(
        success=True,
        license_key=license_key,
        message="License activated successfully",
        telegram_user_id=user.telegram_user_id,
        subscription_tier=user.subscription_tier,
        username=user.username,
        first_name=user.first_name,
        queries_used_today=user.queries_used_today,
        queries_limit=user.queries_limit,
        total_queries=user.total_queries,
        premium_until=user.premium_until
    )


class UsageIncrementResponse(BaseModel):
    success: bool
    queries_used_today: int
    queries_limit: int
    queries_remaining: int
    can_make_query: bool
    message: str


@router.post("/license/{license_key}/increment-usage", response_model=UsageIncrementResponse)
async def increment_usage_by_license(
    license_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Увеличить счётчик использования по лицензионному ключу.
    Вызывается из Chrome Extension после каждого запроса.
    """
    license_key = license_key.strip().upper()
    logger.info(f"Incrementing usage for license: {license_key}")

    result = await db.execute(
        select(TelegramUser).where(TelegramUser.license_key == license_key)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="License not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="License inactive")

    # Определяем, является ли пользователь premium/unlimited
    is_unlimited = (
        user.subscription_tier == "premium" or
        user.queries_limit == -1
    )

    # Проверяем лимит перед инкрементом
    if not user.can_make_query():
        queries_remaining = -1 if is_unlimited else max(0, user.queries_limit - user.queries_used_today)
        return UsageIncrementResponse(
            success=False,
            queries_used_today=user.queries_used_today,
            queries_limit=user.queries_limit,
            queries_remaining=queries_remaining,
            can_make_query=False,
            message="Daily limit exceeded"
        )

    # Инкрементим использование
    user.increment_usage()
    await db.commit()
    await db.refresh(user)

    queries_remaining = -1 if is_unlimited else max(0, user.queries_limit - user.queries_used_today)

    logger.info(f"Usage incremented for {license_key}: {user.queries_used_today}/{user.queries_limit}")

    return UsageIncrementResponse(
        success=True,
        queries_used_today=user.queries_used_today,
        queries_limit=user.queries_limit,
        queries_remaining=queries_remaining,
        can_make_query=user.can_make_query(),
        message="Usage incremented"
    )


@router.get("/license/{license_key}/status", response_model=LicenseResponse)
async def get_status_by_license(
    license_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить текущий статус пользователя по лицензионному ключу.
    """
    license_key = license_key.strip().upper()

    result = await db.execute(
        select(TelegramUser).where(TelegramUser.license_key == license_key)
    )
    user = result.scalar_one_or_none()

    if not user:
        return LicenseResponse(
            success=False,
            message="License not found"
        )

    return LicenseResponse(
        success=True,
        license_key=license_key,
        message="Status retrieved",
        telegram_user_id=user.telegram_user_id,
        subscription_tier=user.subscription_tier,
        username=user.username,
        first_name=user.first_name,
        queries_used_today=user.queries_used_today,
        queries_limit=user.queries_limit,
        total_queries=user.total_queries
    )


@router.get("/license/user/{telegram_user_id}", response_model=LicenseResponse)
async def get_user_license(
    telegram_user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить лицензионный ключ пользователя по telegram_user_id.
    """
    result = await db.execute(
        select(TelegramUser).where(TelegramUser.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.license_key:
        return LicenseResponse(
            success=False,
            message="No license found for this user"
        )

    return LicenseResponse(
        success=True,
        license_key=user.license_key,
        message="License found",
        telegram_user_id=user.telegram_user_id,
        subscription_tier=user.subscription_tier
    )


@router.get("/test-db")
async def test_database_connection(db: AsyncSession = Depends(get_db)):
    """
    Тестовый эндпоинт для проверки подключения к БД
    Возвращает детальную информацию об ошибке
    """
    try:
        # Пробуем выполнить простой запрос
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1"))
        row = result.fetchone()

        return {
            "success": True,
            "message": "Database connection OK",
            "result": row[0] if row else None
        }
    except Exception as e:
        import traceback
        error_details = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        logger.error(f"Database connection test failed: {error_details}")
        return error_details


@router.post("/init-db")
async def init_telegram_database(
    admin_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать таблицу telegram_users в базе данных
    (Вызывается один раз при первом деплое)
    """
    # Простая проверка админского ключа
    if admin_key != "sheetgpt_admin_2025":  # TODO: Использовать env variable
        raise HTTPException(status_code=403, detail="Invalid admin key")

    try:
        # Import model
        from app.core.database import engine, Base
        from app.models import telegram_user

        # Create table
        async with engine.begin() as conn:
            await conn.run_sync(TelegramUser.__table__.create, checkfirst=True)

        logger.info("telegram_users table created successfully")

        return {
            "success": True,
            "message": "telegram_users table created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create telegram_users table: {e}")
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.post("/migrate-license-key")
async def migrate_license_key_column(
    admin_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Добавить колонку license_key в таблицу telegram_users
    (Миграция для существующей таблицы)
    """
    if admin_key != "sheetgpt_admin_2025":
        raise HTTPException(status_code=403, detail="Invalid admin key")

    try:
        from sqlalchemy import text

        # Добавляем колонку если её нет
        await db.execute(text("""
            ALTER TABLE telegram_users
            ADD COLUMN IF NOT EXISTS license_key VARCHAR(19) UNIQUE
        """))
        await db.commit()

        # Создаём индекс
        try:
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_telegram_users_license_key
                ON telegram_users(license_key)
            """))
            await db.commit()
        except Exception:
            pass  # Индекс уже существует

        logger.info("license_key column added successfully")

        return {
            "success": True,
            "message": "license_key column added successfully"
        }
    except Exception as e:
        logger.error(f"Failed to add license_key column: {e}")
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
