import json
from collections import namedtuple
from datetime import datetime
from typing import Any, Generator, Tuple

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
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
from core_backend.app.database import get_session
from core_backend.app.llm_call import check_output, parse_input
from core_backend.app.llm_call.llm_prompts import AlignmentScore, IdentifiedLanguage
from core_backend.app.question_answer.schemas import (
    ResultState,
    UserQueryRefined,
    UserQueryResponse,
)

# Define namedtuples for the embedding endpoint
EmbeddingData = namedtuple("EmbeddingData", "data")
EmbeddingValues = namedtuple("EmbeddingValues", "embedding")

# Define namedtuples for the completion endpoint
CompletionData = namedtuple("CompletionData", "choices")
CompletionChoice = namedtuple("CompletionChoice", "message")
CompletionMessage = namedtuple("CompletionMessage", "content")


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


@pytest.fixture(scope="session")
def faq_contents(client: TestClient, db_session: Session) -> None:
    with open("tests/api/data/content.json", "r") as f:
        json_data = json.load(f)
    contents = []

    for i, content in enumerate(json_data):
        text_to_embed = content["content_title"] + "\n" + content["content_text"]
        content_embedding = fake_embedding(
            model=LITELLM_MODEL_EMBEDDING,
            input=text_to_embed,
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
        ).data[0]["embedding"]

        contend_db = ContentDB(
            content_id=i,
            user_id="user1",  # TEMPORARY HARDCODED USER ID
            content_embedding=content_embedding,
            content_title=content["content_title"],
            content_text=content["content_text"],
            content_language="ENGLISH",
            content_metadata=content.get("content_metadata", {}),
            created_datetime_utc=datetime.utcnow(),
            updated_datetime_utc=datetime.utcnow(),
        )
        contents.append(contend_db)

    db_session.add_all(contents)
    db_session.commit()


@pytest.fixture(scope="session")
def client(patch_llm_call: pytest.FixtureRequest) -> Generator[TestClient, None, None]:
    app = create_app()
    with TestClient(app) as c:
        yield c


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
    monkeysession.setattr("core_backend.app.contents.models.embedding", fake_embedding)
    monkeysession.setattr(
        "core_backend.app.contents.models.aembedding", async_fake_embedding
    )
    monkeysession.setattr(parse_input, "_classify_safety", mock_return_args)
    monkeysession.setattr(parse_input, "_identify_language", mock_identify_language)
    monkeysession.setattr(parse_input, "_paraphrase_question", mock_return_args)
    monkeysession.setattr(parse_input, "_translate_question", mock_translate_question)
    monkeysession.setattr(check_output, "_get_llm_align_score", mock_get_align_score)
    monkeysession.setattr(
        "core_backend.app.question_answer.routers.get_llm_rag_answer",
        patched_llm_rag_answer,
    )


async def patched_llm_rag_answer(*args: Any, **kwargs: Any) -> str:
    return "monkeypatched_llm_response"


async def mock_get_align_score(*args: Any, **kwargs: Any) -> AlignmentScore:
    return AlignmentScore(score=0.9, reason="test - high score")


async def mock_return_args(
    question: UserQueryRefined, response: UserQueryResponse
) -> Tuple[UserQueryRefined, UserQueryResponse]:
    return question, response


async def mock_identify_language(
    question: UserQueryRefined, response: UserQueryResponse
) -> Tuple[UserQueryRefined, UserQueryResponse]:
    """
    Monkeypatch call to LLM language identification service
    """
    question.original_language = IdentifiedLanguage.ENGLISH
    response.debug_info["original_language"] = "ENGLISH"

    return question, response


async def mock_translate_question(
    question: UserQueryRefined, response: UserQueryResponse
) -> Tuple[UserQueryRefined, UserQueryResponse]:
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


def fake_embedding(*arg: str, **kwargs: str) -> EmbeddingData:
    """
    Replicates `litellm.embedding` function but just generates a random
    list of floats
    """

    embedding_list = (
        np.random.rand(int(PGVECTOR_VECTOR_SIZE)).astype(np.float32).tolist()
    )
    data_obj = EmbeddingData([{"embedding": embedding_list}])

    return data_obj


async def async_fake_embedding(*arg: str, **kwargs: str) -> EmbeddingData:
    """
    Replicates `litellm.aembedding` function but just generates a random
    list of floats
    """

    embedding_list = (
        np.random.rand(int(PGVECTOR_VECTOR_SIZE)).astype(np.float32).tolist()
    )
    data_obj = EmbeddingData([{"embedding": embedding_list}])

    return data_obj


@pytest.fixture(scope="session")
def fullaccess_token() -> str:
    """
    Returns a token with full access
    """
    return create_access_token("user1")  # TEMPORARY HARDCODED USER ID


@pytest.fixture(scope="session")
def readonly_token() -> str:
    """
    Returns a token with readonly access
    """
    return create_access_token(
        "user1"
    )  # TEMPORARY HARDCODED USER ID - this is also fullaccess!


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
