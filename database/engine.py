from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./movies.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = sessionmaker(
    expire_on_commit=False,
    class_=AsyncSession,
    bind=engine
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
