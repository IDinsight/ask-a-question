"""This module contains fixtures for the speech API tests."""

import pytest
from fastapi.testclient import TestClient

from ..main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app.

    Returns
    -------
    TestClient
        The test client for the FastAPI app.
    """

    return TestClient(app)
