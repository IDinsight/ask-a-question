"""Unit tests for `app.core.utils`.

LiteLLM, Langfuse and Google Cloud Storage are replaced with mocks, so no network
call is made.
"""

from io import BytesIO
from types import SimpleNamespace
from typing import Any, AsyncGenerator, Mapping
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from app.core import utils
from app.core.config import LITELLM_API_KEY, LITELLM_ENDPOINT, LITELLM_MODEL_EMBEDDING
from app.core.utils import (
    EmbeddingCallException,
    HttpClient,
    LLMCallException,
    ask_llm_async,
    embedding,
    format_prompt,
    generate_public_url,
    generate_random_filename,
    get_file_extension_from_mime_type,
    get_http_client,
    remove_json_markdown,
    upload_file_to_gcs,
)


def _await_kwargs(mock: AsyncMock) -> Mapping[str, Any]:
    """Return the keyword arguments of the mock's last await.

    Parameters
    ----------
    mock
        The awaited mock.

    Returns
    -------
    Mapping[str, Any]
        The keyword arguments.
    """

    assert mock.await_args is not None, "mock was never awaited"
    return mock.await_args.kwargs


def _llm_response(content: str | None = "answer", error: Any = None) -> Any:
    """Build an object shaped like a LiteLLM chat completion response.

    Parameters
    ----------
    content
        The message content of the first choice.
    error
        Value of the response's `error` attribute.

    Returns
    -------
    Any
        The fake response.
    """

    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], error=error)


@pytest.fixture(autouse=True)
def langfuse_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every LLM/embedding call a fixed Langfuse trace ID.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    context = MagicMock()
    context.get_current_trace_id.return_value = "trace-1"
    monkeypatch.setattr(utils, "langfuse_context", context)


@pytest.fixture
def acompletion(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Replace `litellm.acompletion` as used by `ask_llm_async`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    AsyncMock
        The mock, returning a valid response by default.
    """

    mock = AsyncMock(return_value=_llm_response())
    monkeypatch.setattr(utils, "acompletion", mock)
    return mock


@pytest.fixture
def aembedding(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Replace `litellm.aembedding` as used by `embedding`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    AsyncMock
        The mock, returning a valid response by default.
    """

    mock = AsyncMock(return_value=SimpleNamespace(data=[{"embedding": [0.1, 0.2]}]))
    monkeypatch.setattr(utils, "aembedding", mock)
    return mock


@pytest.fixture
async def no_global_http_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[None, None]:
    """Start with no global HTTP client and close any session the test creates.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Yields
    ------
    AsyncGenerator[None, None]
        Nothing.
    """

    monkeypatch.setattr(utils, "_HTTP_CLIENT", None)
    yield
    session = utils.get_global_http_client()
    if session is not None and not session.closed:
        await session.close()


# HTTP client.
async def test_http_client_lifecycle() -> None:
    """`HttpClient` opens a session on start and closes it on stop."""

    http_client = HttpClient()
    http_client.start()
    session = http_client()

    assert isinstance(session, aiohttp.ClientSession)

    await http_client.stop()
    assert session.closed
    assert http_client.session is None
    # Stopping twice is a no-op.
    await http_client.stop()


def test_http_client_call_before_start() -> None:
    """Asking for the session before `start` fails loudly."""

    with pytest.raises(AssertionError):
        HttpClient()()


async def test_get_http_client_reuses_open_session(
    no_global_http_client: None,
) -> None:
    """The global session is created once and reused while open.

    Parameters
    ----------
    no_global_http_client
        Fixture resetting the global client.
    """

    first = get_http_client()
    second = get_http_client()

    assert first is second
    assert utils.get_global_http_client() is first


async def test_get_http_client_replaces_closed_session(
    no_global_http_client: None,
) -> None:
    """A closed global session is replaced by a new one.

    Parameters
    ----------
    no_global_http_client
        Fixture resetting the global client.
    """

    first = get_http_client()
    await first.close()

    second = get_http_client()

    assert second is not first
    assert not second.closed


# Storage.
async def test_generate_public_url() -> None:
    """The public URL points at the blob in the bucket."""

    url = await generate_public_url(blob_name="a/b.mp3", bucket_name="bucket")

    assert url == "https://storage.googleapis.com/bucket/a/b.mp3"


def test_generate_random_filename() -> None:
    """Filenames are five UUID hex strings plus the extension, and unique."""

    name = generate_random_filename(extension=".wav")

    assert name.endswith(".wav")
    assert len(name) == 5 * 32 + len(".wav")
    assert name != generate_random_filename(extension=".wav")


@pytest.mark.parametrize(
    "mime_type, extension",
    [
        ("audio/mpeg", ".mp3"),
        ("audio/x-wav", ".wav"),
        ("application/pdf", ".pdf"),
        ("made/up", ".bin"),
        (None, ".bin"),
        ("", ".bin"),
    ],
)
def test_get_file_extension_from_mime_type(
    mime_type: str | None, extension: str
) -> None:
    """Known audio types use the lookup table, others `mimetypes`, else `.bin`.

    Parameters
    ----------
    mime_type
        The MIME type.
    extension
        The expected extension.
    """

    assert get_file_extension_from_mime_type(mime_type=mime_type) == extension


async def test_upload_file_to_gcs(monkeypatch: pytest.MonkeyPatch) -> None:
    """The stream is rewound and uploaded to the named bucket and blob.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    storage = MagicMock()
    monkeypatch.setattr(utils, "storage", storage)
    stream = BytesIO(b"audio")
    stream.read()  # Move to the end; the upload must start from the beginning.

    await upload_file_to_gcs(
        bucket_name="bucket",
        content_type="audio/mpeg",
        destination_blob_name="a.mp3",
        file_stream=stream,
    )

    bucket = storage.Client.return_value.bucket
    bucket.assert_called_once_with("bucket")
    blob = bucket.return_value.blob
    blob.assert_called_once_with("a.mp3")
    blob.return_value.upload_from_file.assert_called_once_with(
        stream, content_type="audio/mpeg"
    )
    assert stream.tell() == 0


# LLM calls.
async def test_ask_llm_async_builds_messages(acompletion: AsyncMock) -> None:
    """System and user messages become the chat history; defaults are applied.

    Parameters
    ----------
    acompletion
        The mocked `litellm.acompletion`.
    """

    result = await ask_llm_async(
        litellm_model="model-x", system_message="sys", user_message="user"
    )

    assert result == "answer"
    kwargs = _await_kwargs(acompletion)
    assert kwargs["messages"] == [
        {"content": "sys", "role": "system"},
        {"content": "user", "role": "user"},
    ]
    assert kwargs["model"] == "model-x"
    assert kwargs["api_base"] == LITELLM_ENDPOINT
    assert kwargs["api_key"] == LITELLM_API_KEY
    assert kwargs["metadata"] == {"generation_name": "model-x", "trace_id": "trace-1"}
    assert (kwargs["max_tokens"], kwargs["temperature"]) == (1024, 1)
    assert "response_format" not in kwargs


async def test_ask_llm_async_with_messages_json_and_params(
    acompletion: AsyncMock,
) -> None:
    """Explicit messages, JSON mode and generation params are passed through.

    Parameters
    ----------
    acompletion
        The mocked `litellm.acompletion`.
    """

    messages: list[dict[str, str | None]] = [{"content": "hi", "role": "user"}]
    metadata = {"feature": "test"}

    await ask_llm_async(
        json_=True,
        llm_generation_params={"temperature": 0},
        messages=messages,
        metadata=metadata,
    )

    kwargs = _await_kwargs(acompletion)
    assert kwargs["messages"] is messages
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["temperature"] == 0
    assert "max_tokens" not in kwargs
    # The caller's metadata is extended in place.
    assert metadata["feature"] == "test"
    assert metadata["trace_id"] == "trace-1"


@pytest.mark.parametrize(
    "setup, match",
    [
        ({"side_effect": RuntimeError("timeout")}, "Error during LLM call: timeout"),
        (
            {"return_value": _llm_response(error="rate limited")},
            "LLM call returned an error: rate limited",
        ),
        (
            {"return_value": SimpleNamespace(choices=[])},
            "LLM response structure is not as expected",
        ),
        (
            {"return_value": SimpleNamespace(choices=[SimpleNamespace()])},
            "LLM response structure is not as expected",
        ),
    ],
)
async def test_ask_llm_async_errors(
    acompletion: AsyncMock, setup: dict[str, Any], match: str
) -> None:
    """Call failures, error responses and malformed responses raise
    `LLMCallException`.

    Parameters
    ----------
    acompletion
        The mocked `litellm.acompletion`.
    setup
        Attributes to configure on the mock.
    match
        Expected error message pattern.
    """

    acompletion.configure_mock(**setup)

    with pytest.raises(LLMCallException, match=match):
        await ask_llm_async(system_message="sys", user_message="user")


# Prompt and text helpers.
@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"prompt": "  Hi {name}\n    there"}, "Hi {name}\nthere"),
        ({"prompt": "  Hi {name}", "prompt_kws": {"name": "Ann"}}, "Hi Ann"),
        (
            {"prompt": "  Hi {name}", "remove_leading_blank_spaces": False},
            "  Hi {name}",
        ),
    ],
)
def test_format_prompt(kwargs: dict[str, Any], expected: str) -> None:
    """Leading blanks are stripped per line and keywords filled in when given.

    Parameters
    ----------
    kwargs
        Arguments for `format_prompt`.
    expected
        The expected prompt.
    """

    assert format_prompt(**kwargs) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ('```json\n{"a": 1}\n```', '{"a": 1}'),
        ('  {"a": 1}  ', '{"a": 1}'),
        (r"\{\}", "{}"),
        ('```{"a": 1}', '```{"a": 1}'),
    ],
)
def test_remove_json_markdown(text: str, expected: str) -> None:
    """Markdown code fences and escaped braces are removed.

    Parameters
    ----------
    text
        The raw LLM output.
    expected
        The cleaned text.
    """

    assert remove_json_markdown(text=text) == expected


# Embeddings.
async def test_embedding(aembedding: AsyncMock) -> None:
    """The embedding vector is extracted from the LiteLLM response.

    Parameters
    ----------
    aembedding
        The mocked `litellm.aembedding`.
    """

    result = await embedding(text_to_embed="hello")

    assert result == [0.1, 0.2]
    kwargs = _await_kwargs(aembedding)
    assert kwargs["input"] == "hello"
    assert kwargs["model"] == LITELLM_MODEL_EMBEDDING
    assert kwargs["metadata"] == {"trace_id": "trace-1"}


@pytest.mark.parametrize(
    "setup, match",
    [
        ({"side_effect": RuntimeError("down")}, "Error during embedding call: down"),
        ({"return_value": SimpleNamespace(data=[])}, "not as expected"),
        ({"return_value": SimpleNamespace(data=[{}])}, "not as expected"),
        ({"return_value": SimpleNamespace()}, "not as expected"),
    ],
)
async def test_embedding_errors(
    aembedding: AsyncMock, setup: dict[str, Any], match: str
) -> None:
    """Call failures and malformed responses raise `EmbeddingCallException`.

    Parameters
    ----------
    aembedding
        The mocked `litellm.aembedding`.
    setup
        Attributes to configure on the mock.
    match
        Expected error message pattern.
    """

    aembedding.configure_mock(**setup)

    with pytest.raises(EmbeddingCallException, match=match):
        await embedding(metadata={"a": 1}, text_to_embed="hello")


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"system_message": "FooBar"}, {"user_message": "FooBar"}],
    ids=["no_messages", "system_only", "user_only"],
)
async def test_ask_llm_async_requires_messages(
    acompletion: AsyncMock, kwargs: dict[str, Any]
) -> None:
    """`ask_llm_async` needs `messages`, or both a system and a user message.

    Each incomplete combination is its own case, so every one is actually run
    (inside a single `pytest.raises` block only the first call would execute).

    Parameters
    ----------
    acompletion
        Mocked `litellm.acompletion` (never reached).
    kwargs
        The incomplete arguments to call `ask_llm_async` with.
    """

    with pytest.raises(AssertionError):
        await ask_llm_async(**kwargs)
    acompletion.assert_not_awaited()
