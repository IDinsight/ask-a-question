from datetime import datetime, timezone
from typing import AsyncGenerator, List

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from pytest import Item
from pytest_asyncio import is_async_test

from core_backend.app import create_app
from core_backend.app.auth.dependencies import create_access_token
from core_backend.app.database import get_session_context_manager
from core_backend.app.users.models import UserDB
from core_backend.app.utils import get_key_hash, get_password_salted_hash

TEST_USERNAME = "test_username"
TEST_PASSWORD = "test_password"
TEST_USER_API_KEY = "test_api_key"


def pytest_collection_modifyitems(items: List[Item]) -> None:
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c


# create command line arguments for pytest as per https://stackoverflow.com/a/42145604/7664921
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--validation_data_path", type=str, help="Path to validation data")
    parser.addoption("--ud_rules_path", type=str, help="Path to UD rules data")
    parser.addoption(
        "--validation_data_question_col",
        type=str,
        help="Question column in validation data",
    )
    parser.addoption(
        "--validation_data_label_col",
        type=str,
        help="Urgency label column in validation data",
    )
    parser.addoption(
        "--ud_rules_col",
        type=str,
        help="The column in UD rules data that has the urgency rules",
    )
    parser.addoption(
        "--notification_topic",
        type=str,
        help="AWS SNS topic to send notification to. If none, no notification is sent",
        nargs="?",
        default=None,
    )
    parser.addoption(
        "--aws_profile",
        nargs="?",
        type=str,
        help="Name of AWS profile with access to S3 in case data is stored there "
        "(optional)",
        default=None,
    )


@pytest.fixture(scope="session")
def user(client: TestClient) -> UserDB:
    """
    Returns a user dict
    """

    with get_session_context_manager() as db_session:
        user1 = UserDB(
            username=TEST_USERNAME,
            hashed_password=get_password_salted_hash(key=TEST_PASSWORD),
            hashed_api_key=get_key_hash(key=TEST_USER_API_KEY),
            created_datetime_utc=datetime.now(timezone.utc),
            updated_datetime_utc=datetime.now(timezone.utc),
        )

        db_session.add(user1)
        db_session.commit()

    return user1


@pytest.fixture(scope="session")
def api_key() -> str:
    """
    Returns an API key
    """
    return TEST_USER_API_KEY


@pytest.fixture(scope="session")
def fullaccess_token(user: UserDB) -> str:
    """
    Returns a token with full access

    NB: FIX THE CALL TO `create_access_token` WHEN WE WANT THIS TEST TO PASS AGAIN!
    """
    return create_access_token(username=user.username)  # type: ignore


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".

    args = [
        "validation_data_path",
        "ud_rules_path",
        "validation_data_question_col",
        "validation_data_label_col",
        "ud_rules_col",
        "notification_topic",
        "aws_profile",
    ]

    for arg in args:
        option_value = metafunc.config.option.__getattribute__(arg)
        if arg in metafunc.fixturenames and option_value is not None:
            metafunc.parametrize(arg, [option_value], scope="session")
        else:
            metafunc.parametrize(arg, [None], scope="session")
