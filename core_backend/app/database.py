import contextlib
import os
import urllib.parse
from collections.abc import AsyncGenerator, Generator
from typing import ContextManager

from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from .config import (
    DB_POOL_SIZE,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

DATABASE_URL = os.environ.get("DATABASE_URL")

SYNC_DB_API = "psycopg2"
ASYNC_DB_API = "asyncpg"


# global so we don't create more than one engine per process
# outside of being best practice, this is needed so we can properly pool
# connections and not create a new pool on every request
_SYNC_ENGINE: Engine | None = None
_ASYNC_ENGINE: AsyncEngine | None = None


def build_connection_string(
    *,
    db_api: str = ASYNC_DB_API,
    user: str = POSTGRES_USER,
    password: str = POSTGRES_PASSWORD,
    host: str = POSTGRES_HOST,
    port: str = POSTGRES_PORT,
    db: str = POSTGRES_DB,
) -> str:
    """Return a connection string for the given database."""
    encoded_password = urllib.parse.quote_plus(password)
    return f"postgresql+{db_api}://{user}:{encoded_password}@{host}:{port}/{db}"


def get_sqlalchemy_engine() -> Engine:
    """Return a SQLAlchemy engine."""
    global _SYNC_ENGINE
    if _SYNC_ENGINE is None:
        connection_string = build_connection_string(db_api=SYNC_DB_API)
        _SYNC_ENGINE = create_engine(connection_string)
    return _SYNC_ENGINE


def get_sqlalchemy_async_engine() -> AsyncEngine:
    """Return a SQLAlchemy async engine generator."""
    global _ASYNC_ENGINE
    if _ASYNC_ENGINE is None:
        connection_string = build_connection_string()
        _ASYNC_ENGINE = create_async_engine(connection_string, pool_size=DB_POOL_SIZE)
    return _ASYNC_ENGINE


def get_session_context_manager() -> ContextManager[Session]:
    """Return a SQLAlchemy session context manager."""
    return contextlib.contextmanager(get_session)()


def get_session() -> Generator[Session, None, None]:
    """Return a SQLAlchemy session generator."""
    with Session(get_sqlalchemy_engine(), expire_on_commit=False) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Return a SQLAlchemy async session."""
    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as async_session:
        yield async_session
