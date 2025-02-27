"""This module contains tests for the root endpoint of the speech API."""

from fastapi import status
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient) -> None:
    """Test the root endpoint of the speech API.

    Parameters
    ----------
    client
        The FastAPI test client.
    """

    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Welcome to the Whisper Service"}
