from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app import create_app
from core_backend.app.configs.app_config import QDRANT_COLLECTION_NAME
from core_backend.app.db.db_models import UserQueryDB, UserQueryResponseDB
from core_backend.app.db.vector_db import get_qdrant_client
from core_backend.app.schemas import UserQueryResponse


@pytest.fixture(scope="session")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def vectordb_client() -> TestClient:
    client = get_qdrant_client()
    yield client
    client.delete_collection(collection_name=QDRANT_COLLECTION_NAME)


@pytest.fixture(scope="session")
def monkeysession() -> pytest.FixtureRequest:
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session", autouse=True)
def patch_save_to_db(monkeysession: pytest.FixtureRequest) -> None:
    async def mock_save_query_to_db(
        asession: AsyncSession, feedback_secret_key: str, user_query: UserQueryDB
    ) -> UserQueryDB:
        return UserQueryDB(
            query_id=1,
            feedback_secret_key=feedback_secret_key,
            query_datetime_utc=datetime.utcnow(),
            **user_query.model_dump(),
        )

    async def mock_save_response_to_db(
        asession: AsyncSession, user_query_db: UserQueryDB, response: UserQueryResponse
    ) -> UserQueryResponseDB:
        return UserQueryResponseDB(
            query_id=user_query_db.query_id,
            content_response=response.model_dump()["content_response"],
            llm_response=response.model_dump()["llm_response"],
            response_datetime_utc=datetime.utcnow(),
        )

    monkeysession.setattr(
        "core_backend.app.routers.question_answer.save_user_query_to_db",
        mock_save_query_to_db,
    )
    monkeysession.setattr(
        "core_backend.app.routers.question_answer.save_query_response_to_db",
        mock_save_response_to_db,
    )


# create command line arguments for pytestas per https://stackoverflow.com/a/42145604/7664921
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--validation_data_path", type=str, help="Path to validation data")
    parser.addoption("--content_data_path", type=str, help="Path to validation data")
    parser.addoption(
        "--validation_data_question_col",
        type=str,
        help="Question column in validation data",
    )
    parser.addoption(
        "--validation_data_label_col",
        type=str,
        help="Content label column in validation data",
    )
    parser.addoption(
        "--content_data_label_col",
        type=str,
        help="Content label column in content data",
    )
    parser.addoption(
        "--content_data_text_col",
        type=str,
        help="Content text body column in content data",
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


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".

    args = [
        "validation_data_path",
        "content_data_path",
        "validation_data_question_col",
        "validation_data_label_col",
        "content_data_label_col",
        "content_data_text_col",
        "notification_topic",
        "aws_profile",
    ]

    for arg in args:
        option_value = metafunc.config.option.__getattribute__(arg)
        if arg in metafunc.fixturenames and option_value is not None:
            metafunc.parametrize(arg, [option_value])
        else:
            metafunc.parametrize(arg, [None])
