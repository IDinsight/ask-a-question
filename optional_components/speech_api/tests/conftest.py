import pytest
from fastapi.testclient import TestClient

from speech_api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
