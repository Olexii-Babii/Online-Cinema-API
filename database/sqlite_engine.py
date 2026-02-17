from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config.dependencies import get_settings
from database import Base

settings = get_settings()

SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{settings.PATH_TO_DB}"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = sessionmaker(
    expire_on_commit=False, class_=AsyncSession, bind=engine
)


async def get_sqlite_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_sqlite_db_contextmanager() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def reset_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
