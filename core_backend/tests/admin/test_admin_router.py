"""This module contains tests for the admin API endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def test_healthcheck(client: TestClient) -> None:
    """Test the healthcheck endpoint.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    """

    response = client.get("/healthcheck")

    assert response.status_code == status.HTTP_200_OK, f"response: {response.json()}"
    assert response.json() == {"status": "ok"}


def test_healthcheck_database_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that a failed database check is reported as a 500 with the message.

    Parameters
    ----------
    client
        The test client for the FastAPI application.
    monkeypatch
        Pytest monkeypatch fixture.
    """

    async def fake_check(*, asession: AsyncSession) -> str:
        """Pretend the database is unreachable."""
        return "Failed database connection: down"

    monkeypatch.setattr(
        "app.admin.router.service.check_database_connection", fake_check
    )

    response = client.get("/healthcheck")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"message": "Failed database connection: down"}
