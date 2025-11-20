from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Fix DATABASE_URL for asyncpg (Railway uses postgresql:// by default)
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Создаем async engine
engine = create_async_engine(
    database_url,
    echo=True if settings.ENVIRONMENT == "development" else False,
    future=True,
    pool_pre_ping=True,
)

# Session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class для моделей
Base = declarative_base()


# Dependency для получения DB session
async def get_db():
    """Dependency для получения database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Инициализация базы данных (создание таблиц)"""
    async with engine.begin() as conn:
        # Импортируем все модели
        from app.models import user, subscription

        # Создаем таблицы
        await conn.run_sync(Base.metadata.create_all)
