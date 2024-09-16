import pytest
from fastapi.testclient import TestClient

from ..main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
