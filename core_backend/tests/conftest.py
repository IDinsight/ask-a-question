from typing import Union

import pytest
from app import create_app
from fastapi.testclient import TestClient

Fixture = Union


@pytest.fixture(scope="session")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c
