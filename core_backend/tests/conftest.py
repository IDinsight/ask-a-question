import pytest
import os
from fastapi.testclient import TestClient
from app import create_app
from typing import Union

Fixture = Union


@pytest.fixture(scope="session", autouse=True)
def set_test_environment() -> None:
    os.environ["POSTGRES_USER"] = "postgres-test-user"
    os.environ["POSTGRES_PASSWORD"] = "postgres-test-pw"
    os.environ["POSTGRES_DB"] = "postgres-test-db"


@pytest.fixture(scope="session")
def client(set_test_environment: Union[None]) -> TestClient:
    app = create_app()
    return TestClient(app)
