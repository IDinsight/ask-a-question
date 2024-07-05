import json
import os
from collections import namedtuple
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional, Tuple

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pytest import Item
from pytest_asyncio import is_async_test
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from core_backend.app import create_app
from core_backend.app.auth.dependencies import create_access_token
from core_backend.app.config import (
    LITELLM_API_KEY,
    LITELLM_ENDPOINT,
    LITELLM_MODEL_EMBEDDING,
)
from core_backend.app.contents.config import PGVECTOR_VECTOR_SIZE
from core_backend.app.contents.models import ContentDB
from core_backend.app.database import build_connection_string, get_session
from core_backend.app.llm_call import process_input, process_output
from core_backend.app.llm_call.llm_prompts import (
    RAG,
    AlignmentScore,
    IdentifiedLanguage,
)
from core_backend.app.question_answer.schemas import (
    QueryRefined,
    QueryResponse,
    ResultState,
)
from core_backend.app.urgency_rules.models import UrgencyRuleDB
from core_backend.app.users.models import UserDB
from core_backend.app.utils import get_key_hash, get_password_salted_hash

# Define namedtuples for the embedding endpoint
EmbeddingData = namedtuple("EmbeddingData", "data")
EmbeddingValues = namedtuple("EmbeddingValues", "embedding")

# Define namedtuples for the completion endpoint
CompletionData = namedtuple("CompletionData", "choices")
CompletionChoice = namedtuple("CompletionChoice", "message")
CompletionMessage = namedtuple("CompletionMessage", "content")

TEST_ADMIN_USERNAME = "admin"
TEST_ADMIN_PASSWORD = "admin_password"
TEST_ADMIN_API_KEY = "admin_api_key"


TEST_USERNAME = "test_username"
TEST_PASSWORD = "test_password"
TEST_USER_API_KEY = "test_api_key"
TEST_CONTENT_QUOTA = 50
TEST_API_QUOTA = 2000

TEST_USERNAME_2 = "test_username_2"
TEST_PASSWORD_2 = "test_password_2"
TEST_USER_API_KEY_2 = "test_api_key_2"
TEST_CONTENT_QUOTA_2 = 50
TEST_API_QUOTA_2 = 2000


def pytest_collection_modifyitems(items: List[Item]) -> None:
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session")
def db_session() -> Generator[Session, None, None]:
    """Create a test database session."""
    session_gen = get_session()
    session = next(session_gen)

    try:
        yield session
    finally:
        session.rollback()
        next(session_gen, None)


# We recreate engine and session to ensure it is in the same
# event loop as the test. Without this we get "Future attached to different loop" error.
# See https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html#using-multiple-asyncio-event-loops
@pytest.fixture(scope="function")
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    connection_string = build_connection_string()
    engine = create_async_engine(connection_string, pool_size=20)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def asession(
    async_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(async_engine, expire_on_commit=False) as async_session:
        yield async_session


@pytest.fixture(scope="session", autouse=True)
def admin_user(client: TestClient, db_session: Session) -> None:
    admin_user = UserDB(
        username=TEST_ADMIN_USERNAME,
        hashed_password=get_password_salted_hash(TEST_ADMIN_PASSWORD),
        hashed_api_key=get_key_hash(TEST_ADMIN_API_KEY),
        content_quota=None,
        api_daily_quota=None,
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )

    db_session.add(admin_user)
    db_session.commit()
    yield admin_user.user_id


@pytest.fixture(scope="session")
def user1(client: TestClient, db_session: Session) -> None:
    stmt = select(UserDB).where(UserDB.username == TEST_USERNAME)
    result = db_session.execute(stmt)
    user = result.scalar_one()
    yield user.user_id


@pytest.fixture(scope="session", autouse=True)
def user(
    client: TestClient, db_session: Session, admin_user, fullaccess_token_admin: str
) -> None:
    client.post(
        "/user",
        json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "content_quota": TEST_CONTENT_QUOTA,
            "api_daily_quota": TEST_API_QUOTA,
        },
        headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
    )
    client.post(
        "/user",
        json={
            "username": TEST_USERNAME_2,
            "password": TEST_PASSWORD_2,
            "content_quota": TEST_CONTENT_QUOTA_2,
            "api_daily_quota": TEST_API_QUOTA_2,
        },
        headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
    )


@pytest.fixture(scope="session")
async def faq_contents(client: TestClient, user1: int, db_session: Session) -> None:
    with open("tests/api/data/content.json", "r") as f:
        json_data = json.load(f)
    contents = []

    for i, content in enumerate(json_data):
        text_to_embed = content["content_title"] + "\n" + content["content_text"]
        content_embedding = await async_fake_embedding(
            model=LITELLM_MODEL_EMBEDDING,
            input=text_to_embed,
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
        )
        content_db = ContentDB(
            content_id=i,
            user_id=user1,
            content_embedding=content_embedding,
            content_title=content["content_title"],
            content_text=content["content_text"],
            content_metadata=content.get("content_metadata", {}),
            created_datetime_utc=datetime.utcnow(),
            updated_datetime_utc=datetime.utcnow(),
        )
        contents.append(content_db)

    db_session.add_all(contents)
    db_session.commit()


@pytest.fixture(
    scope="module",
    params=[
        ("Tag1"),
        ("tag2",),
    ],
)
def existing_tag_id(
    request: pytest.FixtureRequest, client: TestClient, fullaccess_token: str
) -> Generator[str, None, None]:
    response = client.post(
        "/tag",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
        json={
            "tag_name": request.param[0],
        },
    )
    tag_id = response.json()["tag_id"]
    yield tag_id
    client.delete(
        f"/tag/{tag_id}",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
    )


@pytest.fixture(scope="session")
async def urgency_rules(client: TestClient, user1: int, db_session: Session) -> int:
    with open("tests/api/data/urgency_rules.json", "r") as f:
        json_data = json.load(f)
    rules = []

    for i, rule in enumerate(json_data):
        rule_embedding = await async_fake_embedding(
            model=LITELLM_MODEL_EMBEDDING,
            input=rule["urgency_rule_text"],
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
        )

        rule_db = UrgencyRuleDB(
            urgency_rule_id=i,
            user_id=user1,
            urgency_rule_text=rule["urgency_rule_text"],
            urgency_rule_vector=rule_embedding,
            urgency_rule_metadata=rule.get("urgency_rule_metadata", {}),
            created_datetime_utc=datetime.utcnow(),
            updated_datetime_utc=datetime.utcnow(),
        )
        rules.append(rule_db)

    db_session.add_all(rules)
    db_session.commit()

    return len(rules)


@pytest.fixture(scope="session")
def client(patch_llm_call: pytest.FixtureRequest) -> Generator[TestClient, None, None]:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6397")
    app = create_app(redis_url)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def temp_user_api_key_and_api_quota(
    request: pytest.FixtureRequest,
    fullaccess_token_admin: str,
    client: TestClient,
) -> Generator[tuple[str, int], None, None]:
    username = request.param["username"]
    api_daily_quota = request.param["api_daily_quota"]

    if api_daily_quota is not None:
        json = {
            "username": username,
            "password": "temp_password",
            "content_quota": 50,
            "api_daily_quota": api_daily_quota,
        }
    else:
        json = {
            "username": username,
            "password": "temp_password",
            "content_quota": 50,
        }

    client.post(
        "/user",
        json=json,
        headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
    )

    access_token = create_access_token(username)
    response_key = client.put(
        "/user/rotate-key",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    api_key = response_key.json()["new_api_key"]

    yield (api_key, api_daily_quota)


@pytest.fixture(scope="session")
def monkeysession(
    request: pytest.FixtureRequest,
) -> Generator[pytest.MonkeyPatch, None, None]:
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session", autouse=True)
def patch_llm_call(monkeysession: pytest.MonkeyPatch) -> None:
    """
    Monkeypatch call to LLM embeddings service
    """
    monkeysession.setattr(
        "core_backend.app.contents.models.embedding", async_fake_embedding
    )
    monkeysession.setattr(
        "core_backend.app.urgency_rules.models.embedding", async_fake_embedding
    )
    monkeysession.setattr(process_input, "_classify_safety", mock_return_args)
    monkeysession.setattr(process_input, "_classify_on_off_topic", mock_return_args)
    monkeysession.setattr(process_input, "_identify_language", mock_identify_language)
    monkeysession.setattr(process_input, "_paraphrase_question", mock_return_args)
    monkeysession.setattr(process_input, "_translate_question", mock_translate_question)
    monkeysession.setattr(process_output, "_get_llm_align_score", mock_get_align_score)
    monkeysession.setattr(
        "core_backend.app.urgency_detection.routers.detect_urgency", mock_detect_urgency
    )
    monkeysession.setattr(
        "core_backend.app.question_answer.routers.get_llm_rag_answer",
        patched_llm_rag_answer,
    )


async def patched_llm_rag_answer(*args: Any, **kwargs: Any) -> RAG:
    return RAG(answer="patched llm response", extracted_info=[])


async def mock_get_align_score(*args: Any, **kwargs: Any) -> AlignmentScore:
    return AlignmentScore(score=0.9, reason="test - high score")


async def mock_return_args(
    question: QueryRefined, response: QueryResponse, metadata: Optional[dict]
) -> Tuple[QueryRefined, QueryResponse]:
    return question, response


async def mock_detect_urgency(
    urgency_rules: List[str], message: str, metadata: Optional[dict]
) -> Dict[str, Any]:
    return {
        "best_matching_rule": "made up rule",
        "probability": 0.7,
        "reason": "this is a mocked response",
    }


async def mock_identify_language(
    question: QueryRefined, response: QueryResponse, metadata: Optional[dict]
) -> Tuple[QueryRefined, QueryResponse]:
    """
    Monkeypatch call to LLM language identification service
    """
    question.original_language = IdentifiedLanguage.ENGLISH
    response.debug_info["original_language"] = "ENGLISH"

    return question, response


async def mock_translate_question(
    question: QueryRefined, response: QueryResponse, metadata: Optional[dict]
) -> Tuple[QueryRefined, QueryResponse]:
    """
    Monkeypatch call to LLM translation service
    """
    if question.original_language is None:
        response.state = ResultState.ERROR
        raise ValueError(
            (
                "Language hasn't been identified. "
                "Identify language before running translation"
            )
        )
    response.debug_info["translated_question"] = question.query_text

    return question, response


async def async_fake_embedding(*arg: str, **kwargs: str) -> List[float]:
    """
    Replicates `embedding` function but just generates a random
    list of floats
    """

    embedding_list = (
        np.random.rand(int(PGVECTOR_VECTOR_SIZE)).astype(np.float32).tolist()
    )
    return embedding_list


@pytest.fixture(scope="session")
def fullaccess_token_admin() -> str:
    """
    Returns a token with full access
    """
    return create_access_token(TEST_ADMIN_USERNAME)


@pytest.fixture(scope="session")
def fullaccess_token() -> str:
    """
    Returns a token with full access
    """
    return create_access_token(TEST_USERNAME)


@pytest.fixture(scope="session")
def fullaccess_token_user2() -> str:
    """
    Returns a token with full access
    """
    return create_access_token(TEST_USERNAME_2)


@pytest.fixture(scope="session")
def api_key_user1(client, fullaccess_token: str) -> str:
    """
    Returns a token with full access
    """
    response = client.put(
        "/user/rotate-key",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
    )
    return response.json()["new_api_key"]


@pytest.fixture(scope="session")
def api_key_user2(client, fullaccess_token_user2: str) -> str:
    """
    Returns a token with full access
    """
    response = client.put(
        "/user/rotate-key",
        headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
    )
    return response.json()["new_api_key"]


@pytest.fixture(scope="session", autouse=True)
def patch_httpx_call(monkeysession: pytest.MonkeyPatch) -> None:
    """
    Monkeypatch call to httpx service
    """

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, exc_type: str, exc: str, tb: str) -> None:
            pass

        async def post(self, *args: str, **kwargs: str) -> httpx.Response:
            return httpx.Response(200, json={"status": "success"})

    monkeysession.setattr(httpx, "AsyncClient", MockClient)
