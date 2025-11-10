from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255))

    # Подписка
    subscription_tier = Column(String(20), default="free")  # free, starter, pro, team
    queries_used_this_month = Column(Integer, default=0)
    queries_limit = Column(Integer, default=20)  # Зависит от tier

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User {self.email}>"
