import pytest
import os
from fastapi.testclient import TestClient
from app import create_app


@pytest.fixture(scope="session", autouse=True)
def set_test_environment() -> None:
    os.environ["POSTGRES_USER"] = "postgres-test-user"
    os.environ["POSTGRES_PASSWORD"] = "postgres-test-pw"
    os.environ["POSTGRES_DB"] = "postgres-test-db"
    os.environ["POSTGRES_PORT"] = "5433"


@pytest.fixture
def client(scope: str = "session") -> TestClient:
    app = create_app()
    return TestClient(app)
