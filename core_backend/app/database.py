"""This module contains functions for managing database connections."""

# pylint: disable=global-statement
import contextlib
import os
from collections.abc import AsyncGenerator, Generator
from functools import wraps
from typing import Any, Callable, ContextManager

from sqlalchemy.engine import URL, Engine, create_engine
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

# Global so we don't create more than one engine per process.
# Outside of being best practice, this is needed so we can properly pool connections
# and not create a new pool on every request.
_SYNC_ENGINE: Engine | None = None
_ASYNC_ENGINE: AsyncEngine | None = None


def get_connection_url(
    *,
    db: str = POSTGRES_DB,
    db_api: str = ASYNC_DB_API,
    host: str = POSTGRES_HOST,
    password: str = POSTGRES_PASSWORD,
    port: int | str = POSTGRES_PORT,
    user: str = POSTGRES_USER,
) -> URL:
    """Return a connection string for the given database.

    Parameters
    ----------
    db
        The database name.
    db_api
        The database API.
    host
        The database host.
    password
        The database password.
    port
        The database port.
    user
        The database user.

    Returns
    -------
    URL
        A connection string for the given database.
    """

    return URL.create(
        database=db,
        drivername="postgresql+" + db_api,
        host=host,
        password=password,
        port=int(port),
        username=user,
    )


def get_sqlalchemy_engine() -> Engine:
    """Return a SQLAlchemy engine.

    Returns
    -------
    Engine
        A SQLAlchemy engine.
    """

    global _SYNC_ENGINE
    if _SYNC_ENGINE is None:
        connection_string = get_connection_url(db_api=SYNC_DB_API)
        _SYNC_ENGINE = create_engine(connection_string)
    return _SYNC_ENGINE


def get_sqlalchemy_async_engine() -> AsyncEngine:
    """Return a SQLAlchemy async engine generator.

    Returns
    -------
    AsyncEngine
        A SQLAlchemy async engine.
    """

    global _ASYNC_ENGINE
    if _ASYNC_ENGINE is None:
        connection_string = get_connection_url()
        _ASYNC_ENGINE = create_async_engine(connection_string, pool_size=DB_POOL_SIZE)
    return _ASYNC_ENGINE


def get_session_context_manager() -> ContextManager[Session]:
    """Return a SQLAlchemy session context manager.

    Returns
    -------
    ContextManager[Session]
        A SQLAlchemy session context manager.
    """

    return contextlib.contextmanager(get_session)()


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session generator.

    Yields
    ------
    Generator[Session, None, None]
        A SQLAlchemy session generator.
    """

    with Session(get_sqlalchemy_engine(), expire_on_commit=False) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a SQLAlchemy async session.

    Yields
    ------
    AsyncGenerator[AsyncSession, None]
        An async session generator.
    """

    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as async_session:
        yield async_session


def with_new_session(func: Callable) -> Callable:
    """Decorator that creates a new database session for background tasks.

    This decorator ensures that background tasks get their own database session
    rather than reusing a dependency-injected session that may already be closed.

    Usage:
        @with_new_session
        async def background_task_function(..., asession: AsyncSession):
            # Use asession here
            ...

    The decorated function will automatically receive an 'asession' parameter
    with a fresh AsyncSession instance.

    Parameters
    ----------
    func
        The async function to decorate. Must accept 'asession' as a parameter.

    Returns
    -------
    wrapper
        The wrapped function that creates a new session before calling func.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper that creates a new AsyncSession and passes it to func.

        Parameters
        ----------
        args
            Positional arguments to pass to func.
        kwargs
            Keyword arguments to pass to func.

        Returns
        -------
        Any
            The result of calling func with a new AsyncSession.
        """

        async for asession in get_async_session():
            return await func(*args, asession=asession, **kwargs)

    return wrapper
