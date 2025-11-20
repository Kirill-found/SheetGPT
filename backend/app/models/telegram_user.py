"""
Модель для Telegram пользователей SheetGPT Bot
"""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import secrets
from app.core.database import Base


class TelegramUser(Base):
    """Модель пользователя Telegram бота"""
    __tablename__ = "telegram_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Telegram данные
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))

    # API токен для аутентификации
    api_token = Column(String(64), unique=True, nullable=False, index=True)

    # Подписка и лимиты
    subscription_tier = Column(String(20), default="free")  # free, premium
    is_active = Column(Boolean, default=True)

    # Лимиты запросов
    queries_used_today = Column(Integer, default=0)
    queries_limit = Column(Integer, default=10)  # free: 10, premium: unlimited (-1)

    # Статистика
    total_queries = Column(Integer, default=0)
    last_query_at = Column(DateTime(timezone=True))

    # Даты
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    premium_until = Column(DateTime(timezone=True))  # Дата истечения premium подписки

    @staticmethod
    def generate_api_token():
        """Генерация уникального API токена"""
        return secrets.token_urlsafe(48)

    def can_make_query(self) -> bool:
        """Проверка возможности сделать запрос"""
        if not self.is_active:
            return False

        # Premium пользователи имеют безлимит
        if self.subscription_tier == "premium":
            # Проверяем, не истекла ли подписка
            if self.premium_until:
                from datetime import datetime, timezone
                if datetime.now(timezone.utc) > self.premium_until:
                    return False
            return True

        # Free пользователи ограничены дневным лимитом
        return self.queries_used_today < self.queries_limit

    def increment_usage(self):
        """Увеличение счетчика использования"""
        self.queries_used_today += 1
        self.total_queries += 1
        from datetime import datetime, timezone
        self.last_query_at = datetime.now(timezone.utc)

    def reset_daily_usage(self):
        """Сброс дневного счетчика (вызывается ежедневно)"""
        self.queries_used_today = 0

    def __repr__(self):
        return f"<TelegramUser {self.telegram_user_id} - {self.subscription_tier}>"
