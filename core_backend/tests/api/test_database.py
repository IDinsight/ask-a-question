"""This module contains tests for database.py."""

from typing import Any, AsyncGenerator

import pytest

from core_backend.app import database
from core_backend.app.database import with_new_session


@pytest.mark.asyncio
async def test_with_new_session_injects_session_and_forwards_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decorator should inject a new session and forward args/kwargs correctly.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture for mocking.
    """

    captured: dict[str, Any] = {}
    dummy_session = object()
    get_session_called = False

    async def fake_get_async_session() -> AsyncGenerator[object, None]:
        """Fake async generator to yield a dummy session.

        Yields
        ------
        AsyncGenerator[object, None]
            Yields a dummy session object.
        """

        nonlocal get_session_called
        get_session_called = True

        yield dummy_session

    monkeypatch.setattr(database, "get_async_session", fake_get_async_session)

    @with_new_session
    async def background_task(a: int, b: int, *, asession: Any, flag: str) -> str:
        """Background task that captures its args/kwargs and the injected session.

        Parameters
        ----------
        a
            First positional argument.
        b
            Second positional argument.
        asession
            The injected async session.
        flag
            An optional flag.

        Returns
        -------
        str
            A fixed result string.
        """

        captured["a"] = a
        captured["b"] = b
        captured["flag"] = flag
        captured["session"] = asession

        return "result-value"

    result = await background_task(1, 2, flag="hello")

    assert result == "result-value"
    assert captured["a"] == 1
    assert captured["b"] == 2
    assert captured["flag"] == "hello"

    # Session injected from get_async_session.
    assert captured["session"] is dummy_session

    # The async generator was actually called.
    assert get_session_called is True


@pytest.mark.asyncio
async def test_with_new_session_creates_new_session_each_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each call should get its own fresh session instance.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture for mocking.
    """

    sessions_seen_by_func = []
    sessions_yielded = []

    async def fake_get_async_session() -> AsyncGenerator[object, None]:
        """Fake async generator to yield a new session object each time.

        Yields
        ------
        AsyncGenerator[object, None]
            Yields a new session object.
        """

        session = object()
        sessions_yielded.append(session)

        yield session

    monkeypatch.setattr(database, "get_async_session", fake_get_async_session)

    @with_new_session
    async def background_task(*, asession: Any) -> Any:
        """Background task that records the session it received.

        Parameters
        ----------
        asession
            The injected async session.

        Returns
        -------
        Any
            The session received.
        """

        sessions_seen_by_func.append(asession)

        return asession

    s1 = await background_task()
    s2 = await background_task()

    # Function saw exactly the yielded sessions.
    assert sessions_seen_by_func == sessions_yielded
    assert len(sessions_seen_by_func) == 2

    # Sessions should be different objects.
    assert s1 is not s2


@pytest.mark.asyncio
async def test_with_new_session_preserves_function_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@wraps should preserve the original function's __name__ and __doc__.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture for mocking.
    """

    async def fake_get_async_session() -> AsyncGenerator[object, None]:
        """Fake async generator to yield a dummy session.

        Yields
        ------
        AsyncGenerator[object, None]
            Yields a dummy session object.
        """

        yield object()

    monkeypatch.setattr(database, "get_async_session", fake_get_async_session)

    async def original_func(*, asession: Any) -> str:
        """Original function docstring.

        Parameters
        ----------
        asession
            The injected async session.

        Returns
        -------
        str
            A fixed result string.
        """

        return "ok"

    wrapped = with_new_session(original_func)

    assert wrapped.__name__ == original_func.__name__
    assert wrapped.__doc__ == original_func.__doc__


@pytest.mark.asyncio
async def test_with_new_session_raises_if_asession_is_explicitly_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If caller explicitly passes 'asession', the decorator will also pass one,
    causing a TypeError due to duplicate keyword argument.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture for mocking.
    """

    async def fake_get_async_session() -> AsyncGenerator[object, None]:
        """Fake async generator to yield a dummy session.

        Yields
        ------
        AsyncGenerator[object, None]
            Yields a dummy session object.
        """

        yield object()

    monkeypatch.setattr(database, "get_async_session", fake_get_async_session)

    @with_new_session
    async def background_task(*, asession: Any) -> Any:
        """Background task that returns the session it received.

        Parameters
        ----------
        asession
            The injected async session.

        Returns
        -------
        Any
            The session received.
        """

        return asession

    with pytest.raises(TypeError):
        # The decorator will add its own asession=..., so this causes a conflict.
        await background_task(asession="user-provided-session")
