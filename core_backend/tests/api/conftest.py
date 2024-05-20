import json
import random
from collections import namedtuple
from datetime import datetime
from typing import Any, Dict, Generator, List, Tuple

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
from core_backend.app.llm_call import process_input, process_output
from core_backend.app.llm_call.llm_prompts import AlignmentScore, IdentifiedLanguage
from core_backend.app.question_answer.schemas import (
    ResultState,
    UserQueryRefined,
    UserQueryResponse,
)
from core_backend.app.question_dashboard.schemas import QuestionDashBoard
from core_backend.app.urgency_rules.models import UrgencyRuleDB

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
async def faq_contents(client: TestClient, db_session: Session) -> None:
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
            content_embedding=content_embedding,
            content_title=content["content_title"],
            content_text=content["content_text"],
            content_language="ENGLISH",
            content_metadata=content.get("content_metadata", {}),
            created_datetime_utc=datetime.utcnow(),
            updated_datetime_utc=datetime.utcnow(),
        )
        contents.append(content_db)

    db_session.add_all(contents)
    db_session.commit()


@pytest.fixture(scope="session")
async def urgency_rules(client: TestClient, db_session: Session) -> int:
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


async def patched_llm_rag_answer(*args: Any, **kwargs: Any) -> str:
    return "monkeypatched_llm_response"


async def mock_get_align_score(*args: Any, **kwargs: Any) -> AlignmentScore:
    return AlignmentScore(score=0.9, reason="test - high score")


async def mock_return_args(
    question: UserQueryRefined, response: UserQueryResponse
) -> Tuple[UserQueryRefined, UserQueryResponse]:
    return question, response


async def mock_detect_urgency(urgency_rule: str, message: str) -> Dict[str, Any]:
    return {
        "statement": urgency_rule,
        "probability": 0.7,
        "reason": "this is a mocked response",
    }


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


async def async_fake_embedding(*arg: str, **kwargs: str) -> List[float]:
    """
    Replicates `embedding` function but just generates a random
    list of floats
    """

    embedding_list = (
        np.random.rand(int(PGVECTOR_VECTOR_SIZE)).astype(np.float32).tolist()
    )
    return embedding_list


async def mock_dashboard_stats(*arg: str, **kwargs: str):
    """
    Replicates question_dashboard.models.get_dashboard_stats but generates random
    statistics.
    """
    return QuestionDashBoard(
        six_months_question=[random.randint(0, 100) for _ in range(6)],
        sis_months_upvote=[random.randint(0, 100) for _ in range(6)],
    )


@pytest.fixture(scope="session")
def fullaccess_token() -> str:
    """
    Returns a token with full access
    """
    return create_access_token("fullaccess")


@pytest.fixture(scope="session")
def readonly_token() -> str:
    """
    Returns a token with readonly access
    """
    return create_access_token("readonly")


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
