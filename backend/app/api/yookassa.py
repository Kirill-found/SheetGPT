"""
YooKassa (ЮКасса) Payment Integration API

Для настройки:
1. Зарегистрируйтесь в ЮКассе: https://yookassa.ru/
2. Получите shop_id и secret_key в личном кабинете
3. Установите переменные окружения:
   - YOOKASSA_SHOP_ID
   - YOOKASSA_SECRET_KEY
4. Настройте webhook URL в ЮКассе: https://your-domain.com/api/v1/yookassa/webhook
"""

import logging
import uuid
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/yookassa", tags=["YooKassa Payments"])

# ЮКасса credentials из env
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# Цена PRO подписки
PRO_PRICE = 299  # рублей
PRO_DAYS = 30    # дней


class CreatePaymentRequest(BaseModel):
    telegram_user_id: int
    return_url: Optional[str] = None


class PaymentResponse(BaseModel):
    payment_id: str
    confirmation_url: str
    status: str


@router.post("/create-payment", response_model=PaymentResponse)
async def create_payment(request: CreatePaymentRequest):
    """
    Создать платеж в ЮКассе

    Возвращает ссылку для оплаты, куда нужно перенаправить пользователя.
    После оплаты ЮКасса отправит webhook и PRO активируется автоматически.
    """
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="YooKassa не настроена. Установите YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY"
        )

    try:
        # Используем yookassa SDK
        from yookassa import Configuration, Payment

        Configuration.account_id = YOOKASSA_SHOP_ID
        Configuration.secret_key = YOOKASSA_SECRET_KEY

        # Генерируем уникальный idempotence_key
        idempotence_key = str(uuid.uuid4())

        # Создаем платеж
        payment = Payment.create({
            "amount": {
                "value": str(PRO_PRICE) + ".00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": request.return_url or "https://t.me/SheetGPT_bot"
            },
            "capture": True,
            "description": f"SheetGPT PRO подписка на {PRO_DAYS} дней",
            "metadata": {
                "telegram_user_id": str(request.telegram_user_id),
                "days": str(PRO_DAYS)
            }
        }, idempotence_key)

        logger.info(f"Created YooKassa payment {payment.id} for user {request.telegram_user_id}")

        return PaymentResponse(
            payment_id=payment.id,
            confirmation_url=payment.confirmation.confirmation_url,
            status=payment.status
        )

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="yookassa SDK не установлен. Выполните: pip install yookassa"
        )
    except Exception as e:
        logger.error(f"Failed to create YooKassa payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def yookassa_webhook(request: Request):
    """
    Webhook для обработки уведомлений от ЮКассы

    ЮКасса отправляет POST-запрос когда статус платежа меняется.
    При успешной оплате (status=succeeded) автоматически активируем PRO.

    Настройка в ЮКассе:
    - URL: https://your-domain.com/api/v1/yookassa/webhook
    - События: payment.succeeded, payment.canceled
    """
    try:
        body = await request.json()

        event_type = body.get("event")
        payment_data = body.get("object", {})

        payment_id = payment_data.get("id")
        status = payment_data.get("status")
        metadata = payment_data.get("metadata", {})

        telegram_user_id = metadata.get("telegram_user_id")
        days = int(metadata.get("days", PRO_DAYS))

        logger.info(f"YooKassa webhook: event={event_type}, payment={payment_id}, status={status}, user={telegram_user_id}")

        if event_type == "payment.succeeded" and status == "succeeded":
            if telegram_user_id:
                # Активируем PRO подписку
                success = await activate_pro_subscription(int(telegram_user_id), days, payment_id)
                if success:
                    logger.info(f"PRO activated for user {telegram_user_id} via YooKassa payment {payment_id}")
                else:
                    logger.error(f"Failed to activate PRO for user {telegram_user_id}")
            else:
                logger.warning(f"Payment {payment_id} succeeded but no telegram_user_id in metadata")

        elif event_type == "payment.canceled":
            logger.info(f"Payment {payment_id} was canceled")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"YooKassa webhook error: {e}")
        # Возвращаем 200 чтобы ЮКасса не повторяла запрос
        return {"status": "error", "message": str(e)}


async def activate_pro_subscription(telegram_user_id: int, days: int, payment_id: str) -> bool:
    """
    Активировать PRO подписку для пользователя

    Вызывается автоматически после успешной оплаты через ЮКассу.
    """
    try:
        # Импортируем здесь чтобы избежать циклических импортов
        from app.database import async_session_factory
        from app.models.telegram_user import TelegramUser

        if not async_session_factory:
            logger.error("Database not configured")
            return False

        async with async_session_factory() as session:
            result = await session.execute(
                select(TelegramUser).where(TelegramUser.telegram_user_id == telegram_user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {telegram_user_id} not found in database")
                return False

            # Активируем PRO
            user.subscription_tier = "premium"
            user.queries_limit = -1  # Безлимит
            user.premium_until = datetime.now(timezone.utc) + timedelta(days=days)

            await session.commit()

            logger.info(f"User {telegram_user_id} upgraded to PRO until {user.premium_until}")

            # TODO: Отправить уведомление пользователю в Telegram
            # await send_telegram_notification(telegram_user_id, days)

            return True

    except Exception as e:
        logger.error(f"Failed to activate PRO for user {telegram_user_id}: {e}")
        return False


@router.get("/payment/{payment_id}")
async def get_payment_status(payment_id: str):
    """
    Проверить статус платежа
    """
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        raise HTTPException(status_code=503, detail="YooKassa не настроена")

    try:
        from yookassa import Configuration, Payment

        Configuration.account_id = YOOKASSA_SHOP_ID
        Configuration.secret_key = YOOKASSA_SECRET_KEY

        payment = Payment.find_one(payment_id)

        return {
            "payment_id": payment.id,
            "status": payment.status,
            "amount": payment.amount.value,
            "created_at": payment.created_at,
            "metadata": payment.metadata
        }

    except Exception as e:
        logger.error(f"Failed to get payment status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
