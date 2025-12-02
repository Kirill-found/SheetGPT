"""
SheetGPT Support Bot - Бот поддержки для пользователей

Функции:
- Оплата подписки PRO
- Вопросы в поддержку
- Информация о тарифах
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Admin ID для получения сообщений поддержки
ADMIN_TELEGRAM_ID = 517682186


class SheetGPTSupportBot:
    """Бот поддержки для SheetGPT"""

    def __init__(self, token: str, main_bot_token: str, database_url: str, payment_token: str = None):
        self.token = token
        self.main_bot_token = main_bot_token
        self.database_url = database_url
        self.payment_token = payment_token  # Telegram Payments provider token
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
            self.async_session_factory = sessionmaker(
                self.async_engine, class_=AsyncSession, expire_on_commit=False
            )
            logger.info("Support bot DB connection initialized")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - главное меню поддержки"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started support bot")

        # Проверяем, является ли пользователь админом
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

        # Админские кнопки
        if is_admin:
            keyboard.append([InlineKeyboardButton("🔐 Админ-панель", callback_data="admin_panel")])

        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_prices(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать тарифы"""
        query = update.callback_query
        await query.answer()

        text = """
📋 **Тарифы SheetGPT**

**🆓 FREE** - Бесплатно
• 10 запросов в день
• Базовые функции
• Стандартная скорость

**⭐ PRO** - 299₽/месяц
• Безлимитные запросы
• Приоритетная обработка
• Все функции доступны
• Поддержка 24/7

**💎 PRO Годовой** - 2499₽/год (экономия 40%)
• Всё из PRO
• 12 месяцев по цене 8

Выберите план:
"""
        keyboard = [
            [InlineKeyboardButton("⭐ PRO на месяц - 299₽", callback_data="buy_pro_month")],
            [InlineKeyboardButton("💎 PRO на год - 2499₽", callback_data="buy_pro_year")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")],
        ]

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def buy_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать варианты покупки PRO"""
        query = update.callback_query
        await query.answer()

        text = """
💳 **Купить PRO подписку**

Выберите период подписки:

⭐ **PRO на месяц** - 299₽
• Безлимитные запросы на 30 дней

💎 **PRO на год** - 2499₽
• Безлимитные запросы на 365 дней
• Экономия 40%!
"""
        keyboard = [
            [InlineKeyboardButton("⭐ Месяц - 299₽", callback_data="buy_pro_month")],
            [InlineKeyboardButton("💎 Год - 2499₽", callback_data="buy_pro_year")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")],
        ]

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def process_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE, period: str):
        """Обработка покупки"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user

        if period == "month":
            price = 299
            days = 30
            title = "PRO подписка (месяц)"
        else:  # year
            price = 2499
            days = 365
            title = "PRO подписка (год)"

        # Если есть payment_token - используем Telegram Payments
        if self.payment_token:
            await self.send_invoice(query, user.id, title, price, days)
        else:
            # Иначе показываем инструкции для ручной оплаты
            await self.show_manual_payment(query, user, price, days, title)

    async def show_manual_payment(self, query, user, price: int, days: int, title: str):
        """Показать инструкции для ручной оплаты"""
        # Сохраняем данные о платеже
        payment_id = f"{user.id}_{days}_{int(datetime.now().timestamp())}"

        text = f"""
💳 **Оплата: {title}**

**Сумма:** {price}₽

**Способы оплаты:**

1️⃣ **СБП (Система Быстрых Платежей)**
   Номер: `+79897546891`
   Банк: Т-Банк (Тинькофф)

2️⃣ **Карта Т-Банк**
   `2200 7017 1872 7214`

После оплаты нажмите "✅ Я оплатил" и отправьте скриншот чека.

⏱ Активация в течение 15 минут.
"""
        keyboard = [
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{days}")],
            [InlineKeyboardButton("« Назад", callback_data="buy_pro")],
        ]

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def user_paid(self, update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
        """Пользователь нажал 'Я оплатил'"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        context.user_data['waiting_payment_proof'] = days

        text = """
📸 **Подтверждение оплаты**

Пожалуйста, отправьте скриншот чека или квитанции об оплате.

После проверки администратором ваша подписка будет активирована.
"""
        keyboard = [
            [InlineKeyboardButton("« Отмена", callback_data="buy_pro")],
        ]

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def ask_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать диалог с поддержкой"""
        query = update.callback_query
        await query.answer()

        context.user_data['waiting_question'] = True

        text = """
❓ **Задать вопрос**

Напишите ваш вопрос, и мы ответим в ближайшее время.

Вы можете спросить о:
• Работе расширения
• Проблемах с подпиской
• Функциях SheetGPT
• Технических вопросах

Просто напишите сообщение:
"""
        keyboard = [
            [InlineKeyboardButton("« Отмена", callback_data="back_main")],
        ]

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def my_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статус пользователя"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user

        # Получаем данные из БД
        status_text = "🆓 Free"
        usage_text = "Нет данных"
        premium_text = ""

        if self.async_session_factory:
            async with self.async_session_factory() as session:
                from app.models.telegram_user import TelegramUser
                result = await session.execute(
                    select(TelegramUser).where(TelegramUser.telegram_user_id == user.id)
                )
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

👤 {user.first_name} (@{user.username or 'N/A'})
🆔 `{user.id}`

💳 Подписка: **{status_text}**{premium_text}
📈 Использовано: {usage_text}

Хотите улучшить план?
"""
        keyboard = [
            [InlineKeyboardButton("💳 Купить PRO", callback_data="buy_pro")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")],
        ]

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться в главное меню"""
        query = update.callback_query
        await query.answer()

        # Сбрасываем состояния
        context.user_data.pop('waiting_question', None)
        context.user_data.pop('waiting_payment_proof', None)

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

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user

        # Ожидаем вопрос в поддержку
        if context.user_data.get('waiting_question'):
            await self.forward_question_to_admin(update, context)
            return

        # Ожидаем подтверждение оплаты
        if context.user_data.get('waiting_payment_proof'):
            await self.forward_payment_proof(update, context)
            return

        # Если это админ и это reply на сообщение - отправляем ответ пользователю
        if user.id == ADMIN_TELEGRAM_ID and update.message.reply_to_message:
            await self.admin_reply(update, context)
            return

        # Иначе показываем подсказку
        await update.message.reply_text(
            "Выберите действие из меню или нажмите /start",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
            ])
        )

    async def forward_question_to_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Переслать вопрос админу"""
        user = update.effective_user
        message = update.message.text

        context.user_data['waiting_question'] = False

        # Отправляем админу
        admin_text = f"""
📩 **Новый вопрос в поддержку**

👤 От: {user.first_name} (@{user.username or 'N/A'})
🆔 ID: `{user.id}`

💬 Вопрос:
{message}

_Ответьте на это сообщение, чтобы отправить ответ пользователю_
"""
        try:
            await self.application.bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=admin_text,
                parse_mode='Markdown'
            )
            await update.message.reply_text(
                "✅ Ваш вопрос отправлен!\n\nМы ответим в ближайшее время.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Failed to forward question: {e}")
            await update.message.reply_text("❌ Ошибка отправки. Попробуйте позже.")

    async def forward_payment_proof(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Переслать подтверждение оплаты админу"""
        user = update.effective_user
        days = context.user_data.get('waiting_payment_proof', 30)
        context.user_data['waiting_payment_proof'] = None

        period = "месяц" if days == 30 else "год"
        price = 299 if days == 30 else 2499

        # Формируем сообщение для админа
        admin_text = f"""
💳 **Новая оплата PRO**

👤 От: {user.first_name} (@{user.username or 'N/A'})
🆔 ID: `{user.id}`

📦 Тариф: PRO на {period} ({days} дн.)
💰 Сумма: {price}₽

⬇️ Подтверждение оплаты ниже

Для активации: /grant_{user.id}_{days}
"""
        try:
            await self.application.bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=admin_text,
                parse_mode='Markdown'
            )

            # Пересылаем сообщение/фото пользователя
            await update.message.forward(chat_id=ADMIN_TELEGRAM_ID)

            await update.message.reply_text(
                "✅ Подтверждение отправлено!\n\n"
                "Мы проверим оплату и активируем подписку в течение 15 минут.\n"
                "Вы получите уведомление после активации.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Failed to forward payment proof: {e}")
            await update.message.reply_text("❌ Ошибка отправки. Попробуйте позже.")

    async def admin_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Админ отвечает на сообщение пользователя"""
        reply_msg = update.message.reply_to_message

        # Извлекаем user_id из сообщения
        import re
        match = re.search(r'🆔.*?`(\d+)`', reply_msg.text or '')
        if not match:
            await update.message.reply_text("❌ Не удалось найти ID пользователя в сообщении")
            return

        user_id = int(match.group(1))

        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=f"💬 **Ответ от поддержки:**\n\n{update.message.text}",
                parse_mode='Markdown'
            )
            await update.message.reply_text("✅ Ответ отправлен!")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фотографий (для подтверждения оплаты)"""
        if context.user_data.get('waiting_payment_proof'):
            await self.forward_payment_proof(update, context)

    # ==================== АДМИН ФУНКЦИИ ====================

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Админ-панель"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        if user.id != ADMIN_TELEGRAM_ID:
            await query.edit_message_text("❌ Доступ запрещён")
            return

        text = """
🔐 **Админ-панель**

Команды:
• /grant_<user_id>_<days> - выдать PRO
• /users - список пользователей
• /stats - статистика

Также можно отвечать на сообщения пользователей reply-ем.
"""
        keyboard = [
            [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users_0")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("« Назад", callback_data="back_main")],
        ]

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def admin_grant(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /grant_<user_id>_<days> - выдать PRO"""
        user = update.effective_user
        if user.id != ADMIN_TELEGRAM_ID:
            return

        # Парсим команду
        import re
        match = re.match(r'/grant_(\d+)_(\d+)', update.message.text)
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
            result = await session.execute(
                select(TelegramUser).where(TelegramUser.telegram_user_id == target_user_id)
            )
            db_user = result.scalar_one_or_none()

            if not db_user:
                await update.message.reply_text(f"❌ Пользователь {target_user_id} не найден")
                return

            db_user.subscription_tier = "premium"
            db_user.queries_limit = -1
            db_user.premium_until = datetime.now(timezone.utc) + timedelta(days=days)
            await session.commit()

            # Уведомляем пользователя
            try:
                await self.application.bot.send_message(
                    chat_id=target_user_id,
                    text=f"🎉 **Поздравляем!**\n\n"
                         f"Ваша подписка **PRO** активирована на {days} дней!\n\n"
                         f"✨ Безлимитные запросы доступны!",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Could not notify user: {e}")

            await update.message.reply_text(
                f"✅ PRO выдан пользователю {target_user_id} на {days} дней\n"
                f"👤 {db_user.first_name} @{db_user.username}"
            )

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика для админа"""
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

                pro_result = await session.execute(
                    select(func.count(TelegramUser.id)).where(TelegramUser.subscription_tier == "premium")
                )
                pro_users = pro_result.scalar()

                queries_result = await session.execute(select(func.sum(TelegramUser.total_queries)))
                total_queries = queries_result.scalar() or 0

                today_result = await session.execute(select(func.sum(TelegramUser.queries_used_today)))
                today_queries = today_result.scalar() or 0

            text = f"""
📊 **Статистика SheetGPT**

👥 Всего пользователей: **{total_users}**
⭐ PRO подписчиков: **{pro_users}**
🆓 Free: **{total_users - pro_users}**

📈 Запросов всего: **{total_queries}**
📅 Запросов сегодня: **{today_queries}**

🕐 {datetime.now().strftime('%H:%M:%S')}
"""

        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
            [InlineKeyboardButton("« Назад", callback_data="admin_panel")],
        ]

        if query:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def admin_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
        """Список пользователей для админа"""
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

            result = await session.execute(
                select(TelegramUser)
                .order_by(TelegramUser.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            users = result.scalars().all()

            if not users:
                await query.edit_message_text("👥 Пользователей пока нет")
                return

            text = f"👥 **Пользователи** ({offset+1}-{min(offset+per_page, total)} из {total})\n\n"

            keyboard = []
            for u in users:
                tier = "⭐" if u.subscription_tier == "premium" else "🆓"
                name = u.first_name or u.username or "N/A"
                btn_text = f"{tier} {name[:15]} | {u.queries_used_today}/{u.queries_limit if u.queries_limit > 0 else '∞'}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"user_{u.license_key}")])

            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"admin_users_{page-1}"))
            if offset + per_page < total:
                nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"admin_users_{page+1}"))
            if nav_buttons:
                keyboard.append(nav_buttons)

            keyboard.append([InlineKeyboardButton("« Назад", callback_data="admin_panel")])

            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

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
        elif data == "buy_pro_year":
            await self.process_buy(update, context, "year")
        elif data.startswith("paid_"):
            days = int(data.replace("paid_", ""))
            await self.user_paid(update, context, days)
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

    def run(self):
        """Запуск бота"""
        logger.info("Starting SheetGPT Support Bot...")

        self._init_db()

        self.application = Application.builder().token(self.token).build()

        # Команды
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stats", self.admin_stats))
        self.application.add_handler(MessageHandler(
            filters.Regex(r'^/grant_\d+_\d+$'),
            self.admin_grant
        ))

        # Callback кнопки
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))

        # Текстовые сообщения
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Фото (для подтверждения оплаты)
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

        logger.info("Support Bot is running...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)


def main():
    """Точка входа"""
    from app.config import settings

    token = settings.TELEGRAM_ADMIN_BOT_TOKEN  # Используем тот же токен
    main_bot_token = settings.TELEGRAM_BOT_TOKEN
    database_url = settings.DATABASE_URL

    if not token:
        logger.error("TELEGRAM_ADMIN_BOT_TOKEN not set")
        return

    bot = SheetGPTSupportBot(
        token=token,
        main_bot_token=main_bot_token,
        database_url=database_url
    )
    bot.run()


if __name__ == "__main__":
    main()
