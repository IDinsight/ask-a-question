"""This module contains tests for the admin API endpoints."""

from fastapi import status
from fastapi.testclient import TestClient


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
