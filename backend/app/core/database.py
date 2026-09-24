from collections.abc import AsyncIterator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    # Importa os modelos antes de criar as tabelas.
    from app import models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

        def ensure_profile_columns(sync_connection) -> None:
            columns = {column["name"] for column in inspect(sync_connection).get_columns("users")}
            if "avatar" not in columns:
                sync_connection.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN avatar VARCHAR(50) "
                        "NOT NULL DEFAULT 'astronauta'"
                    )
                )

        await connection.run_sync(ensure_profile_columns)


async def close_database() -> None:
    await engine.dispose()
