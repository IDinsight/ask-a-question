"""Unit tests for `app.question_answer.service`.

These tests never touch Postgres, Redis or the network: repository functions,
LLM calls, HTTP clients and cloud SDK clients are replaced with fakes on the service
module (`monkeypatch.setattr(service, "<name>", fake)`), and Redis is replaced with
the in-memory `FakeRedis` below.

NB: `tests/conftest.py::patch_llm_call` replaces some service functions for the
whole session (`_identify_language`, `_classify_safety`, `_translate_question`,
`_paraphrase_question`, `_get_llm_align_score`, `get_llm_rag_answer`, ...). The real
functions are imported by name below; that import runs at collection time, before
the session patch is applied, so the names in this module refer to the real
implementations.
"""

import copy
import inspect
import json
from functools import partial
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urljoin

import httpx
import pytest
from fastapi import status
from litellm import token_counter
from sqlalchemy.exc import IntegrityError

from app.contents.schemas import QuerySearchResult
from app.core.config import LITELLM_MODEL_CHAT, TURNIO_API_BASE
from app.core.security import get_random_int32
from app.core.utils import LLMCallException
from app.question_answer import service
from app.question_answer.models import QueryDB
from app.question_answer.schemas import (
    ContentFeedback,
    ErrorType,
    FeedbackSentiment,
    IdentifiedLanguage,
    QueryAudioResponse,
    QueryBase,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
    ResponseFeedbackBase,
)
from app.question_answer.service import (
    INTERNAL_SERVER_ERROR_MESSAGE,
    LLM_CALL_ERROR_MESSAGE,
    PARAPHRASE_FAILED_MESSAGE,
    RAG,
    RAG_FAILURE_MESSAGE,
    TRANSLATE_FAILED_MESSAGE,
    TURNIO_ACK_MESSAGE,
    AlignmentScore,
    ChatHistory,
    FeedbackRejectedError,
    SafetyClassification,
    _check_align_score,
    _classify_safety,
    _get_llm_align_score,
    _identify_language,
    _paraphrase_question,
    _translate_question,
    _truncate_chat_history,
    append_message_content_to_chat_history,
    get_context_string_from_search_results,
    get_llm_rag_answer,
    init_chat_history,
    init_user_query_and_chat_histories,
    send_turn_text_message,
)

CHAT_PARAMS: dict[str, Any] = {
    "max_input_tokens": 1000,
    "max_output_tokens": 100,
    "model": LITELLM_MODEL_CHAT,
}
SESSION_ID = 11


# =====================================================================================
# Fakes and shared fixtures
# =====================================================================================


class FakeRedis:
    """In-memory stand-in for the subset of `redis.asyncio.Redis` the service uses."""

    def __init__(self) -> None:
        """Start with an empty store."""

        self.store: dict[str, Any] = {}

    async def get(self, key: str) -> Any:
        """Return the stored value or `None`.

        Parameters
        ----------
        key
            The cache key.

        Returns
        -------
        Any
            The stored value, or `None` if the key is missing.
        """

        return self.store.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None) -> None:
        """Store a value (the expiry is ignored).

        Parameters
        ----------
        key
            The cache key.
        value
            The value to store.
        ex
            Expiry in seconds (ignored).
        """

        self.store[key] = value

    async def delete(self, key: str) -> None:
        """Remove a key if it exists.

        Parameters
        ----------
        key
            The cache key.
        """

        self.store.pop(key, None)


class FakeAiohttpResponse:
    """Stand-in for an `aiohttp` response used as an async context manager."""

    def __init__(
        self,
        *,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
        json_data: Any = None,
        status_code: int = status.HTTP_200_OK,
        text: str = "",
    ) -> None:
        """Store the canned response.

        Parameters
        ----------
        body
            The raw body returned by `read()`.
        headers
            The response headers.
        json_data
            The value returned by `json()`.
        status_code
            The HTTP status.
        text
            The value returned by `text()`.
        """

        self._body = body
        self._json = json_data
        self._text = text
        self.headers = headers or {}
        self.status = status_code

    async def __aenter__(self) -> "FakeAiohttpResponse":
        """Enter the context.

        Returns
        -------
        FakeAiohttpResponse
            This response.
        """

        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        """Exit the context.

        Parameters
        ----------
        exc_info
            Exception information (ignored).
        """

    async def json(self) -> Any:
        """Return the canned JSON body.

        Returns
        -------
        Any
            The JSON body.
        """

        return self._json

    async def read(self) -> bytes:
        """Return the canned raw body.

        Returns
        -------
        bytes
            The raw body.
        """

        return self._body

    async def text(self) -> str:
        """Return the canned text body.

        Returns
        -------
        str
            The text body.
        """

        return self._text


class FakeAiohttpClient:
    """Stand-in for `aiohttp.ClientSession` that records requests."""

    def __init__(self, response: FakeAiohttpResponse) -> None:
        """Store the response to return for every request.

        Parameters
        ----------
        response
            The canned response.
        """

        self.calls: list[tuple[str, str, Any]] = []
        self.response = response

    async def __aenter__(self) -> "FakeAiohttpClient":
        """Enter the context.

        Returns
        -------
        FakeAiohttpClient
            This client.
        """

        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        """Exit the context.

        Parameters
        ----------
        exc_info
            Exception information (ignored).
        """

    def get(self, url: str) -> FakeAiohttpResponse:
        """Record a GET request.

        Parameters
        ----------
        url
            The request URL.

        Returns
        -------
        FakeAiohttpResponse
            The canned response.
        """

        self.calls.append(("GET", url, None))
        return self.response

    def post(self, url: str, json: Any = None) -> FakeAiohttpResponse:
        """Record a POST request.

        Parameters
        ----------
        url
            The request URL.
        json
            The JSON payload.

        Returns
        -------
        FakeAiohttpResponse
            The canned response.
        """

        self.calls.append(("POST", url, json))
        return self.response


class FakeCrossEncoder:
    """Cross-encoder stand-in that returns fixed scores."""

    def __init__(self, scores: list[float]) -> None:
        """Store the scores.

        Parameters
        ----------
        scores
            One score per (query, content) pair, in input order.
        """

        self.pairs: list[tuple[str, str]] = []
        self.scores = scores

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        """Record the pairs and return the fixed scores.

        Parameters
        ----------
        pairs
            The (query, content) pairs.

        Returns
        -------
        list[float]
            The fixed scores.
        """

        self.pairs = pairs
        return self.scores


class FakeTurnResponse:
    """A fake `httpx` response for the Turn.io API."""

    def __init__(self, status_code: int, data: dict[str, Any]) -> None:
        """Initialize the fake response.

        Parameters
        ----------
        status_code
            The HTTP status code of the response.
        data
            The JSON data of the response.
        """

        self._data = data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise an error for bad status codes, like `httpx` does."""

        if self.status_code >= status.HTTP_400_BAD_REQUEST:
            raise httpx.HTTPStatusError(
                message="Request failed",
                request=httpx.Request("POST", "https://example.com/messages"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict[str, Any]:
        """Return the JSON data of the response.

        Returns
        -------
        dict[str, Any]
            The JSON data of the response.
        """

        return self._data


class RecordingAsyncClient:
    """Fake `httpx.AsyncClient` that records the last POST call."""

    def __init__(self, response: FakeTurnResponse) -> None:
        """Initialize the recording client.

        Parameters
        ----------
        response
            The fake response to return on POST requests.
        """

        self.last_headers: dict[str, Any] = {}
        self.last_json: dict[str, Any] = {}
        self.last_url: str = ""
        self.response = response

    async def post(
        self, url: str, json: dict[str, Any], headers: dict[str, Any]
    ) -> FakeTurnResponse:
        """Record the POST request parameters and return the fake response.

        Parameters
        ----------
        url
            The URL of the POST request.
        json
            The JSON payload of the POST request.
        headers
            The headers of the POST request.

        Returns
        -------
        FakeTurnResponse
            The fake response.
        """

        self.last_headers = headers
        self.last_json = json
        self.last_url = url
        return self.response


async def _passthrough(
    *,
    metadata: dict | None = None,
    query_refined: QueryRefined,
    response: QueryResponse,
) -> tuple[QueryRefined, QueryResponse]:
    """Guardrail stand-in that changes nothing.

    Parameters
    ----------
    metadata
        Unused.
    query_refined
        The refined query.
    response
        The response.

    Returns
    -------
    tuple[QueryRefined, QueryResponse]
        The inputs, unchanged.
    """

    return query_refined, response


def _search_results() -> dict[int, QuerySearchResult]:
    """Build two search results.

    Returns
    -------
    dict[int, QuerySearchResult]
        The search results.
    """

    return {
        1: QuerySearchResult(distance=0.2, id=1, text="hello world", title="World"),
        2: QuerySearchResult(
            distance=0.2, id=2, text="goodbye universe", title="Universe"
        ),
    }


def _error_response(**overrides: Any) -> QueryResponseError:
    """Build a guardrail-failure response.

    Parameters
    ----------
    overrides
        Fields to override.

    Returns
    -------
    QueryResponseError
        The error response.
    """

    fields: dict[str, Any] = {
        "debug_info": {},
        "error_message": "Guardrail failure: bad query",
        "error_type": ErrorType.QUERY_UNSAFE,
        "feedback_secret_key": "abc123",
        "llm_response": None,
        "query_id": 124,
        "search_results": _search_results(),
        "session_id": SESSION_ID,
    }
    fields.update(overrides)
    return QueryResponseError(**fields)


@pytest.fixture
def fake_redis() -> FakeRedis:
    """Provide an empty in-memory Redis.

    Returns
    -------
    FakeRedis
        The fake Redis client.
    """

    return FakeRedis()


@pytest.fixture
def mock_logger(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the service logger so log calls can be asserted.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.

    Returns
    -------
    MagicMock
        The mock logger.
    """

    logger = MagicMock()
    monkeypatch.setattr(service, "logger", logger)
    return logger


@pytest.fixture
def query_refined() -> QueryRefined:
    """Build an English refined query that asks for an LLM answer.

    Returns
    -------
    QueryRefined
        The refined query.
    """

    return QueryRefined(
        generate_llm_response=True,
        generate_tts=False,
        original_language=IdentifiedLanguage.ENGLISH,
        query_text="How do I stay hydrated?",
        query_text_original="How do I stay hydrated?",
        session_id=SESSION_ID,
        workspace_doc_language="ENGLISH",
        workspace_id=1,
    )


@pytest.fixture
def query_response() -> QueryResponse:
    """Build a successful response with search results and an LLM answer.

    Returns
    -------
    QueryResponse
        The response.
    """

    return QueryResponse(
        debug_info={},
        feedback_secret_key="abc123",
        llm_response="Drink water.",
        query_id=124,
        search_results=_search_results(),
        session_id=SESSION_ID,
    )


@pytest.fixture
def bypass_input_guardrails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the input guardrail decorators no-ops.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    """

    for name in (
        "_classify_safety",
        "_identify_language",
        "_paraphrase_question",
        "_translate_question",
    ):
        monkeypatch.setattr(service, name, _passthrough)


# =====================================================================================
# Chat history helpers
# =====================================================================================


async def test_init_user_query_and_chat_histories(fake_redis: FakeRedis) -> None:
    """Test that the `QueryBase` object returned after initializing the user query
    and chat histories contains the expected attributes.

    Parameters
    ----------
    fake_redis
        The in-memory Redis client.
    """

    query_text = "I have a stomachache."
    reset_chat_history = False
    user_query_object = QueryBase(generate_llm_response=False, query_text=query_text)
    assert user_query_object.generate_llm_response is False
    assert user_query_object.session_id is None
    user_query_object.session_id = get_random_int32()

    # Mock return values
    mock_init_chat_history_return_value = (
        None,
        None,
        [{"role": "system", "content": "You are a helpful assistant."}],
        {"model": "test-model", "max_input_tokens": 1000, "max_output_tokens": 200},
    )
    mock_search_query_json_str = (
        '{"message_type": "NEW", "query": "stomachache and possible remedies"}'
    )

    with (
        patch(
            "app.question_answer.service.init_chat_history",
            new_callable=AsyncMock,
        ) as mock_init_chat_history,
        patch(
            "app.question_answer.service.get_chat_response",
            new_callable=AsyncMock,
        ) as mock_get_chat_response,
    ):
        mock_init_chat_history.return_value = mock_init_chat_history_return_value
        mock_get_chat_response.return_value = mock_search_query_json_str

        # Call the function under test
        user_query = await init_user_query_and_chat_histories(
            redis_client=fake_redis,  # type: ignore[arg-type]
            reset_chat_history=reset_chat_history,
            user_query=user_query_object,
        )
        chat_query_params = user_query.chat_query_params
        assert isinstance(chat_query_params, dict)

        # Check that the mocked functions were called as expected.
        mock_init_chat_history.assert_called_once_with(
            chat_cache_key=f"chatCache:{user_query.session_id}",
            chat_params_cache_key=f"chatParamsCache:{user_query.session_id}",
            redis_client=fake_redis,
            reset=reset_chat_history,
            session_id=str(user_query.session_id),
        )
        mock_get_chat_response.assert_called_once()

        # After initialization, the user query object should have the following
        # attributes set correctly.
        assert user_query.generate_llm_response is True
        assert user_query.query_text == query_text
        assert (
            chat_query_params["chat_cache_key"] == f"chatCache:{user_query.session_id}"
        )
        assert chat_query_params["message_type"] == "NEW"
        assert chat_query_params["search_query"] == "stomachache and possible remedies"


def test__truncate_chat_history() -> None:
    """Test chat history truncation scenarios."""

    # Empty chat should return empty chat.
    chat_history: list[dict[str, str | None]] = []
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        total_tokens_for_next_generation=50,
    )
    assert len(chat_history) == 0

    # Non-empty chat that fits within the model context length should not be truncated.
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]

    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        total_tokens_for_next_generation=50,
    )
    assert len(chat_history) == 1
    assert chat_history[0]["content"] == "You are a helpful assistant."
    assert chat_history[0]["role"] == "system"

    # Chat history that exceeds the model context length should be truncated. In this
    # case, however, since the chat history only has a system message, the system
    # message should NOT be truncated.
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        total_tokens_for_next_generation=150,
    )
    assert len(chat_history) == 1
    assert chat_history[0]["role"] == "system"
    assert chat_history[0]["content"] == "You are a helpful assistant."

    # Exact model context length should not be truncated.
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    chat_history_tokens = token_counter(messages=chat_history, model=LITELLM_MODEL_CHAT)
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=chat_history_tokens + 1,
        total_tokens_for_next_generation=0,
    )
    assert chat_history[0]["content"] == "You are a helpful assistant."
    assert chat_history[0]["role"] == "system"

    # Check truncation of 1 message in the chat history for system-user roles.
    chat_history = [
        {
            "content": "FooBar",
            "role": "system",
        },
        {
            "content": "What is the meaning of life?",
            "role": "user",
        },
    ]
    chat_history_tokens = token_counter(messages=chat_history, model=LITELLM_MODEL_CHAT)
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=chat_history_tokens,
        total_tokens_for_next_generation=4,
    )
    assert len(chat_history) == 1 and chat_history[0]["content"] == "FooBar"

    # Check truncation of 1 message in the chat history for user-user roles.
    chat_history = [
        {
            "content": "FooBar",
            "role": "user",
        },
        {
            "content": "What is the meaning of life?",
            "role": "user",
        },
    ]
    chat_history_tokens = token_counter(messages=chat_history, model=LITELLM_MODEL_CHAT)
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=chat_history_tokens,
        total_tokens_for_next_generation=4,
    )
    assert (
        len(chat_history) == 1
        and chat_history[0]["content"] == "What is the meaning of life?"
    )


def test__truncate_chat_history_can_empty_history(mock_logger: MagicMock) -> None:
    """A lone non-system message is dropped (with a warning) when it alone fills
    the context window.

    Parameters
    ----------
    mock_logger
        The mock service logger.
    """

    chat_history: list[dict[str, str | None]] = [{"content": "Hi", "role": "user"}]
    tokens = token_counter(messages=chat_history, model=LITELLM_MODEL_CHAT)

    # Exactly zero tokens left triggers truncation; dropping the message frees them.
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=tokens + 5,
        total_tokens_for_next_generation=5,
    )

    assert chat_history == []
    mock_logger.warning.assert_called_with(
        "Empty chat history after truncating chat messages!"
    )


def test_append_message_content_to_chat_history() -> None:
    """Test appending messages to chat histories."""

    # Should have expected message appended to chat history without any truncation even
    # with truncate_history set to True.
    chat_history: list[dict[str, str | None]] = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    append_message_content_to_chat_history(
        chat_history=chat_history,
        message_content="What is the meaning of life?",
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        name="123",
        role="user",
        total_tokens_for_next_generation=50,
        truncate_history=True,
    )
    assert (
        len(chat_history) == 2
        and chat_history[1]["role"] == "user"
        and chat_history[1]["content"] == "What is the meaning of life?"
        and chat_history[1]["name"] == "123"
    )

    # Should have expected message appended to chat history without any truncation even
    # if the total tokens for next generation exceeds the model context length.
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    append_message_content_to_chat_history(
        chat_history=chat_history,
        message_content="What is the meaning of life?",
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        name="123",
        role="user",
        total_tokens_for_next_generation=150,
        truncate_history=False,
    )
    assert (
        len(chat_history) == 2
        and chat_history[1]["role"] == "user"
        and chat_history[1]["content"] == "What is the meaning of life?"
    )

    # Check that empty message content with assistant role is correctly appended.
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    append_message_content_to_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        name="123",
        role="assistant",
        total_tokens_for_next_generation=150,
        truncate_history=False,
    )
    assert (
        len(chat_history) == 2
        and chat_history[1]["role"] == "assistant"
        and chat_history[1]["content"] is None
    )

    # This should fail because message content is not provided and the role is not
    # "assistant" or "function".
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    with pytest.raises(AssertionError):
        append_message_content_to_chat_history(
            chat_history=chat_history,
            model=LITELLM_MODEL_CHAT,
            model_context_length=100,
            name="123",
            role="user",
            total_tokens_for_next_generation=150,
            truncate_history=False,
        )


@pytest.mark.parametrize("as_list", [True, False])
def test_append_messages_to_chat_history(as_list: bool) -> None:
    """One message or a list of messages is appended in order.

    Parameters
    ----------
    as_list
        Whether to pass the message wrapped in a list.
    """

    chat_history: list[dict[str, str | None]] = [
        {"content": "You are a helpful assistant.", "name": "1", "role": "system"}
    ]
    message: dict[str, str | None] = {"content": "Hello", "name": "1", "role": "user"}

    service.append_messages_to_chat_history(
        chat_history=chat_history,
        messages=[message] if as_list else message,
        model=LITELLM_MODEL_CHAT,
        model_context_length=1000,
        total_tokens_for_next_generation=50,
    )

    assert chat_history[-1] == message
    assert len(chat_history) == 2


@pytest.mark.parametrize(
    "message_params, expected_prompt",
    [
        ("Hello there", "Hello there"),
        ({"prompt": "Hello {name}", "prompt_kws": {"name": "Bob"}}, "Hello Bob"),
    ],
)
async def test_get_chat_response(
    message_params: str | dict[str, Any],
    expected_prompt: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The formatted prompt and the LLM reply are both appended to the history.

    Parameters
    ----------
    message_params
        A plain prompt or a prompt with format keywords.
    expected_prompt
        The prompt after formatting.
    monkeypatch
        Pytest monkeypatch.
    """

    mock_ask_llm = AsyncMock(return_value="General Kenobi")
    monkeypatch.setattr(service, "ask_llm_async", mock_ask_llm)
    # NB: an empty list is falsy, so the service would swap it for a new list.
    chat_history: list[dict[str, str | None]] = [
        {"content": "sys", "name": "1", "role": "system"}
    ]

    reply = await service.get_chat_response(
        chat_history=chat_history,
        chat_params=CHAT_PARAMS,
        message_params=message_params,
        session_id="1",
        json_=True,
    )

    assert reply == "General Kenobi"
    assert [(m["role"], m["content"]) for m in chat_history] == [
        ("system", "sys"),
        ("user", expected_prompt),
        ("assistant", "General Kenobi"),
    ]
    # Extra keyword arguments are forwarded to the LLM call.
    assert mock_ask_llm.call_args.kwargs["json_"] is True
    assert mock_ask_llm.call_args.kwargs["messages"] is chat_history


def _model_info_response(*entries: dict[str, Any]) -> MagicMock:
    """Build a fake `requests` response for the LiteLLM `/model/info` endpoint.

    Parameters
    ----------
    entries
        The model entries.

    Returns
    -------
    MagicMock
        The fake response.
    """

    response = MagicMock()
    # Deep copy: the service adds a "model" key to the chat entry it finds.
    response.json.return_value = {"data": copy.deepcopy(list(entries))}
    return response


CHAT_MODEL_INFO = {
    "litellm_params": {"model": "test-model"},
    "model_info": {"max_input_tokens": 1000, "max_output_tokens": 200},
    "model_name": "chat",
}


async def test_init_chat_history(fake_redis: FakeRedis) -> None:
    """Test chat history initialization.

    Parameters
    ----------
    fake_redis
        The in-memory Redis client.
    """

    # A non-chat model listed first must be skipped.
    mock_response = _model_info_response(
        {"model_name": "embeddings", "model_info": {}, "litellm_params": {}},
        CHAT_MODEL_INFO,
    )

    with patch("app.question_answer.service.requests.get", return_value=mock_response):
        # Call the function under test
        session_id = "12345"
        (
            chat_cache_key,
            chat_params_cache_key,
            chat_history,
            old_chat_params,
        ) = await init_chat_history(
            redis_client=fake_redis,  # type: ignore[arg-type]
            reset=False,
            session_id=session_id,
        )

        # Check that attributes are generated correctly and that the chat history is
        # initialized with the system message.
        assert chat_cache_key == f"chatCache:{session_id}"
        assert chat_params_cache_key == f"chatParamsCache:{session_id}"
        assert chat_history == [
            {
                "content": "You are a helpful assistant.",
                "name": session_id,
                "role": "system",
            }
        ]
        assert isinstance(old_chat_params, dict)
        assert all(
            x in old_chat_params
            for x in ["max_input_tokens", "max_output_tokens", "model"]
        )

        # Check that initialization with reset=False does not clear existing chat
        # history.
        altered_chat_history = chat_history + [
            {
                "content": "What is the meaning of life?",
                "name": session_id,
                "role": "user",
            }
        ]
        await fake_redis.set(chat_cache_key, json.dumps(altered_chat_history))
        _, _, new_chat_history, _ = await init_chat_history(
            redis_client=fake_redis,  # type: ignore[arg-type]
            reset=False,
            session_id=session_id,
        )
        assert new_chat_history == [
            {
                "content": "You are a helpful assistant.",
                "name": session_id,
                "role": "system",
            },
            {
                "content": "What is the meaning of life?",
                "name": session_id,
                "role": "user",
            },
        ]

    # Check that initialization with reset=True clears existing chat history.
    mock_response = _model_info_response(CHAT_MODEL_INFO)
    with patch("app.question_answer.service.requests.get", return_value=mock_response):
        _, _, reset_chat_history, _ = await init_chat_history(
            redis_client=fake_redis,  # type: ignore[arg-type]
            reset=True,
            session_id=session_id,
        )
        assert reset_chat_history == [
            {
                "content": "You are a helpful assistant.",
                "name": session_id,
                "role": "system",
            }
        ]


async def test_init_chat_history_falls_back_to_cached_params(
    fake_redis: FakeRedis,
) -> None:
    """If `/model/info` has no chat model, previously cached chat params are used.

    Parameters
    ----------
    fake_redis
        The in-memory Redis client.
    """

    cached_params = {"max_input_tokens": 500, "max_output_tokens": 50, "model": "m"}
    await fake_redis.set("chatParamsCache:7", json.dumps(cached_params))
    mock_response = _model_info_response(
        {"model_name": "embeddings", "model_info": {}, "litellm_params": {}}
    )

    with patch("app.question_answer.service.requests.get", return_value=mock_response):
        _, _, chat_history, chat_params = await init_chat_history(
            redis_client=fake_redis,  # type: ignore[arg-type]
            reset=True,
            session_id="7",
            system_message="Be brief.",
        )

    assert chat_params == cached_params
    assert chat_history == [{"content": "Be brief.", "name": "7", "role": "system"}]


@pytest.mark.parametrize("context", [None, "after search"])
def test_log_chat_history(context: str | None, mock_logger: MagicMock) -> None:
    """Every message is logged, with function calls shown for assistant turns.

    Parameters
    ----------
    context
        Optional label for the log block.
    mock_logger
        The mock service logger.
    """

    chat_history: list[dict[str, Any]] = [
        {"content": "sys", "role": "system"},
        {"content": "question", "role": "user"},
        {"content": None, "function_call": "lookup()", "role": "assistant"},
        {"content": "42", "name": "lookup", "role": "function"},
    ]

    service.log_chat_history(chat_history=chat_history, context=context)

    logged = [c.args[0] for c in mock_logger.info.call_args_list]
    assert logged[0] == (
        f"\n###Chat history: {context}###" if context else "\n###Chat history###"
    )
    assert logged[1:] == [
        "\nsystem:\nsys\n",
        "\nuser:\nquestion\n",
        "\nassistant:\nlookup()\n",
        "\nfunction:\n(lookup): 42\n",
    ]


@pytest.mark.parametrize(
    "chat_cache_key, expected_key", [(None, "chatCache:9"), ("custom", "custom")]
)
async def test_reset_chat_history(
    chat_cache_key: str | None, expected_key: str, fake_redis: FakeRedis
) -> None:
    """The chat history key (default or custom) is deleted.

    Parameters
    ----------
    chat_cache_key
        The key passed in, or `None` for the default.
    expected_key
        The key that should be deleted.
    fake_redis
        The in-memory Redis client.
    """

    await fake_redis.set(expected_key, "[]")
    await fake_redis.set("other", "[]")

    await service.reset_chat_history(
        chat_cache_key=chat_cache_key,
        redis_client=fake_redis,  # type: ignore[arg-type]
        session_id="9",
    )

    assert list(fake_redis.store) == ["other"]


def test_chat_history_parse_json_valid() -> None:
    """Valid search-query JSON (even wrapped in markdown) is parsed."""

    parsed = ChatHistory.parse_json(
        chat_type="search",
        json_str='```json{"message_type": "FOLLOW-UP", "query": "q"}```',
    )

    assert parsed == {"message_type": "FOLLOW-UP", "query": "q"}


@pytest.mark.parametrize(
    "chat_type, json_str, error, match",
    [
        ("search", '{"message_type": "OTHER", "query": "q"}', ValueError, "validating"),
        ("other", "{}", NotImplementedError, "not implemented"),
    ],
)
def test_chat_history_parse_json_errors(
    chat_type: str, json_str: str, error: type[Exception], match: str
) -> None:
    """Invalid output and unknown chat types are rejected.

    Parameters
    ----------
    chat_type
        The chat type.
    json_str
        The LLM output.
    error
        The expected exception type.
    match
        A fragment of the expected error message.
    """

    with pytest.raises(error, match=match):
        ChatHistory.parse_json(chat_type=chat_type, json_str=json_str)  # type: ignore[arg-type]


def test_safety_classification_defaults_to_safe() -> None:
    """Unknown values passed to the enum constructor fall back to SAFE."""

    assert SafetyClassification("something else") is SafetyClassification.SAFE


# =====================================================================================
# RAG
# =====================================================================================


@pytest.mark.parametrize(
    "llm_output, expected",
    [
        (
            '```json{"answer": "Drink water.", "extracted_info": ["water"]}```',
            RAG(answer="Drink water.", extracted_info=["water"]),
        ),
        ("not json", RAG(answer="not json", extracted_info=[])),
    ],
)
async def test_get_llm_rag_answer(
    llm_output: str, expected: RAG, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The JSON answer is parsed; anything else becomes the answer text.

    Parameters
    ----------
    llm_output
        The raw LLM output.
    expected
        The expected RAG object.
    monkeypatch
        Pytest monkeypatch.
    """

    mock_ask_llm = AsyncMock(return_value=llm_output)
    monkeypatch.setattr(service, "ask_llm_async", mock_ask_llm)

    result = await get_llm_rag_answer(
        context="1. Water\nDrink water.",
        original_language=IdentifiedLanguage.ENGLISH,
        question="How do I stay hydrated?",
    )

    assert result == expected
    kwargs = mock_ask_llm.call_args.kwargs
    assert kwargs["json_"] is True
    assert "Drink water." in kwargs["system_message"]
    assert kwargs["user_message"] == "How do I stay hydrated?"


@pytest.mark.parametrize(
    "llm_output, expected_answer",
    [
        ('{"answer": "Drink water.", "extracted_info": []}', "Drink water."),
        ("oops", "oops"),
    ],
)
@pytest.mark.parametrize("first_role", ["system", "user"])
async def test_get_llm_rag_answer_with_chat_history(
    llm_output: str,
    expected_answer: str,
    first_role: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A leading system prompt is replaced with the RAG prompt, and the stored user
    turn is the bare question (not the question plus context).

    Parameters
    ----------
    llm_output
        The raw LLM output.
    expected_answer
        The expected answer.
    first_role
        Role of the first message already in the history.
    monkeypatch
        Pytest monkeypatch.
    """

    monkeypatch.setattr(service, "ask_llm_async", AsyncMock(return_value=llm_output))
    first_message: dict[str, str | None] = {
        "content": "Earlier message",
        "name": "11",
        "role": first_role,
    }
    chat_history = [first_message.copy()]

    response, new_history = await service.get_llm_rag_answer_with_chat_history(
        chat_history=chat_history,
        chat_params=CHAT_PARAMS,
        context="1. Water\nDrink water.",
        message_type="FOLLOW-UP",
        original_language=IdentifiedLanguage.ENGLISH,
        question="How do I stay hydrated?",
        session_id="11",
    )

    assert response.answer == expected_answer
    if first_role == "system":
        assert "FOLLOW-UP" in str(new_history[0]["content"])
    else:
        # Without a system prompt there is nothing to replace.
        assert new_history[0] == first_message
    assert new_history[1:] == [
        {"content": "How do I stay hydrated?", "name": "11", "role": "user"},
        {"content": expected_answer, "name": "11", "role": "assistant"},
    ]


@pytest.mark.parametrize("as_model", [True, False])
def test_get_context_string_from_search_results(as_model: bool) -> None:
    """Search results (models or plain dicts from the cache) become a numbered
    context string.

    Parameters
    ----------
    as_model
        Whether the search results are `QuerySearchResult` objects or dicts.
    """

    results: dict[int, Any] = _search_results()
    if not as_model:
        results = {k: v.model_dump() for k, v in results.items()}

    context_string = get_context_string_from_search_results(search_results=results)

    assert context_string == "1. World\nhello world\n\n2. Universe\ngoodbye universe"


@pytest.mark.parametrize("missing", ["error", "search_results", "language"])
async def test_generate_llm_query_response_skips(
    missing: str,
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """Generation is skipped for guardrail failures or missing prerequisites.

    Parameters
    ----------
    missing
        Which prerequisite is missing.
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    mock_rag = AsyncMock()
    monkeypatch.setattr(service, "get_llm_rag_answer", mock_rag)
    response: QueryResponse = query_response
    if missing == "error":
        response = _error_response()
    elif missing == "search_results":
        response.search_results = None
    else:
        query_refined.original_language = None

    result, chat_history = await service.generate_llm_query_response(
        query_refined=query_refined, response=response
    )

    assert result is response
    assert chat_history == []
    mock_rag.assert_not_called()


@pytest.mark.parametrize(
    "answer, expect_error", [("Drink water.", False), (RAG_FAILURE_MESSAGE, True)]
)
async def test_generate_llm_query_response_single_turn(
    answer: str,
    expect_error: bool,
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """A normal answer is attached; the RAG failure marker becomes an error.

    Parameters
    ----------
    answer
        The answer returned by the RAG call.
    expect_error
        Whether an error response is expected.
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    query_response.llm_response = None
    mock_rag = AsyncMock(return_value=RAG(answer=answer, extracted_info=["fact"]))
    monkeypatch.setattr(service, "get_llm_rag_answer", mock_rag)

    result, _ = await service.generate_llm_query_response(
        query_refined=query_refined, response=query_response
    )

    assert result.debug_info["extracted_info"] == ["fact"]
    # The original (untranslated, unparaphrased) question is sent to the LLM.
    assert mock_rag.call_args.kwargs["question"] == query_refined.query_text_original
    if expect_error:
        assert isinstance(result, QueryResponseError)
        assert result.error_type == ErrorType.UNABLE_TO_GENERATE_RESPONSE
        assert result.llm_response is None
    else:
        assert not isinstance(result, QueryResponseError)
        assert result.llm_response == "Drink water."


async def test_generate_llm_query_response_with_chat_history(
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """With chat params, the chat-aware RAG call is used and its history returned.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    new_history = [{"content": "updated", "role": "system"}]
    mock_rag_chat = AsyncMock(
        return_value=(RAG(answer="Yes.", extracted_info=[]), new_history)
    )
    monkeypatch.setattr(service, "get_llm_rag_answer_with_chat_history", mock_rag_chat)
    query_refined.chat_query_params = {
        "chat_history": [{"content": "old", "role": "system"}],
        "chat_params": CHAT_PARAMS,
        "message_type": "FOLLOW-UP",
        "session_id": str(SESSION_ID),
    }

    result, chat_history = await service.generate_llm_query_response(
        query_refined=query_refined, response=query_response
    )

    assert chat_history == new_history
    assert result.llm_response == "Yes."
    assert result.message_type == "FOLLOW-UP"
    assert mock_rag_chat.call_args.kwargs["session_id"] == str(SESSION_ID)


# =====================================================================================
# Speech helpers
# =====================================================================================


@pytest.mark.parametrize(
    "whisper_language, expected", [("hi", "hi-IN"), ("fr", "en-US")]
)
def test_detect_language(
    whisper_language: str, expected: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whisper's language is mapped to a Google STT code, defaulting to en-US.

    Parameters
    ----------
    whisper_language
        The language reported by Whisper.
    expected
        The expected Google language code.
    monkeypatch
        Pytest monkeypatch.
    """

    model = MagicMock()
    model.transcribe.return_value = ([], SimpleNamespace(language=whisper_language))
    monkeypatch.setattr(service, "WhisperModel", MagicMock(return_value=model))

    assert service.detect_language(file_path="voice.wav") == expected
    model.transcribe.assert_called_once_with("voice.wav")


def test_get_gtts_lang_code_and_model() -> None:
    """Supported languages map to a code and voice; others raise."""

    assert service.get_gtts_lang_code_and_model(
        identified_language=IdentifiedLanguage.ENGLISH
    ) == ("en-US", "Neural2-D")
    with pytest.raises(ValueError, match="Unsupported language"):
        service.get_gtts_lang_code_and_model(
            identified_language=IdentifiedLanguage.SWAHILI
        )


@pytest.mark.parametrize(
    "input_filename, converted_to", [("voice.mp3", "voice.wav"), ("voice.WAV", None)]
)
def test_convert_audio_to_wav(
    input_filename: str, converted_to: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-WAV files are converted first; every file then gets the WAV specs.

    Parameters
    ----------
    input_filename
        The audio file name.
    converted_to
        The expected WAV file name after conversion, or `None` if no conversion.
    monkeypatch
        Pytest monkeypatch.
    """

    audio_segment = MagicMock()
    set_specs = MagicMock(return_value="final.wav")
    monkeypatch.setattr(service, "AudioSegment", audio_segment)
    monkeypatch.setattr(service, "set_wav_specifications", set_specs)

    assert service.convert_audio_to_wav(input_filename=input_filename) == "final.wav"

    if converted_to is None:
        audio_segment.from_file.assert_not_called()
        set_specs.assert_called_once_with(wav_filename=input_filename)
    else:
        audio_segment.from_file.assert_called_once_with(input_filename, format="mp3")
        audio_segment.from_file.return_value.export.assert_called_once_with(
            converted_to, format="wav"
        )
        set_specs.assert_called_once_with(wav_filename=converted_to)


def test_convert_audio_to_wav_rejects_unknown_format() -> None:
    """Unsupported extensions raise a `ValueError`."""

    with pytest.raises(ValueError, match="Unsupported file format: txt"):
        service.convert_audio_to_wav(input_filename="notes.txt")


def test_set_wav_specifications(monkeypatch: pytest.MonkeyPatch) -> None:
    """The WAV is resampled to 16 kHz mono LINEAR16 into a new file.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    """

    audio_segment = MagicMock()
    monkeypatch.setattr(service, "AudioSegment", audio_segment)

    assert (
        service.set_wav_specifications(wav_filename="voice.wav") == "voice_updated.wav"
    )

    audio = audio_segment.from_wav.return_value
    audio.set_frame_rate.assert_called_once_with(16000)
    audio.set_frame_rate.return_value.set_channels.assert_called_once_with(1)
    audio.set_frame_rate.return_value.set_channels.return_value.export.assert_called_once_with(
        "voice_updated.wav", format="wav", codec="pcm_s16le"
    )


def _use_http_response(
    monkeypatch: pytest.MonkeyPatch, response: FakeAiohttpResponse
) -> FakeAiohttpClient:
    """Make `get_http_client()` in the service return a fake client.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    response
        The canned response for every request.

    Returns
    -------
    FakeAiohttpClient
        The fake client (to inspect recorded calls).
    """

    client = FakeAiohttpClient(response)
    monkeypatch.setattr(service, "get_http_client", lambda: client)
    return client


async def test_post_to_internal_tts(monkeypatch: pytest.MonkeyPatch) -> None:
    """The audio bytes from the TTS service are returned as a stream.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    """

    client = _use_http_response(monkeypatch, FakeAiohttpResponse(body=b"audio"))

    result = await service.post_to_internal_tts(
        endpoint_url="http://tts", language=IdentifiedLanguage.ENGLISH, text="Hi"
    )

    assert result.read() == b"audio"
    assert client.calls == [
        ("POST", "http://tts", {"text": "Hi", "language": IdentifiedLanguage.ENGLISH})
    ]


async def test_post_to_internal_tts_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-200 from the TTS service raises a `ValueError`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    """

    _use_http_response(
        monkeypatch,
        FakeAiohttpResponse(json_data={"detail": "boom"}, status_code=500),
    )

    with pytest.raises(ValueError, match="CUSTOM_TTS_ENDPOINT"):
        await service.post_to_internal_tts(
            endpoint_url="http://tts", language=IdentifiedLanguage.ENGLISH, text="Hi"
        )


async def test_download_file_from_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """The file, its content type and its extension are returned.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    """

    client = _use_http_response(
        monkeypatch,
        FakeAiohttpResponse(body=b"voice", headers={"Content-Type": "audio/mpeg"}),
    )

    stream, content_type, extension = await service.download_file_from_url(
        file_url="http://files/voice"
    )

    assert stream.read() == b"voice"
    assert (content_type, extension) == ("audio/mpeg", ".mp3")
    assert client.calls == [("GET", "http://files/voice", None)]


@pytest.mark.parametrize(
    "response, match",
    [
        (FakeAiohttpResponse(status_code=404, text="missing"), "missing"),
        (FakeAiohttpResponse(body=b"voice"), "content type"),
    ],
)
async def test_download_file_from_url_errors(
    response: FakeAiohttpResponse, match: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failed downloads and missing content types raise a `ValueError`.

    Parameters
    ----------
    response
        The canned response.
    match
        A fragment of the expected error message.
    monkeypatch
        Pytest monkeypatch.
    """

    _use_http_response(monkeypatch, response)

    with pytest.raises(ValueError, match=f"Unable to fetch file: .*{match}"):
        await service.download_file_from_url(file_url="http://files/voice")


@pytest.mark.parametrize("status_code", [200, 500])
async def test_post_to_speech_stt(
    status_code: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The STT JSON is returned on success; errors raise a `ValueError`.

    Parameters
    ----------
    status_code
        The status returned by the STT service.
    monkeypatch
        Pytest monkeypatch.
    """

    client = _use_http_response(
        monkeypatch,
        FakeAiohttpResponse(json_data={"text": "hello"}, status_code=status_code),
    )

    if status_code == 200:
        result = await service.post_to_speech_stt(
            file_path="temp/a.wav", endpoint_url="http://stt"
        )
        assert result == {"text": "hello"}
        assert client.calls == [("POST", "http://stt", {"stt_file_path": "temp/a.wav"})]
    else:
        with pytest.raises(ValueError, match="CUSTOM_STT_ENDPOINT"):
            await service.post_to_speech_stt(
                file_path="temp/a.wav", endpoint_url="http://stt"
            )


async def test_transcribe_audio(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The converted WAV is sent to Google STT and the transcripts are joined.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    tmp_path
        Pytest temporary directory.
    """

    wav_file = tmp_path / "voice_updated.wav"
    wav_file.write_bytes(b"wav-bytes")
    monkeypatch.setattr(service, "detect_language", MagicMock(return_value="hi-IN"))
    monkeypatch.setattr(
        service, "convert_audio_to_wav", MagicMock(return_value=str(wav_file))
    )
    speech_client = MagicMock()
    speech_client.recognize.return_value = SimpleNamespace(
        results=[
            SimpleNamespace(alternatives=[SimpleNamespace(transcript="Hello ")]),
            SimpleNamespace(alternatives=[SimpleNamespace(transcript="world")]),
        ]
    )
    monkeypatch.setattr(
        service.speech, "SpeechClient", MagicMock(return_value=speech_client)
    )

    transcript = await service.transcribe_audio(audio_filename="voice.mp3")

    assert transcript == "Hello world"
    kwargs = speech_client.recognize.call_args.kwargs
    assert kwargs["audio"].content == b"wav-bytes"
    assert kwargs["config"].language_code == "hi-IN"


async def test_transcribe_audio_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any failure is reported as a `ValueError`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    """

    monkeypatch.setattr(
        service, "detect_language", MagicMock(side_effect=RuntimeError("no model"))
    )

    with pytest.raises(ValueError, match="Failed to transcribe voice.mp3: no model"):
        await service.transcribe_audio(audio_filename="voice.mp3")


@pytest.mark.parametrize(
    "language, expect_error",
    [(IdentifiedLanguage.ENGLISH, False), (IdentifiedLanguage.SWAHILI, True)],
)
async def test_synthesize_speech(
    language: IdentifiedLanguage, expect_error: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Supported languages are synthesized with the mapped voice; others raise.

    Parameters
    ----------
    language
        The language to synthesize.
    expect_error
        Whether a `ValueError` is expected.
    monkeypatch
        Pytest monkeypatch.
    """

    tts_client = MagicMock()
    tts_client.synthesize_speech.return_value = SimpleNamespace(audio_content=b"wav")
    monkeypatch.setattr(
        service.texttospeech, "TextToSpeechClient", MagicMock(return_value=tts_client)
    )

    if expect_error:
        with pytest.raises(ValueError, match="Failed to generate speech"):
            await service.synthesize_speech(language=language, text="Hi")
        return

    result = await service.synthesize_speech(language=language, text="Hi")

    assert result.read() == b"wav"
    assert tts_client.synthesize_speech.call_args.kwargs["voice"].name == (
        "en-US-Neural2-D"
    )


# =====================================================================================
# Turn.io
# =====================================================================================


async def test_send_turn_text_message_success() -> None:
    """Test sending a text message via Turn.io API successfully."""

    expected_response = {"id": "msg_123", "status": "queued"}

    fake_response = FakeTurnResponse(
        data=expected_response, status_code=status.HTTP_200_OK
    )
    fake_client = RecordingAsyncClient(response=fake_response)

    text = "Hello from tests"
    api_key = "[TURNIO_API_KEY]"  # pragma: allowlist secret
    whatsapp_id = "whatsapp:+1234567890"

    result = await send_turn_text_message(
        httpx_client=fake_client,  # type: ignore[arg-type]
        text=text,
        turnio_api_key=api_key,
        whatsapp_id=whatsapp_id,
    )

    assert result == expected_response
    assert fake_client.last_url == urljoin(TURNIO_API_BASE, "messages")

    assert fake_client.last_json["to"] == whatsapp_id
    assert fake_client.last_json["type"] == "text"
    assert fake_client.last_json["text"]["body"] == text

    assert fake_client.last_json["recipient_type"] == "individual"
    assert fake_client.last_json["preview_url"] is False

    assert fake_client.last_headers["Authorization"] == f"Bearer {api_key}"


async def test_send_turn_text_message_raises_on_http_error() -> None:
    """Test that sending a text message raises an error on HTTP failure."""

    # Arrange response so that it will raise HTTPStatusError.
    error_response = FakeTurnResponse(
        data={"error": "Bad Request"}, status_code=status.HTTP_400_BAD_REQUEST
    )
    fake_client = RecordingAsyncClient(response=error_response)

    with pytest.raises(httpx.HTTPStatusError):
        await send_turn_text_message(
            httpx_client=fake_client,  # type: ignore[arg-type]
            text="This will fail",
            turnio_api_key="[TURNIO_API_KEY]",  # pragma: allowlist secret
            whatsapp_id="whatsapp:+0000000000",
        )


@pytest.mark.parametrize("session_id, expected", [(None, 424242), (7, 7)])
def test_assign_chat_session_id(
    session_id: int | None, expected: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A random session ID is assigned only when the query has none.

    Parameters
    ----------
    session_id
        The incoming session ID.
    expected
        The session ID after assignment.
    monkeypatch
        Pytest monkeypatch.
    """

    monkeypatch.setattr(service, "get_random_int32", lambda: 424242)
    user_query = QueryBase(
        generate_llm_response=True, query_text="hello", session_id=session_id
    )

    service.assign_chat_session_id(user_query=user_query)

    assert user_query.session_id == expected


@pytest.mark.parametrize(
    "turnio_api_key, wa_id, expected",
    [
        ("[TURNIO_API_KEY]", "whatsapp:+1", True),
        ("[TURNIO_API_KEY]", None, False),
        (None, "whatsapp:+1", False),
    ],
)
def test_is_turnio_chat(
    turnio_api_key: str | None, wa_id: str | None, expected: bool
) -> None:
    """Only queries with both a Turn.io key and a WhatsApp ID are Turn.io chats.

    Parameters
    ----------
    turnio_api_key
        The Turn.io API key.
    wa_id
        The WhatsApp ID.
    expected
        Whether the query is a Turn.io chat.
    """

    user_query = QueryBase(
        generate_llm_response=True,
        query_text="hi",
        turnio_api_key=turnio_api_key,
        wa_id=wa_id,
    )

    assert service.is_turnio_chat(user_query=user_query) is expected


def test_build_turnio_ack_response() -> None:
    """The acknowledgement carries the session ID and nothing else."""

    ack = service.build_turnio_ack_response(session_id=424242)

    assert ack.llm_response == TURNIO_ACK_MESSAGE
    assert ack.session_id == 424242
    assert (ack.feedback_secret_key, ack.query_id, ack.search_results) == (
        None,
        None,
        None,
    )


@pytest.mark.parametrize(
    "response, expected",
    [
        (
            QueryResponse(
                feedback_secret_key=None,
                llm_response="answer",
                query_id=None,
                search_results=None,
                session_id=None,
            ),
            "answer",
        ),
        (_error_response(), "Guardrail failure: bad query"),
        (None, INTERNAL_SERVER_ERROR_MESSAGE),
    ],
)
def test_get_turnio_reply_text(response: Any, expected: str) -> None:
    """The reply is the answer, the guardrail message, or a generic error.

    Parameters
    ----------
    response
        The pipeline result.
    expected
        The expected reply text.
    """

    assert service._get_turnio_reply_text(response=response) == expected


# =====================================================================================
# Input guardrails
# =====================================================================================


class TestErrorResponses:
    """Tests for the input guardrails (language, translation, safety)."""

    SUPPORTED_LANGUAGE = IdentifiedLanguage.get_supported_languages()[-1]

    @pytest.fixture
    def user_query_response(self) -> QueryResponse:
        """Create a query response.

        Returns
        -------
        QueryResponse
            The query response object.
        """

        return QueryResponse(
            debug_info={},
            feedback_secret_key="abc123",
            llm_response=None,
            query_id=124,
            search_results={},
            session_id=None,
        )

    @pytest.fixture
    def user_query_refined(self, request: pytest.FixtureRequest) -> QueryRefined:
        """Create a query refined object.

        Parameters
        ----------
        request
            Pytest request object.

        Returns
        -------
        QueryRefined
            The query refined object.
        """

        language = request.param if hasattr(request, "param") else None
        return QueryRefined(
            generate_llm_response=False,
            generate_tts=False,
            original_language=language,
            query_text="This is a basic query",
            query_text_original="This is a query original",
            workspace_doc_language="ENGLISH",
            workspace_id=124,
        )

    @pytest.mark.parametrize(
        "identified_lang_str,should_error,expected_error_type",
        [
            ("ENGLISH", False, None),
            ("HINDI", False, None),
            ("UNINTELLIGIBLE", True, ErrorType.UNINTELLIGIBLE_INPUT),
            ("GIBBERISH", True, ErrorType.UNSUPPORTED_LANGUAGE),
            ("UNSUPPORTED", True, ErrorType.UNSUPPORTED_LANGUAGE),
            ("SOME_UNSUPPORTED_LANG", True, ErrorType.UNSUPPORTED_LANGUAGE),
            ("don't kow", True, ErrorType.UNSUPPORTED_LANGUAGE),
        ],
    )
    async def test_language_identify_error(
        self,
        identified_lang_str: str,
        should_error: bool,
        expected_error_type: ErrorType,
        monkeypatch: pytest.MonkeyPatch,
        user_query_response: QueryResponse,
    ) -> None:
        """Test language identification errors.

        Parameters
        ----------
        identified_lang_str
            Identified language string.
        should_error
            Specifies whether an error is expected.
        expected_error_type
            Expected error type.
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response.
        """

        user_query_refined = QueryRefined(
            generate_llm_response=False,
            generate_tts=False,
            original_language=None,
            query_text="This is a basic query",
            query_text_original="This is a query original",
            workspace_doc_language="ENGLISH",
            workspace_id=124,
        )

        monkeypatch.setattr(
            service, "ask_llm_async", AsyncMock(return_value=identified_lang_str)
        )

        query, response = await _identify_language(
            query_refined=user_query_refined, response=user_query_response
        )

        if should_error:
            assert isinstance(response, QueryResponseError)
            assert response.error_type == expected_error_type
        else:
            assert isinstance(response, QueryResponse)
            assert query.original_language == getattr(
                IdentifiedLanguage, identified_lang_str
            )

    @pytest.mark.parametrize(
        "user_query_refined,workspace_doc_language, should_error,expected_error_type",
        [
            ("ENGLISH", "ENGLISH", False, None),
            ("ENGLISH", SUPPORTED_LANGUAGE, False, None),
        ],
        indirect=["user_query_refined"],
    )
    async def test_translate_error(
        self,
        user_query_refined: QueryRefined,
        workspace_doc_language: str,
        should_error: bool,
        expected_error_type: ErrorType,
        monkeypatch: pytest.MonkeyPatch,
        user_query_response: QueryResponse,
    ) -> None:
        """Test translation errors.

        Parameters
        ----------
        user_query_refined
            The user query refined object.
        workspace_doc_language
            The workspace document language.
        should_error
            Specifies whether an error is expected.
        expected_error_type
            Expected error type.
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response object.
        """

        monkeypatch.setattr(
            service,
            "ask_llm_async",
            AsyncMock(return_value="This is a translated LLM response"),
        )
        user_query_refined.workspace_doc_language = workspace_doc_language
        query, response = await _translate_question(
            query_refined=user_query_refined, response=user_query_response
        )

        if should_error:
            assert isinstance(response, QueryResponseError)
            assert response.error_type == expected_error_type
        else:
            assert isinstance(response, QueryResponse)
            if (
                query.original_language == "ENGLISH"
                and workspace_doc_language == "ENGLISH"
            ):
                assert query.query_text == "This is a basic query"
            else:
                assert query.query_text == "This is a translated LLM response"

    @pytest.mark.parametrize("user_query_refined", ["HINDI"], indirect=True)
    async def test_translate_failure(
        self,
        user_query_refined: QueryRefined,
        monkeypatch: pytest.MonkeyPatch,
        user_query_response: QueryResponse,
    ) -> None:
        """The translation bot's failure marker becomes an error response.

        Parameters
        ----------
        user_query_refined
            The user query refined object.
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response object.
        """

        monkeypatch.setattr(
            service, "ask_llm_async", AsyncMock(return_value=TRANSLATE_FAILED_MESSAGE)
        )

        query, response = await _translate_question(
            query_refined=user_query_refined, response=user_query_response
        )

        assert isinstance(response, QueryResponseError)
        assert response.error_type == ErrorType.UNABLE_TO_TRANSLATE
        assert query.query_text == "This is a basic query"

    async def test_translate_before_language_id_errors(
        self, monkeypatch: pytest.MonkeyPatch, user_query_response: QueryResponse
    ) -> None:
        """Test translation before language identification errors.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response object.
        """

        monkeypatch.setattr(
            service,
            "ask_llm_async",
            AsyncMock(return_value="This is a translated LLM response"),
        )

        user_query_refined = QueryRefined(
            generate_llm_response=False,
            generate_tts=False,
            original_language=None,
            query_text="This is a basic query",
            query_text_original="This is a query original",
            workspace_doc_language="ENGLISH",
            workspace_id=124,
        )

        with pytest.raises(ValueError):
            _, _ = await _translate_question(
                query_refined=user_query_refined, response=user_query_response
            )

    @pytest.mark.parametrize(
        "classification, should_error",
        [("SAFE", False), ("INAPPROPRIATE_LANGUAGE", True), ("PROMPT_INJECTION", True)],
    )
    async def test_unsafe_query_error(
        self,
        classification: str,
        should_error: bool,
        monkeypatch: pytest.MonkeyPatch,
        user_query_refined: QueryRefined,
        user_query_response: QueryResponse,
    ) -> None:
        """Test unsafe query errors.

        Parameters
        ----------
        classification
            The classification of the query.
        should_error
            Specifies whether an error is expected.
        monkeypatch
            Pytest monkeypatch.
        user_query_refined
            The user query refined object.
        user_query_response
            The user query response object.
        """

        async def mock_ask_llm(llm_response: str, *args: Any, **kwargs: Any) -> str:
            """Mock the LLM response.

            Parameters
            ----------
            llm_response
                The LLM response.
            args
                Additional positional arguments.
            kwargs
                Additional keyword arguments.

            Returns
            -------
            str
                The mocked LLM response.
            """

            return llm_response

        monkeypatch.setattr(
            "app.question_answer.service.ask_llm_async",
            partial(mock_ask_llm, classification),
        )
        query, response = await _classify_safety(
            query_refined=user_query_refined, response=user_query_response
        )

        if should_error:
            assert isinstance(response, QueryResponseError)
            assert response.error_type == ErrorType.QUERY_UNSAFE
        else:
            assert isinstance(response, QueryResponse)
            assert query.query_text == "This is a basic query"


@pytest.mark.parametrize(
    "guardrail",
    [_identify_language, _translate_question, _classify_safety, _paraphrase_question],
)
async def test_input_guardrails_pass_errors_through(
    guardrail: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
) -> None:
    """A response that already failed a guardrail is returned untouched.

    Parameters
    ----------
    guardrail
        The guardrail function under test.
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    """

    mock_ask_llm = AsyncMock()
    monkeypatch.setattr(service, "ask_llm_async", mock_ask_llm)
    # Make translation actually needed so the error check is what short-circuits.
    query_refined.original_language = IdentifiedLanguage.HINDI
    error = _error_response()

    query, response = await guardrail(query_refined=query_refined, response=error)

    assert (query, response) == (query_refined, error)
    mock_ask_llm.assert_not_called()


@pytest.mark.parametrize(
    "llm_output, expect_error",
    [("How can I stay hydrated?", False), (PARAPHRASE_FAILED_MESSAGE, True)],
)
async def test_paraphrase_question(
    llm_output: str,
    expect_error: bool,
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """The paraphrase replaces the query text; the failure marker is an error.

    Parameters
    ----------
    llm_output
        The paraphrasing bot's output.
    expect_error
        Whether an error response is expected.
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    monkeypatch.setattr(service, "ask_llm_async", AsyncMock(return_value=llm_output))

    query, response = await _paraphrase_question(
        query_refined=query_refined, response=query_response
    )

    if expect_error:
        assert isinstance(response, QueryResponseError)
        assert response.error_type == ErrorType.UNABLE_TO_PARAPHRASE
        assert query.query_text == "How do I stay hydrated?"
    else:
        assert not isinstance(response, QueryResponseError)
        assert query.query_text == llm_output
        assert response.debug_info["paraphrased_question"] == llm_output


@pytest.mark.parametrize("has_chat_params", [True, False])
async def test_paraphrase_decorator_skipped_for_chat(
    has_chat_params: bool,
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """Chat queries are already rewritten by the chat LLM, so no paraphrasing.

    Parameters
    ----------
    has_chat_params
        Whether the query comes from the chat endpoint.
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    mock_paraphrase = AsyncMock(side_effect=_passthrough)
    monkeypatch.setattr(service, "_paraphrase_question", mock_paraphrase)
    if has_chat_params:
        query_refined.chat_query_params = {"session_id": "1"}

    @service.paraphrase_question__before
    async def wrapped(
        query_refined: QueryRefined, response: QueryResponse
    ) -> QueryResponse:
        """Return the response unchanged.

        Parameters
        ----------
        query_refined
            The refined query.
        response
            The response.

        Returns
        -------
        QueryResponse
            The response.
        """

        return response

    assert await wrapped(query_refined, query_response) is query_response
    assert mock_paraphrase.called is not has_chat_params


# =====================================================================================
# Output guardrails
# =====================================================================================


class TestAlignScore:
    """Tests for alignment score."""

    @pytest.fixture
    def user_query_response(self) -> QueryResponse:
        """Create a query response.

        Returns
        -------
        QueryResponse
            The query response object
        """

        return QueryResponse(
            debug_info={},
            feedback_secret_key="abc123",
            llm_response="This is a response",
            query_id=124,
            search_results=_search_results(),
            session_id=None,
        )

    async def test_score_less_than_threshold(
        self, monkeypatch: pytest.MonkeyPatch, user_query_response: QueryResponse
    ) -> None:
        """Test alignment score less than threshold.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response.
        """

        monkeypatch.setattr(
            service,
            "_get_llm_align_score",
            AsyncMock(
                return_value=AlignmentScore(reason="test - low score", score=0.2)
            ),
        )
        monkeypatch.setattr(service, "ALIGN_SCORE_THRESHOLD", 0.7)
        update_query_response = await _check_align_score(response=user_query_response)
        assert isinstance(update_query_response, QueryResponse)
        assert update_query_response.debug_info["factual_consistency"]["score"] == 0.2
        assert update_query_response.llm_response is None

    async def test_score_greater_than_threshold(
        self, monkeypatch: pytest.MonkeyPatch, user_query_response: QueryResponse
    ) -> None:
        """Test alignment score greater than threshold.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response.
        """

        monkeypatch.setattr(service, "ALIGN_SCORE_THRESHOLD", 0.7)
        monkeypatch.setattr(
            service,
            "_get_llm_align_score",
            AsyncMock(
                return_value=AlignmentScore(reason="test - high score", score=0.9)
            ),
        )
        update_query_response = await _check_align_score(response=user_query_response)
        assert isinstance(update_query_response, QueryResponse)
        assert update_query_response.debug_info["factual_consistency"]["score"] == 0.9

    @pytest.mark.parametrize("missing", ["error", "search_results", "llm_response"])
    async def test_check_skipped(
        self,
        missing: str,
        monkeypatch: pytest.MonkeyPatch,
        user_query_response: QueryResponse,
    ) -> None:
        """No score is computed for errors or when the claim/evidence is missing.

        Parameters
        ----------
        missing
            Which prerequisite is missing.
        monkeypatch
            Pytest monkeypatch.
        user_query_response
            The user query response.
        """

        mock_score = AsyncMock()
        monkeypatch.setattr(service, "_get_llm_align_score", mock_score)
        response: QueryResponse = user_query_response
        if missing == "error":
            response = _error_response()
        else:
            setattr(response, missing, None)

        assert await _check_align_score(response=response) is response
        mock_score.assert_not_called()


@pytest.mark.parametrize(
    "llm_output, expected",
    [
        (
            '```json{"score": 0.8, "reason": "ok"}```',
            AlignmentScore(reason="ok", score=0.8),
        ),
        ('{"score": "high"}', None),
    ],
)
async def test_get_llm_align_score(
    llm_output: str, expected: AlignmentScore | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valid JSON is parsed; anything else raises a `RuntimeError`.

    Parameters
    ----------
    llm_output
        The raw LLM output.
    expected
        The expected score, or `None` if an error is expected.
    monkeypatch
        Pytest monkeypatch.
    """

    mock_ask_llm = AsyncMock(return_value=llm_output)
    monkeypatch.setattr(service, "ask_llm_async", mock_ask_llm)
    data = service.AlignScoreData(claim="Drink water.", evidence="1. W\nwater")

    if expected is None:
        with pytest.raises(RuntimeError, match="not valid json"):
            await _get_llm_align_score(align_score_data=data)
        return

    assert await _get_llm_align_score(align_score_data=data) == expected
    assert mock_ask_llm.call_args.kwargs["user_message"] == "Drink water."
    assert "1. W\nwater" in mock_ask_llm.call_args.kwargs["system_message"]


@pytest.mark.parametrize("custom_endpoint", [None, "http://tts"])
async def test_generate_tts_response(
    custom_endpoint: str | None,
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
) -> None:
    """Speech comes from the custom TTS endpoint if set, else Google TTS; it is
    uploaded and its public URL attached.

    Parameters
    ----------
    custom_endpoint
        The configured custom TTS endpoint.
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    """

    internal_tts = AsyncMock(return_value=BytesIO(b"a"))
    google_tts = AsyncMock(return_value=BytesIO(b"b"))
    upload = AsyncMock()
    monkeypatch.setattr(service, "CUSTOM_TTS_ENDPOINT", custom_endpoint)
    monkeypatch.setattr(service, "post_to_internal_tts", internal_tts)
    monkeypatch.setattr(service, "synthesize_speech", google_tts)
    monkeypatch.setattr(service, "upload_file_to_gcs", upload)
    monkeypatch.setattr(
        service, "generate_public_url", AsyncMock(return_value="https://gcs/tts.wav")
    )
    response = QueryAudioResponse(
        feedback_secret_key="k",
        llm_response="Hi",
        query_id=1,
        search_results=None,
        session_id=None,
        tts_filepath=None,
    )

    result = await service._generate_tts_response(
        query_refined=query_refined, response=response
    )

    assert isinstance(result, QueryAudioResponse)
    assert result.tts_filepath == "https://gcs/tts.wav"
    assert internal_tts.called is (custom_endpoint is not None)
    assert google_tts.called is (custom_endpoint is None)
    assert upload.call_args.kwargs["content_type"] == "audio/wav"
    assert upload.call_args.kwargs["destination_blob_name"].startswith(
        "tts-voice-notes/"
    )


async def test_generate_tts_response_without_llm_response(
    query_refined: QueryRefined,
) -> None:
    """Nothing to speak means the response is returned unchanged.

    Parameters
    ----------
    query_refined
        The refined query.
    """

    response = QueryAudioResponse(
        feedback_secret_key="k",
        llm_response=None,
        query_id=1,
        search_results=None,
        session_id=None,
        tts_filepath=None,
    )

    assert (
        await service._generate_tts_response(
            query_refined=query_refined, response=response
        )
        is response
    )


async def test_generate_tts_response_without_language(
    query_refined: QueryRefined,
) -> None:
    """A missing language becomes a TTS error response.

    Parameters
    ----------
    query_refined
        The refined query.
    """

    query_refined.original_language = None
    response = QueryAudioResponse(
        feedback_secret_key="k",
        llm_response="Hi",
        query_id=1,
        search_results=None,
        session_id=None,
        tts_filepath=None,
    )

    result = await service._generate_tts_response(
        query_refined=query_refined, response=response
    )

    assert isinstance(result, QueryResponseError)
    assert result.error_type == ErrorType.TTS_ERROR
    assert result.llm_response == "Hi"


@pytest.mark.parametrize("returned_kind", ["response", "audio", "error"])
async def test_generate_tts_decorator(
    returned_kind: str,
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """Plain responses are upgraded to audio responses; errors skip TTS.

    Parameters
    ----------
    returned_kind
        The kind of response returned by the wrapped function.
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    mock_tts = AsyncMock(side_effect=lambda **kwargs: kwargs["response"])
    monkeypatch.setattr(service, "_generate_tts_response", mock_tts)
    query_refined.generate_tts = True
    returned: QueryResponse = {
        "response": query_response,
        "audio": QueryAudioResponse(**query_response.model_dump()),
        "error": _error_response(),
    }[returned_kind]

    @service.generate_tts__after
    async def wrapped(
        query_refined: QueryRefined, response: QueryResponse
    ) -> QueryResponse:
        """Return the prepared response.

        Parameters
        ----------
        query_refined
            The refined query.
        response
            The response (ignored).

        Returns
        -------
        QueryResponse
            The prepared response.
        """

        return returned

    result = await wrapped(query_refined, query_response)

    if returned_kind == "error":
        assert result is returned
        mock_tts.assert_not_called()
    else:
        assert isinstance(result, QueryAudioResponse)
        assert result.llm_response == "Drink water."
        mock_tts.assert_called_once()
    if returned_kind == "audio":
        # `QueryAudioResponse` subclasses `QueryResponse`, so even an audio response
        # is rebuilt (with `tts_filepath` reset) before TTS runs.
        assert result is not returned
        assert result.tts_filepath is None


# =====================================================================================
# Query pipeline
# =====================================================================================


def test_rerank_search_results() -> None:
    """Results are ordered by cross-encoder score and cut to `n_similar`."""

    results = {
        0: QuerySearchResult(distance=0.1, id=10, text="a", title="A"),
        1: QuerySearchResult(distance=0.2, id=11, text="b", title="B"),
        2: QuerySearchResult(distance=0.3, id=12, text="c", title="C"),
    }
    crossencoder = FakeCrossEncoder(scores=[0.1, 0.9, 0.5])

    reranked = service.rerank_search_results(
        crossencoder=crossencoder,
        n_similar=2,
        query_text="q",
        search_results=results,
    )

    assert [r.id for r in reranked.values()] == [11, 12]
    assert list(reranked) == [0, 1]
    assert crossencoder.pairs[0] == ("q", "A\na")


@pytest.mark.usefixtures("bypass_input_guardrails")
async def test_get_search_response_reranks(
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """With the cross-encoder on, more candidates are fetched and then reranked.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    candidates = {
        0: QuerySearchResult(distance=0.1, id=10, text="a", title="A"),
        1: QuerySearchResult(distance=0.2, id=11, text="b", title="B"),
    }
    mock_search = AsyncMock(return_value=candidates)
    monkeypatch.setattr(service, "USE_CROSS_ENCODER", "True")
    monkeypatch.setattr(service, "get_similar_content_async", mock_search)

    result = await service.get_search_response(
        query_refined=query_refined,
        response=query_response,
        asession=AsyncMock(),
        n_similar=1,
        n_to_crossencoder=5,
        crossencoder=FakeCrossEncoder(scores=[0.1, 0.9]),
        workspace_id=1,
    )

    assert mock_search.call_args.kwargs["n_similar"] == 5
    assert result.search_results is not None
    assert [r.id for r in result.search_results.values()] == [11]


@pytest.mark.usefixtures("bypass_input_guardrails")
async def test_get_search_response_rejects_bad_crossencoder_config(
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """Sending fewer candidates to the cross-encoder than requested is an error.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    monkeypatch.setattr(service, "USE_CROSS_ENCODER", "True")

    with pytest.raises(ValueError, match="n_to_crossencoder"):
        await service.get_search_response(
            query_refined=query_refined,
            response=query_response,
            asession=AsyncMock(),
            n_similar=5,
            n_to_crossencoder=2,
            crossencoder=None,
            workspace_id=1,
        )


async def test_get_generation_response_without_llm(
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """Search-only queries skip generation and the alignment check.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    mock_generate = AsyncMock()
    mock_align = AsyncMock()
    monkeypatch.setattr(service, "generate_llm_query_response", mock_generate)
    monkeypatch.setattr(service, "_check_align_score", mock_align)
    query_refined.generate_llm_response = False

    result = await service.get_generation_response(
        query_refined=query_refined, response=query_response
    )

    assert result is query_response
    mock_generate.assert_not_called()
    mock_align.assert_not_called()


async def test_get_generation_response_saves_chat_history(
    fake_redis: FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """For chats, the updated history is cached and the answer is align-checked.

    Parameters
    ----------
    fake_redis
        The in-memory Redis client.
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    history = [{"content": "hi", "name": "11", "role": "user"}]
    monkeypatch.setattr(
        service,
        "generate_llm_query_response",
        AsyncMock(return_value=(query_response, history)),
    )
    mock_align = AsyncMock(side_effect=lambda **kwargs: kwargs["response"])
    monkeypatch.setattr(service, "_check_align_score", mock_align)
    query_refined.chat_query_params = {
        "chat_cache_key": "chatCache:11",
        "redis_client": fake_redis,
    }

    result = await service.get_generation_response(
        query_refined=query_refined, response=query_response
    )

    assert result is query_response
    assert json.loads(fake_redis.store["chatCache:11"]) == history
    mock_align.assert_called_once()


@pytest.mark.parametrize(
    "chat_query_params, expected_query_text",
    [
        (None, "original"),
        ({"search_query": "rewritten", "session_id": "1"}, "rewritten"),
    ],
)
async def test_get_user_query_and_response(
    chat_query_params: dict[str, Any] | None,
    expected_query_text: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query is saved and chat queries search with the LLM-built query.

    Parameters
    ----------
    chat_query_params
        The chat parameters, or `None` for a plain search.
    expected_query_text
        The query text used for the search.
    monkeypatch
        Pytest monkeypatch.
    """

    query_db = SimpleNamespace(feedback_secret_key="secret", query_id=7)
    mock_save = AsyncMock(return_value=query_db)
    monkeypatch.setattr(service, "save_user_query_to_db", mock_save)
    user_query = QueryBase(
        chat_query_params=chat_query_params,
        generate_llm_response=True,
        query_text="original",
        session_id=3,
    )

    saved, refined, response = await service.get_user_query_and_response(
        asession=AsyncMock(),
        generate_tts=True,
        user_query=user_query,
        workspace_doc_language="ENGLISH",
        workspace_id=1,
    )

    assert saved is query_db
    assert refined.query_text == expected_query_text
    assert refined.query_text_original == "original"
    assert refined.generate_tts is True
    assert "search_query" not in (refined.chat_query_params or {})
    assert (response.query_id, response.feedback_secret_key, response.session_id) == (
        7,
        "secret",
        3,
    )


@pytest.mark.parametrize("generate_llm_response", [True, False])
async def test_run_query_pipeline(
    generate_llm_response: bool,
    monkeypatch: pytest.MonkeyPatch,
    query_refined: QueryRefined,
    query_response: QueryResponse,
) -> None:
    """Search always runs, generation only on request, and everything is saved.

    Parameters
    ----------
    generate_llm_response
        Whether the user asked for an LLM answer.
    monkeypatch
        Pytest monkeypatch.
    query_refined
        The refined query.
    query_response
        The response.
    """

    query_db = QueryDB(query_id=124)
    mocks = {
        "get_user_query_and_response": AsyncMock(
            return_value=(query_db, query_refined, query_response)
        ),
        "get_search_response": AsyncMock(return_value=query_response),
        "get_generation_response": AsyncMock(return_value=query_response),
        "save_query_response_to_db": AsyncMock(),
        "increment_query_count": AsyncMock(),
        "save_content_for_query_to_db": AsyncMock(),
        "langfuse_context": MagicMock(),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(service, name, mock)
    workspace_db = SimpleNamespace(doc_language="ENGLISH", workspace_id=1)
    user_query = QueryBase(
        generate_llm_response=generate_llm_response, query_text="q", session_id=3
    )

    result = await service._run_query_pipeline(
        asession=AsyncMock(),
        crossencoder=None,
        generate_tts=False,
        trace_name="search",
        user_query=user_query,
        workspace_db=workspace_db,  # type: ignore[arg-type]
    )

    assert result is query_response
    assert mocks["get_generation_response"].called is generate_llm_response
    assert mocks["langfuse_context"].update_current_trace.call_args.kwargs["name"] == (
        "search"
    )
    assert mocks["save_query_response_to_db"].call_args.kwargs["user_query_db"] is (
        query_db
    )
    assert mocks["save_content_for_query_to_db"].call_args.kwargs["query_id"] == 124
    assert mocks["increment_query_count"].call_args.kwargs["workspace_id"] == 1


async def test_search_and_respond(
    monkeypatch: pytest.MonkeyPatch, query_response: QueryResponse
) -> None:
    """Search runs the shared pipeline without TTS under the "search" trace.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    query_response
        The response.
    """

    mock_pipeline = AsyncMock(return_value=query_response)
    monkeypatch.setattr(service, "_run_query_pipeline", mock_pipeline)

    result = await service.search_and_respond(
        asession=AsyncMock(),
        crossencoder=None,
        user_query=QueryBase(generate_llm_response=False, query_text="q"),
        workspace_db=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert result is query_response
    assert mock_pipeline.call_args.kwargs["generate_tts"] is False
    assert mock_pipeline.call_args.kwargs["trace_name"] == "search"


@pytest.mark.parametrize("stt_endpoint", [None, "http://stt"])
async def test_download_and_transcribe_audio(
    stt_endpoint: str | None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The voice note is archived, copied to `temp/` and transcribed by the custom
    STT endpoint if set, else Google STT.

    Parameters
    ----------
    stt_endpoint
        The configured custom STT endpoint.
    monkeypatch
        Pytest monkeypatch.
    tmp_path
        Pytest temporary directory.
    """

    # The service writes to a relative `temp/` folder, so run from a temp dir.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "temp").mkdir()
    stream = BytesIO(b"voice")
    custom_stt = AsyncMock(return_value={"text": "hello"})
    google_stt = AsyncMock(return_value="hello")
    upload = AsyncMock()
    monkeypatch.setattr(service, "CUSTOM_STT_ENDPOINT", stt_endpoint)
    monkeypatch.setattr(
        service,
        "download_file_from_url",
        AsyncMock(return_value=(stream, "audio/mpeg", ".mp3")),
    )
    monkeypatch.setattr(
        service, "generate_random_filename", MagicMock(return_value="voice.mp3")
    )
    monkeypatch.setattr(service, "upload_file_to_gcs", upload)
    monkeypatch.setattr(service, "post_to_speech_stt", custom_stt)
    monkeypatch.setattr(service, "transcribe_audio", google_stt)

    text, file_path, file_stream = await service._download_and_transcribe_audio(
        file_url="http://files/voice"
    )

    assert (text, file_path, file_stream) == ("hello", "temp/voice.mp3", stream)
    assert (tmp_path / "temp" / "voice.mp3").read_bytes() == b"voice"
    assert stream.tell() == 0  # Rewound so it can be read again.
    assert upload.call_args.kwargs["destination_blob_name"] == (
        "stt-voice-notes/voice.mp3"
    )
    assert custom_stt.called is (stt_endpoint is not None)
    assert google_stt.called is (stt_endpoint is None)


@pytest.mark.parametrize("file_exists", [True, False])
def test_remove_temp_audio_file(file_exists: bool, tmp_path: Path) -> None:
    """The temporary file is deleted (and the stream closed) only if it exists.

    Parameters
    ----------
    file_exists
        Whether the temporary file exists.
    tmp_path
        Pytest temporary directory.
    """

    file_path = tmp_path / "voice.mp3"
    if file_exists:
        file_path.write_bytes(b"voice")
    stream = BytesIO(b"voice")

    service._remove_temp_audio_file(file_path=str(file_path), file_stream=stream)

    assert not file_path.exists()
    assert stream.closed is file_exists


# =====================================================================================
# Endpoint services
# =====================================================================================


async def test_process_chat(
    fake_redis: FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
    query_response: QueryResponse,
) -> None:
    """Chat initializes the histories, then runs the search pipeline.

    Parameters
    ----------
    fake_redis
        The in-memory Redis client.
    monkeypatch
        Pytest monkeypatch.
    query_response
        The response.
    """

    initialized = QueryBase(
        generate_llm_response=True, query_text="rewritten", session_id=5
    )
    mock_init = AsyncMock(return_value=initialized)
    mock_search = AsyncMock(return_value=query_response)
    monkeypatch.setattr(service, "init_user_query_and_chat_histories", mock_init)
    monkeypatch.setattr(service, "search_and_respond", mock_search)
    asession = AsyncMock()
    workspace_db = SimpleNamespace(workspace_id=1)

    # `inspect.unwrap` skips `with_new_session`, so no real DB session is opened.
    result = await inspect.unwrap(service.process_chat)(
        asession=asession,
        crossencoder=None,
        redis_client=fake_redis,
        reset_chat_history=True,
        user_query=QueryBase(
            generate_llm_response=False, query_text="hi", session_id=5
        ),
        workspace_db=workspace_db,
    )

    assert result is query_response
    assert mock_init.call_args.kwargs["reset_chat_history"] is True
    assert mock_init.call_args.kwargs["redis_client"] is fake_redis
    assert mock_search.call_args.kwargs == {
        "asession": asession,
        "crossencoder": None,
        "user_query": initialized,
        "workspace_db": workspace_db,
    }


def _turnio_query() -> QueryBase:
    """Build a Turn.io (WhatsApp) chat query.

    Returns
    -------
    QueryBase
        The query.
    """

    return QueryBase(
        generate_llm_response=True,
        query_text="hello via WhatsApp",
        session_id=456,
        turnio_api_key="[TURNIO_API_KEY]",  # pragma: allowlist secret
        wa_id="whatsapp:+1234567890",
    )


@pytest.mark.parametrize(
    "search_outcome, expected_text",
    [
        (
            QueryResponse(
                feedback_secret_key=None,
                llm_response="WhatsApp reply text",
                query_id=None,
                search_results=None,
                session_id=None,
            ),
            "WhatsApp reply text",
        ),
        (_error_response(), "Guardrail failure: bad query"),
        (LLMCallException("boom"), LLM_CALL_ERROR_MESSAGE),
    ],
    ids=["answer", "guardrail-error", "llm-error"],
)
async def test_process_turnio_chat_sends_reply(
    search_outcome: QueryResponse | Exception,
    expected_text: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reply (answer, guardrail message or LLM error) is sent via Turn.io and
    the Turn.io payload is merged with its API response.

    Parameters
    ----------
    search_outcome
        What the search pipeline returns (or raises).
    expected_text
        The text that should be sent to WhatsApp.
    monkeypatch
        Pytest monkeypatch.
    """

    user_query = _turnio_query()
    httpx_client = object()
    mock_send = AsyncMock(return_value={"id": "turn-msg-123", "status": "queued"})
    langfuse = MagicMock()
    monkeypatch.setattr(
        service,
        "init_user_query_and_chat_histories",
        AsyncMock(side_effect=lambda **kwargs: kwargs["user_query"]),
    )
    monkeypatch.setattr(
        service, "search_and_respond", AsyncMock(side_effect=[search_outcome])
    )
    monkeypatch.setattr(service, "send_turn_text_message", mock_send)
    monkeypatch.setattr(service, "langfuse_context", langfuse)

    result = await inspect.unwrap(service.process_turnio_chat)(
        asession=AsyncMock(),
        crossencoder=None,
        httpx_client=httpx_client,
        redis_client=FakeRedis(),
        reset_chat_history=False,
        user_query=user_query,
        workspace_db=SimpleNamespace(workspace_id=1),
    )

    assert result is not None
    assert result["to"] == user_query.wa_id
    assert result["text"]["body"] == expected_text
    assert (result["id"], result["status"]) == ("turn-msg-123", "queued")
    mock_send.assert_awaited_once_with(
        httpx_client=httpx_client,
        text=expected_text,
        turnio_api_key=user_query.turnio_api_key,
        whatsapp_id=user_query.wa_id,
    )
    langfuse.update_current_trace.assert_called_once_with(name="chat")


async def test_process_turnio_chat_stops_if_chat_init_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An LLM failure while building the chat query ends the task silently.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    """

    mock_send = AsyncMock()
    mock_search = AsyncMock()
    monkeypatch.setattr(
        service,
        "init_user_query_and_chat_histories",
        AsyncMock(side_effect=LLMCallException("boom")),
    )
    monkeypatch.setattr(service, "search_and_respond", mock_search)
    monkeypatch.setattr(service, "send_turn_text_message", mock_send)

    result = await inspect.unwrap(service.process_turnio_chat)(
        asession=AsyncMock(),
        crossencoder=None,
        httpx_client=object(),
        redis_client=FakeRedis(),
        reset_chat_history=False,
        user_query=_turnio_query(),
        workspace_db=SimpleNamespace(workspace_id=1),
    )

    assert result is None
    mock_search.assert_not_called()
    mock_send.assert_not_called()


@pytest.mark.parametrize("is_chat", [False, True])
async def test_voice_flows(
    is_chat: bool,
    monkeypatch: pytest.MonkeyPatch,
    query_response: QueryResponse,
) -> None:
    """Voice search/chat transcribe, run the TTS pipeline and clean up the file.

    Parameters
    ----------
    is_chat
        Whether to test voice chat (else voice search).
    monkeypatch
        Pytest monkeypatch.
    query_response
        The response.
    """

    stream = BytesIO(b"voice")
    mock_cleanup = MagicMock()
    mock_pipeline = AsyncMock(return_value=query_response)
    mock_init = AsyncMock(side_effect=lambda **kwargs: kwargs["user_query"])
    monkeypatch.setattr(
        service,
        "_download_and_transcribe_audio",
        AsyncMock(return_value=("hello", "temp/voice.mp3", stream)),
    )
    monkeypatch.setattr(service, "_run_query_pipeline", mock_pipeline)
    monkeypatch.setattr(service, "_remove_temp_audio_file", mock_cleanup)
    monkeypatch.setattr(service, "init_user_query_and_chat_histories", mock_init)
    common: dict[str, Any] = {
        "asession": AsyncMock(),
        "crossencoder": None,
        "file_url": "http://files/voice",
        "workspace_db": SimpleNamespace(workspace_id=1),
    }

    if is_chat:
        result = await service.voice_chat_and_respond(
            **common,
            redis_client=FakeRedis(),  # type: ignore[arg-type]
            reset_chat_history=True,
            session_id=9,
        )
    else:
        result = await service.voice_search_and_respond(**common)

    assert result is query_response
    kwargs = mock_pipeline.call_args.kwargs
    assert kwargs["generate_tts"] is True
    assert kwargs["trace_name"] == ("voice-chat" if is_chat else "voice-search")
    assert kwargs["user_query"].query_text == "hello"
    assert kwargs["user_query"].generate_llm_response is True
    assert mock_init.called is is_chat
    if is_chat:
        assert mock_init.call_args.kwargs["reset_chat_history"] is True
        assert kwargs["user_query"].session_id == 9
    mock_cleanup.assert_called_once_with(file_path="temp/voice.mp3", file_stream=stream)


def _response_feedback() -> ResponseFeedbackBase:
    """Build response feedback.

    Returns
    -------
    ResponseFeedbackBase
        The feedback.
    """

    return ResponseFeedbackBase(
        feedback_secret_key="secret",
        feedback_sentiment=FeedbackSentiment.POSITIVE,
        feedback_text=None,
        query_id=5,
    )


def _content_feedback() -> ContentFeedback:
    """Build content feedback.

    Returns
    -------
    ContentFeedback
        The feedback.
    """

    return ContentFeedback(
        content_id=3,
        feedback_secret_key="secret",
        feedback_sentiment=FeedbackSentiment.NEGATIVE,
        feedback_text=None,
        query_id=5,
    )


@pytest.mark.parametrize("is_content", [False, True])
async def test_save_feedback_rejects_wrong_secret(
    is_content: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Feedback whose secret key does not match the query is rejected.

    Parameters
    ----------
    is_content
        Whether to test content feedback (else response feedback).
    monkeypatch
        Pytest monkeypatch.
    """

    mock_save_response = AsyncMock()
    mock_save_content = AsyncMock()
    monkeypatch.setattr(
        service, "check_secret_key_match", AsyncMock(return_value=False)
    )
    monkeypatch.setattr(service, "save_response_feedback_to_db", mock_save_response)
    monkeypatch.setattr(service, "save_content_feedback_to_db", mock_save_content)

    with pytest.raises(FeedbackRejectedError) as exc_info:
        if is_content:
            await service.save_content_feedback(
                asession=AsyncMock(), feedback=_content_feedback(), workspace_id=1
            )
        else:
            await service.save_response_feedback(
                asession=AsyncMock(), feedback=_response_feedback()
            )

    assert "Secret key does not match query" in exc_info.value.content["message"]
    mock_save_response.assert_not_called()
    mock_save_content.assert_not_called()


async def test_save_response_feedback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Matching feedback is saved and confirmed.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    """

    monkeypatch.setattr(service, "check_secret_key_match", AsyncMock(return_value=True))
    monkeypatch.setattr(
        service,
        "save_response_feedback_to_db",
        AsyncMock(return_value=SimpleNamespace(feedback_id=8, query_id=5)),
    )

    message = await service.save_response_feedback(
        asession=AsyncMock(), feedback=_response_feedback()
    )

    assert message == "Added Feedback: 8 for Query: 5"


async def test_save_content_feedback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Matching content feedback is saved and the content's votes are updated.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    """

    mock_votes = AsyncMock()
    monkeypatch.setattr(service, "check_secret_key_match", AsyncMock(return_value=True))
    monkeypatch.setattr(
        service,
        "save_content_feedback_to_db",
        AsyncMock(
            return_value=SimpleNamespace(content_id=3, feedback_id=8, query_id=5)
        ),
    )
    monkeypatch.setattr(service, "update_votes_in_db", mock_votes)

    message = await service.save_content_feedback(
        asession=AsyncMock(), feedback=_content_feedback(), workspace_id=1
    )

    assert message == "Added Feedback: 8 for Query: 5 for Content: 3"
    assert mock_votes.call_args.kwargs["content_id"] == 3
    assert mock_votes.call_args.kwargs["vote"] == FeedbackSentiment.NEGATIVE
    assert mock_votes.call_args.kwargs["workspace_id"] == 1


async def test_save_content_feedback_unknown_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign-key failure (unknown content) is turned into a rejection.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch.
    """

    mock_votes = AsyncMock()
    monkeypatch.setattr(service, "check_secret_key_match", AsyncMock(return_value=True))
    monkeypatch.setattr(
        service,
        "save_content_feedback_to_db",
        AsyncMock(side_effect=IntegrityError("INSERT", {}, Exception("fk"))),
    )
    monkeypatch.setattr(service, "update_votes_in_db", mock_votes)

    with pytest.raises(FeedbackRejectedError) as exc_info:
        await service.save_content_feedback(
            asession=AsyncMock(), feedback=_content_feedback(), workspace_id=1
        )

    assert exc_info.value.content["message"] == "Content ID: 3 does not exist."
    assert exc_info.value.content["details"]["exception"] == "IntegrityError"
    mock_votes.assert_not_called()
