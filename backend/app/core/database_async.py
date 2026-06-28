import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.env import load_backend_env

load_backend_env()


def _coerce_async_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql+psycopg2://"):
        return f"postgresql+asyncpg://{url[len('postgresql+psycopg2://'):]}"
    if url.startswith("postgresql://"):
        return f"postgresql+asyncpg://{url[len('postgresql://'):]}"
    return url


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

ADMIN_DATABASE_URL = os.getenv("DATABASE_URL_ADMIN", "").strip()

ASYNC_DATABASE_URL = _coerce_async_database_url(DATABASE_URL)

engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

if ADMIN_DATABASE_URL:
    ASYNC_ADMIN_DATABASE_URL = _coerce_async_database_url(ADMIN_DATABASE_URL)
    admin_engine = create_async_engine(ASYNC_ADMIN_DATABASE_URL, pool_pre_ping=True)
    AdminAsyncSessionLocal = async_sessionmaker(
        admin_engine, expire_on_commit=False, class_=AsyncSession
    )
else:
    admin_engine = None
    AdminAsyncSessionLocal = None
