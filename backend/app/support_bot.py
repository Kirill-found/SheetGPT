"""
SheetGPT Support Bot - Бот поддержки для пользователей

Функции:
- Оплата подписки PRO через ЮКасса
- Вопросы в поддержку
- Информация о тарифах
"""

import logging
import asyncio
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ADMIN_TELEGRAM_ID = 517682186
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
PRO_PRICE = 299
PRO_DAYS = 30


class SheetGPTSupportBot:
    """Бот поддержки для SheetGPT"""

    def __init__(self, token: str, main_bot_token: str, database_url: str, payment_token: str = None):
        self.token = token
        self.main_bot_token = main_bot_token
        self.database_url = database_url
        self.payment_token = payment_token
        self.application = None
        self.async_engine = None
        self.async_session_factory = None

    def _init_db(self):
        """Инициализация подключения к БД"""
        if self.database_url:
            db_url = self.database_url
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            self.async_engine = create_async_engine(db_url, echo=False)
            self.async_session_factory = sessionmaker(self.async_engine, class_=AsyncSession, expire_on_commit=False)
            logger.info("Support bot DB connection initialized")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started support bot")
        is_admin = user.id == ADMIN_TELEGRAM_ID

        text = f"""
Привет, {user.first_name}! 👋

Добро пожаловать в **Поддержку SheetGPT**!

Здесь вы можете:
• 💳 Оплатить PRO подписку
• ❓ Задать вопрос в поддержку
• 📋 Узнать о тарифах

Выберите действие:
"""
        keyboard = [
            [InlineKeyboardButton("💳 Купить PRO подписку", callback_data="buy_pro")],
            [InlineKeyboardButton("📋 Тарифы и цены", callback_data="show_prices")],
            [InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_question")],
            [InlineKeyboardButton("📊 Мой статус", callback_data="my_status")],
        ]
        if is_admin:
            keyboard.append([InlineKeyboardButton("🔐 Админ-панель", callback_data="admin_panel")])

        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def show_prices(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать тарифы"""
        query = update.callback_query
        await query.answer()
        text = """
📋 **Тарифы SheetGPT**

**🆓 FREE** - Бесплатно
• 10 запросов в день
• Базовые функции

**⭐ PRO** - 299₽/месяц
• Безлимитные запросы
• Приоритетная обработка
• Все функции
"""
        keyboard = [
            [InlineKeyboardButton("⭐ Купить PRO - 299₽", callback_data="buy_pro_month")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def buy_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать варианты покупки PRO"""
        query = update.callback_query
        await query.answer()
        text = """
💳 **Купить PRO подписку**

⭐ **PRO** - 299₽/месяц
• Безлимитные запросы на 30 дней
• Приоритетная обработка
• Все функции доступны

Выберите способ оплаты:
"""
        keyboard = [
            [InlineKeyboardButton("💳 Картой", callback_data="pay_card")],
            [InlineKeyboardButton("📱 СБП (QR-код)", callback_data="pay_sbp")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def process_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE, period: str):
        """Обработка покупки - создание платежа ЮКасса"""
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        await self.create_yookassa_payment(query, user)

    async def create_yookassa_payment(self, query, user, use_sbp: bool = False):
        """Создать платеж в ЮКасса"""
        if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
            await self.show_manual_payment(query, user, PRO_PRICE, PRO_DAYS, "PRO подписка")
            return

        try:
            idempotence_key = str(uuid.uuid4())
            payment_data = {
                "amount": {"value": f"{PRO_PRICE}.00", "currency": "RUB"},
                "capture": True,
                "description": f"SheetGPT PRO подписка на {PRO_DAYS} дней",
                "metadata": {"telegram_user_id": str(user.id), "days": str(PRO_DAYS)},
                "receipt": {
                    "customer": {
                        "email": f"{user.id}@telegram.user"
                    },
                    "items": [{
                        "description": f"SheetGPT PRO подписка {PRO_DAYS} дней",
                        "quantity": "1.00",
                        "amount": {"value": f"{PRO_PRICE}.00", "currency": "RUB"},
                        "vat_code": 1,
                        "payment_subject": "service",
                        "payment_mode": "full_payment"
                    }]
                }
            }
            
            if use_sbp:
                # СБП - редирект на страницу с QR-кодом
                payment_data["payment_method_data"] = {"type": "sbp"}
                payment_data["confirmation"] = {"type": "redirect", "return_url": "https://t.me/sheetgpt_supportBot"}
            else:
                # Обычная оплата картой - редирект
                payment_data["confirmation"] = {"type": "redirect", "return_url": "https://t.me/sheetgpt_supportBot"}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.yookassa.ru/v3/payments",
                    json=payment_data,
                    auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY),
                    headers={"Idempotence-Key": idempotence_key, "Content-Type": "application/json"}
                )

                logger.info(f"YooKassa response: status={response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    payment_id = result.get("id")
                    payment_status = result.get("status")
                    confirmation = result.get("confirmation", {})
                    confirmation_url = confirmation.get("confirmation_url")

                    logger.info(f"Created YooKassa payment {payment_id}, status={payment_status}, sbp={use_sbp}")
                    logger.info(f"Full response: {result}")

                    if confirmation_url and use_sbp:
                        # СБП - редирект на страницу YooKassa с QR-кодом
                        text = f"""
📱 **Оплата через СБП**

**Сумма:** {PRO_PRICE}₽
**Период:** {PRO_DAYS} дней

1. Нажмите кнопку ниже
2. На открывшейся странице отсканируйте QR-код или выберите банк
3. Подтвердите оплату в приложении банка

После оплаты подписка активируется автоматически!
"""
                        keyboard = [
                            [InlineKeyboardButton("📱 Оплатить через СБП", url=confirmation_url)],
                            [InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_payment_{payment_id}")],
                            [InlineKeyboardButton("« Назад", callback_data="buy_pro")],
                        ]
                        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
                        return

                    elif confirmation_url:
                        # Карта - редирект
                        text = f"""
💳 **Оплата PRO подписки**

**Сумма:** {PRO_PRICE}₽
**Период:** {PRO_DAYS} дней

Нажмите кнопку ниже для перехода на страницу оплаты.
После успешной оплаты подписка активируется автоматически!
"""
                        keyboard = [
                            [InlineKeyboardButton("💳 Перейти к оплате", url=confirmation_url)],
                            [InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_payment_{payment_id}")],
                            [InlineKeyboardButton("« Назад", callback_data="buy_pro")],
                        ]
                        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
                        return
                else:
                    error_text = response.text
                    logger.error(f"YooKassa API error {response.status_code}: {error_text}")
                    err_msg = f"❌ Ошибка: {response.status_code}: {error_text[:200]}"
                    keyboard = [[InlineKeyboardButton("« Назад", callback_data="buy_pro")]]
                    await query.edit_message_text(err_msg, reply_markup=InlineKeyboardMarkup(keyboard))
                    return

        except Exception as e:
            logger.error(f"Failed to create YooKassa payment: {e}")

        await self.show_manual_payment(query, user, PRO_PRICE, PRO_DAYS, "PRO подписка")

    async def check_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
        """Проверить статус платежа"""
        query = update.callback_query
        await query.answer("Проверяем статус оплаты...")
        user = update.effective_user

        if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
            await query.edit_message_text("❌ Платежная система не настроена")
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.yookassa.ru/v3/payments/{payment_id}",
                    auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
                )

                if response.status_code == 200:
                    result = response.json()
                    status = result.get("status")

                    if status == "succeeded":
                        await self.activate_pro_from_payment(user.id, PRO_DAYS, payment_id)
                        text = """
🎉 **Оплата прошла успешно!**

Ваша подписка **PRO** активирована!
✨ Безлимитные запросы теперь доступны!
"""
                        keyboard = [
                            [InlineKeyboardButton("📊 Мой статус", callback_data="my_status")],
                            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")],
                        ]
                        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

                    elif status == "pending":
                        text = """
⏳ **Ожидание оплаты**

Платеж ещё не завершён.
Если вы уже оплатили, подождите 1-2 минуты и нажмите "Проверить" снова.
"""
                        confirmation_url = result.get("confirmation", {}).get("confirmation_url")
                        keyboard = []
                        if confirmation_url:
                            keyboard.append([InlineKeyboardButton("💳 Перейти к оплате", url=confirmation_url)])
                        keyboard.append([InlineKeyboardButton("🔄 Проверить ещё раз", callback_data=f"check_payment_{payment_id}")])
                        keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_main")])
                        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

                    elif status == "canceled":
                        text = """
❌ **Платеж отменён**

Вы можете попробовать оплатить ещё раз.
"""
                        keyboard = [
                            [InlineKeyboardButton("💳 Попробовать снова", callback_data="buy_pro_month")],
                            [InlineKeyboardButton("« Назад", callback_data="back_main")],
                        ]
                        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            await query.edit_message_text("❌ Ошибка проверки платежа")

    async def activate_pro_from_payment(self, telegram_user_id: int, days: int, payment_id: str):
        """Активировать PRO после успешной оплаты"""
        if not self.async_session_factory:
            return False

        try:
            async with self.async_session_factory() as session:
                from app.models.telegram_user import TelegramUser
                result = await session.execute(select(TelegramUser).where(TelegramUser.telegram_user_id == telegram_user_id))
                user = result.scalar_one_or_none()

                if not user:
                    return False

                user.subscription_tier = "premium"
                user.queries_limit = -1
                user.premium_until = datetime.now(timezone.utc) + timedelta(days=days)
                await session.commit()
                logger.info(f"PRO activated for user {telegram_user_id} via payment {payment_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to activate PRO: {e}")
            return False

    async def show_manual_payment(self, query, user, price: int, days: int, title: str):
        """Fallback если ЮКасса не настроена"""
        text = f"""
💳 **Оплата: {title}**

**Сумма:** {price}₽

⚠️ Автоматическая оплата временно недоступна.
Для активации PRO напишите в поддержку.
"""
        keyboard = [
            [InlineKeyboardButton("💬 Написать в поддержку", callback_data="ask_question")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def ask_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать диалог с поддержкой"""
        query = update.callback_query
        await query.answer()
        context.user_data["waiting_question"] = True

        text = """
❓ **Задать вопрос**

Напишите ваш вопрос, и мы ответим в ближайшее время.
"""
        keyboard = [[InlineKeyboardButton("« Отмена", callback_data="back_main")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def my_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статус пользователя"""
        query = update.callback_query
        await query.answer()
        user = update.effective_user

        status_text = "🆓 Free"
        usage_text = "Нет данных"
        premium_text = ""

        if self.async_session_factory:
            async with self.async_session_factory() as session:
                from app.models.telegram_user import TelegramUser
                result = await session.execute(select(TelegramUser).where(TelegramUser.telegram_user_id == user.id))
                db_user = result.scalar_one_or_none()

                if db_user:
                    if db_user.subscription_tier == "premium":
                        status_text = "⭐ PRO"
                        if db_user.premium_until:
                            days_left = (db_user.premium_until - datetime.now(timezone.utc)).days
                            premium_text = f"\n📅 Действует до: {db_user.premium_until.strftime('%d.%m.%Y')} ({days_left} дн.)"
                    limit_str = "∞" if db_user.queries_limit == -1 else str(db_user.queries_limit)
                    usage_text = f"{db_user.queries_used_today}/{limit_str} сегодня"

        text = f"""
📊 **Ваш статус**

👤 {user.first_name} (@{user.username or "N/A"})
🆔 `{user.id}`

💳 Подписка: **{status_text}**{premium_text}
📈 Использовано: {usage_text}
"""
        keyboard = [
            [InlineKeyboardButton("💳 Купить PRO", callback_data="buy_pro")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться в главное меню"""
        query = update.callback_query
        await query.answer()
        context.user_data.pop("waiting_question", None)
        context.user_data.pop("waiting_payment_proof", None)

        user = update.effective_user
        is_admin = user.id == ADMIN_TELEGRAM_ID

        text = """
**Поддержка SheetGPT**

Выберите действие:
"""
        keyboard = [
            [InlineKeyboardButton("💳 Купить PRO подписку", callback_data="buy_pro")],
            [InlineKeyboardButton("📋 Тарифы и цены", callback_data="show_prices")],
            [InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_question")],
            [InlineKeyboardButton("📊 Мой статус", callback_data="my_status")],
        ]
        if is_admin:
            keyboard.append([InlineKeyboardButton("🔐 Админ-панель", callback_data="admin_panel")])

        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user

        if context.user_data.get("waiting_question"):
            await self.forward_question_to_admin(update, context)
            return

        if user.id == ADMIN_TELEGRAM_ID and update.message.reply_to_message:
            await self.admin_reply(update, context)
            return

        await update.message.reply_text(
            "Выберите действие из меню или нажмите /start",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]])
        )

    async def forward_question_to_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Переслать вопрос админу"""
        user = update.effective_user
        msg = update.message
        context.user_data["waiting_question"] = False

        has_media = msg.photo or msg.document or msg.video
        text_content = msg.caption if has_media else msg.text

        admin_text = f"""
📩 **Новый вопрос в поддержку**

👤 От: {user.first_name} (@{user.username or "N/A"})
🆔 ID: `{user.id}`

💬 Сообщение: {text_content or "[Без текста]"}

_Ответьте reply-ем на это сообщение_
"""
        try:
            await self.application.bot.send_message(chat_id=ADMIN_TELEGRAM_ID, text=admin_text, parse_mode="Markdown")
            if has_media:
                await msg.forward(chat_id=ADMIN_TELEGRAM_ID)
            await msg.reply_text(
                "✅ Ваш вопрос отправлен!\n\nМы ответим в ближайшее время.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]])
            )
        except Exception as e:
            logger.error(f"Failed to forward question: {e}")
            await msg.reply_text("❌ Ошибка отправки.")

    async def admin_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Админ отвечает на сообщение"""
        import re
        reply_msg = update.message.reply_to_message
        match = re.search(r"🆔\s*(?:ID:?\s*)?(\d+)", reply_msg.text or "")
        if not match:
            await update.message.reply_text("❌ Не удалось найти ID пользователя")
            return
        user_id = int(match.group(1))
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=f"💬 **Ответ от поддержки:**\n\n{update.message.text}",
                parse_mode="Markdown"
            )
            await update.message.reply_text("✅ Ответ отправлен!")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фотографий"""
        if context.user_data.get("waiting_question"):
            await self.forward_question_to_admin(update, context)

    async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка медиа"""
        if context.user_data.get("waiting_question"):
            await self.forward_question_to_admin(update, context)

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Админ-панель"""
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        if user.id != ADMIN_TELEGRAM_ID:
            await query.edit_message_text("❌ Доступ запрещён")
            return

        text = """
🔐 <b>Админ-панель</b>

Команды:
• /grant_&lt;user_id&gt;_&lt;days&gt; - выдать PRO
• /stats - статистика
"""
        keyboard = [
            [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users_0")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")],
        ]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    async def admin_grant(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выдать PRO"""
        import re
        user = update.effective_user
        if user.id != ADMIN_TELEGRAM_ID:
            return
        match = re.match(r"/grant_(\d+)_(\d+)", update.message.text)
        if not match:
            await update.message.reply_text("Формат: /grant_<user_id>_<days>")
            return
        target_user_id = int(match.group(1))
        days = int(match.group(2))

        if not self.async_session_factory:
            await update.message.reply_text("❌ БД не подключена")
            return

        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            result = await session.execute(select(TelegramUser).where(TelegramUser.telegram_user_id == target_user_id))
            db_user = result.scalar_one_or_none()

            if not db_user:
                await update.message.reply_text(f"❌ Пользователь {target_user_id} не найден")
                return

            db_user.subscription_tier = "premium"
            db_user.queries_limit = -1
            db_user.premium_until = datetime.now(timezone.utc) + timedelta(days=days)
            await session.commit()

            try:
                await self.application.bot.send_message(
                    chat_id=target_user_id,
                    text=f"🎉 **Поздравляем!**\n\nВаша подписка **PRO** активирована на {days} дней!\n\n✨ Безлимитные запросы доступны!",
                    parse_mode="Markdown"
                )
            except:
                pass

            await update.message.reply_text(f"✅ PRO выдан пользователю {target_user_id} на {days} дней")

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика"""
        query = update.callback_query
        if query:
            await query.answer()
            user = query.from_user
        else:
            user = update.effective_user

        if user.id != ADMIN_TELEGRAM_ID:
            return

        if not self.async_session_factory:
            text = "❌ БД не подключена"
        else:
            async with self.async_session_factory() as session:
                from app.models.telegram_user import TelegramUser
                total_result = await session.execute(select(func.count(TelegramUser.id)))
                total_users = total_result.scalar()
                pro_result = await session.execute(select(func.count(TelegramUser.id)).where(TelegramUser.subscription_tier == "premium"))
                pro_users = pro_result.scalar()

            text = f"""
📊 **Статистика SheetGPT**

👥 Всего пользователей: **{total_users}**
⭐ PRO подписчиков: **{pro_users}**
🆓 Free: **{total_users - pro_users}**
"""
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
            [InlineKeyboardButton("« Назад", callback_data="admin_panel")],
        ]
        if query:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def admin_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
        """Список пользователей"""
        query = update.callback_query
        await query.answer()
        user = query.from_user
        if user.id != ADMIN_TELEGRAM_ID:
            return

        if not self.async_session_factory:
            await query.edit_message_text("❌ БД не подключена")
            return

        per_page = 10
        offset = page * per_page

        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            count_result = await session.execute(select(func.count(TelegramUser.id)))
            total = count_result.scalar()

            result = await session.execute(select(TelegramUser).order_by(TelegramUser.created_at.desc()).offset(offset).limit(per_page))
            users = result.scalars().all()

            if not users:
                await query.edit_message_text("👥 Пользователей пока нет")
                return

            text = f"👥 **Пользователи** ({offset+1}-{min(offset+per_page, total)} из {total})\n\n"
            keyboard = []
            for u in users:
                tier = "⭐" if u.subscription_tier == "premium" else "🆓"
                name = u.first_name or u.username or "N/A"
                btn_text = f"{tier} {name[:15]}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"user_{u.license_key}")])

            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"admin_users_{page-1}"))
            if offset + per_page < total:
                nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"admin_users_{page+1}"))
            if nav_buttons:
                keyboard.append(nav_buttons)
            keyboard.append([InlineKeyboardButton("« Назад", callback_data="admin_panel")])

            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    async def admin_view_user(self, update, context, license_key):
        query = update.callback_query
        await query.answer()
        if query.from_user.id != ADMIN_TELEGRAM_ID:
            return
        if not self.async_session_factory:
            await query.edit_message_text("DB error")
            return
        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            result = await session.execute(select(TelegramUser).where(TelegramUser.license_key == license_key))
            u = result.scalar_one_or_none()
            if not u:
                await query.edit_message_text("Not found")
                return
            tier = "PRO" if u.subscription_tier == "premium" else "Free"
            until = u.premium_until.strftime("%Y-%m-%d") if u.premium_until else "-"
            text = "User: " + (u.first_name or "-") + " (@" + (u.username or "-") + ")\nKey: " + u.license_key + "\nTier: " + tier + "\nPRO until: " + until
            kb = []
            if u.subscription_tier != "premium":
                kb.append([InlineKeyboardButton("PRO 7d", callback_data="grant_" + license_key + "_7")])
                kb.append([InlineKeyboardButton("PRO 30d", callback_data="grant_" + license_key + "_30")])
                kb.append([InlineKeyboardButton("PRO 365d", callback_data="grant_" + license_key + "_365")])
            else:
                kb.append([InlineKeyboardButton("Revoke", callback_data="revoke_" + license_key)])
            kb.append([InlineKeyboardButton("Back", callback_data="admin_users_0")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

    async def admin_grant_interactive(self, update, context, license_key, days):
        query = update.callback_query
        await query.answer()
        if query.from_user.id != ADMIN_TELEGRAM_ID:
            return
        if not self.async_session_factory:
            return
        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            result = await session.execute(select(TelegramUser).where(TelegramUser.license_key == license_key))
            u = result.scalar_one_or_none()
            if not u:
                return
            u.subscription_tier = "premium"
            u.queries_limit = -1
            u.premium_until = datetime.now(timezone.utc) + timedelta(days=days)
            await session.commit()
            text = "PRO granted!\n" + (u.first_name or "User") + "\nUntil: " + u.premium_until.strftime("%Y-%m-%d")
            kb = [[InlineKeyboardButton("Back", callback_data="admin_users_0")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
            try:
                from telegram import Bot
                bot = Bot(token=self.main_bot_token)
                await bot.send_message(chat_id=u.telegram_user_id, text="PRO activated until " + u.premium_until.strftime("%Y-%m-%d") + "!")
            except:
                pass

    async def admin_revoke_interactive(self, update, context, license_key):
        query = update.callback_query
        await query.answer()
        if query.from_user.id != ADMIN_TELEGRAM_ID:
            return
        if not self.async_session_factory:
            return
        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            result = await session.execute(select(TelegramUser).where(TelegramUser.license_key == license_key))
            u = result.scalar_one_or_none()
            if not u:
                return
            u.subscription_tier = "free"
            u.queries_limit = 10
            u.premium_until = None
            await session.commit()
            kb = [[InlineKeyboardButton("Back", callback_data="admin_users_0")]]
            await query.edit_message_text("PRO revoked", reply_markup=InlineKeyboardMarkup(kb))

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback кнопок"""
        query = update.callback_query
        data = query.data

        if data == "back_main":
            await self.back_to_main(update, context)
        elif data == "buy_pro":
            await self.buy_pro(update, context)
        elif data == "show_prices":
            await self.show_prices(update, context)
        elif data == "buy_pro_month":
            await self.process_buy(update, context, "month")
        elif data == "pay_card":
            await self.create_yookassa_payment(update.callback_query, update.effective_user, use_sbp=False)
        elif data == "pay_sbp":
            await self.create_yookassa_payment(update.callback_query, update.effective_user, use_sbp=True)
        elif data.startswith("check_payment_"):
            payment_id = data.replace("check_payment_", "")
            await self.check_payment_status(update, context, payment_id)
        elif data == "ask_question":
            await self.ask_question(update, context)
        elif data == "my_status":
            await self.my_status(update, context)
        elif data == "admin_panel":
            await self.admin_panel(update, context)
        elif data == "admin_stats":
            await self.admin_stats(update, context)
        elif data.startswith("admin_users_"):
            page = int(data.replace("admin_users_", ""))
            await self.admin_users(update, context, page)
        elif data.startswith("user_"):
            license_key = data.replace("user_", "")
            await self.admin_view_user(update, context, license_key)
        elif data.startswith("grant_"):
            parts = data.split("_")
            license_key = parts[1]
            days = int(parts[2])
            await self.admin_grant_interactive(update, context, license_key, days)
        elif data.startswith("revoke_"):
            license_key = data.replace("revoke_", "")
            await self.admin_revoke_interactive(update, context, license_key)

    def run(self):
        """Запуск бота"""
        logger.info("Starting SheetGPT Support Bot...")
        logger.info(f"YooKassa SHOP_ID set: {bool(YOOKASSA_SHOP_ID)}")
        logger.info(f"YooKassa SECRET_KEY set: {bool(YOOKASSA_SECRET_KEY)}")
        if YOOKASSA_SHOP_ID:
            logger.info(f"SHOP_ID prefix: {YOOKASSA_SHOP_ID[:6]}...")

        self._init_db()
        self.application = Application.builder().token(self.token).build()

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stats", self.admin_stats))
        self.application.add_handler(MessageHandler(filters.Regex(r"^/grant_\d+_\d+$"), self.admin_grant))
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO, self.handle_media))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("Support Bot is running...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)


def main():
    """Точка входа"""
    from app.config import settings

    token = settings.TELEGRAM_ADMIN_BOT_TOKEN
    main_bot_token = settings.TELEGRAM_BOT_TOKEN
    database_url = settings.DATABASE_URL

    if not token:
        logger.error("TELEGRAM_ADMIN_BOT_TOKEN not set")
        return

    bot = SheetGPTSupportBot(token=token, main_bot_token=main_bot_token, database_url=database_url)
    bot.run()


if __name__ == "__main__":
    main()
