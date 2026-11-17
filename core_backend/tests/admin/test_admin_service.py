"""Unit tests for `app.admin.service` (no database: the session is a mock)."""

from unittest.mock import AsyncMock

from sqlalchemy.exc import OperationalError

from app.admin.service import check_database_connection


async def test_check_database_connection_ok() -> None:
    """Test that a responsive database yields no error message."""

    asession = AsyncMock()
    assert await check_database_connection(asession=asession) is None
    asession.execute.assert_awaited_once()


async def test_check_database_connection_failure() -> None:
    """Test that a database error is returned as a message, not raised."""

    asession = AsyncMock()
    asession.execute.side_effect = OperationalError("SELECT 1;", {}, Exception("down"))

    message = await check_database_connection(asession=asession)

    assert message is not None
    assert message.startswith("Failed database connection:")
    assert "down" in message
