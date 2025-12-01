"""
SheetGPT Admin Bot - Отдельный бот для администрирования

Функции:
- Получение сообщений от пользователей (пересылка из основного бота)
- Ответ пользователям простым реплаем
- Управление ключами и подписками
- Статистика
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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

# Хранилище для связи сообщений админа с пользователями
# {admin_message_id: user_telegram_id}
message_user_map = {}


class SheetGPTAdminBot:
    """Админ-бот для SheetGPT"""

    def __init__(self, token: str, main_bot_token: str, database_url: str):
        self.token = token
        self.main_bot_token = main_bot_token
        self.database_url = database_url
        self.application = None
        self.main_bot = None  # Для отправки сообщений пользователям
        self.async_engine = None
        self.async_session_factory = None

    def _init_db(self):
        """Инициализация подключения к БД"""
        if self.database_url:
            # Преобразуем postgres:// в postgresql+asyncpg://
            db_url = self.database_url
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

            self.async_engine = create_async_engine(db_url, echo=False)
            self.async_session_factory = sessionmaker(
                self.async_engine, class_=AsyncSession, expire_on_commit=False
            )
            logger.info("Admin bot DB connection initialized")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        text = """
🔐 **SheetGPT Admin Panel**

Добро пожаловать в панель администратора!

**Команды:**
/users - Список пользователей
/search <запрос> - Поиск по имени/username
/stats - Статистика

**Управление:**
• Нажми на пользователя для управления
• Отвечай на пересланные сообщения - ответ уйдёт юзеру

**Уведомления:**
• Новые пользователи
• Сообщения в поддержку
• Оплаты (когда подключим)
"""
        keyboard = [
            [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users_0")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_refresh")]
        ]
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
        """Показать список пользователей с пагинацией"""
        query = update.callback_query
        if query:
            await query.answer()

        per_page = 10
        offset = page * per_page

        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser

            # Получаем общее количество
            count_result = await session.execute(select(func.count(TelegramUser.id)))
            total = count_result.scalar()

            # Получаем пользователей
            result = await session.execute(
                select(TelegramUser)
                .order_by(TelegramUser.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            users = result.scalars().all()

            if not users:
                text = "👥 Пользователей пока нет"
                if query:
                    await query.edit_message_text(text)
                else:
                    await update.message.reply_text(text)
                return

            text = f"👥 **Пользователи** ({offset+1}-{min(offset+per_page, total)} из {total})\n\n"

            keyboard = []
            for u in users:
                tier = "⭐" if u.subscription_tier == "premium" else "🆓"
                name = u.first_name or u.username or "N/A"
                btn_text = f"{tier} {name[:15]} | {u.queries_used_today}/{u.queries_limit if u.queries_limit > 0 else '∞'}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"user_{u.license_key}")])

            # Пагинация
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_users_{page-1}"))
            if offset + per_page < total:
                nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"admin_users_{page+1}"))
            if nav_buttons:
                keyboard.append(nav_buttons)

            keyboard.append([InlineKeyboardButton("🏠 Главная", callback_data="admin_home")])

            if query:
                await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def show_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, license_key: str):
        """Показать информацию о пользователе"""
        query = update.callback_query
        await query.answer()

        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            result = await session.execute(
                select(TelegramUser).where(TelegramUser.license_key == license_key)
            )
            user = result.scalar_one_or_none()

            if not user:
                await query.edit_message_text(f"❌ Пользователь не найден")
                return

            tier = "⭐ PRO" if user.subscription_tier == "premium" else "🆓 Free"
            premium_info = ""
            if user.premium_until:
                days_left = (user.premium_until - datetime.now(timezone.utc)).days
                premium_info = f"\n📅 PRO до: {user.premium_until.strftime('%d.%m.%Y')} ({days_left} дн.)"

            text = f"""
👤 **{user.first_name or 'N/A'}** @{user.username or 'N/A'}

🔑 `{user.license_key}`
🆔 `{user.telegram_user_id}`

💳 {tier}{premium_info}
📊 Сегодня: {user.queries_used_today}/{user.queries_limit if user.queries_limit > 0 else '∞'}
📈 Всего: {user.total_queries}

📅 Рег: {user.created_at.strftime('%d.%m.%Y') if user.created_at else 'N/A'}
🕐 Актив: {user.last_query_at.strftime('%d.%m.%Y %H:%M') if user.last_query_at else 'Никогда'}
"""
            # Кнопки действий
            if user.subscription_tier == "premium":
                action_btn = InlineKeyboardButton("❌ Забрать PRO", callback_data=f"revoke_{license_key}")
            else:
                action_btn = InlineKeyboardButton("⭐ Выдать PRO", callback_data=f"grant_{license_key}")

            keyboard = [
                [action_btn],
                [
                    InlineKeyboardButton("📅 PRO 30д", callback_data=f"grant30_{license_key}"),
                    InlineKeyboardButton("📅 PRO 365д", callback_data=f"grant365_{license_key}")
                ],
                [InlineKeyboardButton("🔄 Сброс счётчика", callback_data=f"reset_{license_key}")],
                [InlineKeyboardButton("💬 Написать", callback_data=f"msg_{license_key}")],
                [InlineKeyboardButton("« Назад к списку", callback_data="admin_users_0")]
            ]

            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def grant_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE, license_key: str, days: int = 365):
        """Выдать PRO подписку"""
        query = update.callback_query
        await query.answer()

        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            result = await session.execute(
                select(TelegramUser).where(TelegramUser.license_key == license_key)
            )
            user = result.scalar_one_or_none()

            if not user:
                await query.edit_message_text("❌ Пользователь не найден")
                return

            user.subscription_tier = "premium"
            user.queries_limit = -1
            user.premium_until = datetime.now(timezone.utc) + timedelta(days=days)
            await session.commit()

            # Уведомляем пользователя через основной бот
            try:
                from telegram import Bot
                main_bot = Bot(token=self.main_bot_token)
                await main_bot.send_message(
                    chat_id=user.telegram_user_id,
                    text=f"🎉 **Поздравляем!**\n\nВам активирована подписка **PRO** на {days} дней!\n\n✨ Безлимитные запросы активированы!",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Could not notify user: {e}")

            await query.edit_message_text(
                f"✅ PRO выдан на {days} дней!\n\n"
                f"👤 {user.first_name} @{user.username}\n"
                f"📅 До: {user.premium_until.strftime('%d.%m.%Y')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👤 К пользователю", callback_data=f"user_{license_key}"),
                    InlineKeyboardButton("👥 К списку", callback_data="admin_users_0")
                ]])
            )

    async def revoke_pro(self, update: Update, context: ContextTypes.DEFAULT_TYPE, license_key: str):
        """Забрать PRO подписку"""
        query = update.callback_query
        await query.answer()

        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            result = await session.execute(
                select(TelegramUser).where(TelegramUser.license_key == license_key)
            )
            user = result.scalar_one_or_none()

            if not user:
                await query.edit_message_text("❌ Пользователь не найден")
                return

            user.subscription_tier = "free"
            user.queries_limit = 10
            user.premium_until = None
            await session.commit()

            await query.edit_message_text(
                f"✅ PRO отозван\n\n"
                f"👤 {user.first_name} @{user.username}\n"
                f"📊 Теперь: Free (10 запросов)",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👤 К пользователю", callback_data=f"user_{license_key}"),
                    InlineKeyboardButton("👥 К списку", callback_data="admin_users_0")
                ]])
            )

    async def reset_usage(self, update: Update, context: ContextTypes.DEFAULT_TYPE, license_key: str):
        """Сбросить счётчик использования"""
        query = update.callback_query
        await query.answer("Счётчик сброшен!")

        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            result = await session.execute(
                select(TelegramUser).where(TelegramUser.license_key == license_key)
            )
            user = result.scalar_one_or_none()

            if user:
                user.queries_used_today = 0
                await session.commit()

        # Обновляем карточку пользователя
        await self.show_user(update, context, license_key)

    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику"""
        query = update.callback_query
        if query:
            await query.answer()

        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser

            # Общее количество
            total_result = await session.execute(select(func.count(TelegramUser.id)))
            total_users = total_result.scalar()

            # PRO пользователи
            pro_result = await session.execute(
                select(func.count(TelegramUser.id)).where(TelegramUser.subscription_tier == "premium")
            )
            pro_users = pro_result.scalar()

            # Всего запросов
            queries_result = await session.execute(select(func.sum(TelegramUser.total_queries)))
            total_queries = queries_result.scalar() or 0

            # Запросов сегодня
            today_result = await session.execute(select(func.sum(TelegramUser.queries_used_today)))
            today_queries = today_result.scalar() or 0

        text = f"""
📊 **Статистика SheetGPT**

👥 Всего пользователей: **{total_users}**
⭐ PRO подписчиков: **{pro_users}**
🆓 Free: **{total_users - pro_users}**

📈 Запросов всего: **{total_queries}**
📅 Запросов сегодня: **{today_queries}**

🕐 Обновлено: {datetime.now().strftime('%H:%M:%S')}
"""
        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
                    [InlineKeyboardButton("🏠 Главная", callback_data="admin_home")]]

        if query:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def prepare_message_to_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, license_key: str):
        """Подготовка отправки сообщения пользователю"""
        query = update.callback_query
        await query.answer()

        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            result = await session.execute(
                select(TelegramUser).where(TelegramUser.license_key == license_key)
            )
            user = result.scalar_one_or_none()

            if not user:
                await query.edit_message_text("❌ Пользователь не найден")
                return

            context.user_data['reply_to_user'] = user.telegram_user_id
            context.user_data['reply_to_name'] = user.first_name or user.username

            await query.edit_message_text(
                f"💬 Напиши сообщение для **{user.first_name or user.username}**:\n\n"
                f"(Просто отправь текст следующим сообщением)",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отмена", callback_data=f"user_{license_key}")
                ]])
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        # Если это ответ на пересланное сообщение от пользователя
        if update.message.reply_to_message:
            reply_msg = update.message.reply_to_message
            # Проверяем, есть ли в тексте ID пользователя
            if reply_msg.text and "🆔" in reply_msg.text:
                # Извлекаем user_id из сообщения
                import re
                match = re.search(r'🆔.*?`(\d+)`', reply_msg.text)
                if match:
                    user_id = int(match.group(1))
                    await self.send_to_user(update, context, user_id, update.message.text)
                    return

        # Если ждём сообщение для конкретного пользователя
        if context.user_data.get('reply_to_user'):
            user_id = context.user_data.pop('reply_to_user')
            user_name = context.user_data.pop('reply_to_name', 'пользователь')
            await self.send_to_user(update, context, user_id, update.message.text)
            return

        # Иначе это просто сообщение - игнорируем или показываем подсказку
        await update.message.reply_text(
            "💡 Чтобы ответить пользователю:\n"
            "• Сделай реплай на его сообщение\n"
            "• Или нажми 💬 в карточке пользователя"
        )

    async def send_to_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
        """Отправить сообщение пользователю"""
        try:
            from telegram import Bot
            main_bot = Bot(token=self.main_bot_token)
            await main_bot.send_message(
                chat_id=user_id,
                text=f"💬 **Сообщение от поддержки:**\n\n{text}",
                parse_mode='Markdown'
            )
            await update.message.reply_text(f"✅ Сообщение отправлено!")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")

    async def search_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск пользователей"""
        if not context.args:
            await update.message.reply_text("Использование: /search <имя или username>")
            return

        query_text = ' '.join(context.args).lower()

        async with self.async_session_factory() as session:
            from app.models.telegram_user import TelegramUser
            result = await session.execute(
                select(TelegramUser).where(
                    (TelegramUser.username.ilike(f"%{query_text}%")) |
                    (TelegramUser.first_name.ilike(f"%{query_text}%")) |
                    (TelegramUser.license_key.ilike(f"%{query_text}%"))
                ).limit(10)
            )
            users = result.scalars().all()

            if not users:
                await update.message.reply_text(f"🔍 По запросу '{query_text}' ничего не найдено")
                return

            text = f"🔍 Результаты поиска: **{query_text}**\n\n"
            keyboard = []
            for u in users:
                tier = "⭐" if u.subscription_tier == "premium" else "🆓"
                name = u.first_name or u.username or "N/A"
                keyboard.append([InlineKeyboardButton(
                    f"{tier} {name} | {u.license_key[:9]}...",
                    callback_data=f"user_{u.license_key}"
                )])

            await update.message.reply_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback кнопок"""
        query = update.callback_query
        data = query.data

        if data == "admin_home":
            await query.answer()
            text = """
🔐 **SheetGPT Admin Panel**

Выбери действие:
"""
            keyboard = [
                [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users_0")],
                [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            ]
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("admin_users_"):
            page = int(data.replace("admin_users_", ""))
            await self.show_users(update, context, page)

        elif data == "admin_stats":
            await self.show_stats(update, context)

        elif data.startswith("user_"):
            license_key = data.replace("user_", "")
            await self.show_user(update, context, license_key)

        elif data.startswith("grant30_"):
            license_key = data.replace("grant30_", "")
            await self.grant_pro(update, context, license_key, 30)

        elif data.startswith("grant365_"):
            license_key = data.replace("grant365_", "")
            await self.grant_pro(update, context, license_key, 365)

        elif data.startswith("grant_"):
            license_key = data.replace("grant_", "")
            await self.grant_pro(update, context, license_key, 365)

        elif data.startswith("revoke_"):
            license_key = data.replace("revoke_", "")
            await self.revoke_pro(update, context, license_key)

        elif data.startswith("reset_"):
            license_key = data.replace("reset_", "")
            await self.reset_usage(update, context, license_key)

        elif data.startswith("msg_"):
            license_key = data.replace("msg_", "")
            await self.prepare_message_to_user(update, context, license_key)

    def run(self):
        """Запуск бота"""
        logger.info("Starting SheetGPT Admin Bot...")

        self._init_db()

        self.application = Application.builder().token(self.token).build()

        # Команды
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("users", lambda u, c: self.show_users(u, c, 0)))
        self.application.add_handler(CommandHandler("stats", self.show_stats))
        self.application.add_handler(CommandHandler("search", self.search_users))

        # Callback кнопки
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))

        # Текстовые сообщения (для ответов)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        logger.info("Admin Bot is running...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)


def main():
    """Точка входа"""
    from app.config import settings

    token = "8472527828:AAHXB30EtficnooQnNsOLrJqhoE6yotSZaE"  # Admin bot token
    main_bot_token = settings.TELEGRAM_BOT_TOKEN
    database_url = settings.DATABASE_URL

    if not database_url:
        logger.error("DATABASE_URL not set")
        return

    bot = SheetGPTAdminBot(
        token=token,
        main_bot_token=main_bot_token,
        database_url=database_url
    )
    bot.run()


if __name__ == "__main__":
    main()
