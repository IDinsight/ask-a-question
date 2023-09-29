import pytest
from fastapi.testclient import TestClient
from app import create_app
from typing import Union

Fixture = Union


@pytest.fixture(scope="session")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c
