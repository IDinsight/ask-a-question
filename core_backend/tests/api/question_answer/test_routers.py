"""This module contains tests for question_answer/routers.py."""

from typing import Any

import pytest
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from core_backend.app.question_answer import routers
from core_backend.app.question_answer.routers import _chat, chat
from core_backend.app.question_answer.schemas import QueryBase, QueryResponse


class DummyLangfuseContext:
    """Simple stand-in for Langfuse context for testing."""

    def __init__(self) -> None:
        """Initialize the dummy Langfuse context."""

        self.updated = False
        self.last_name: str = ""

    def update_current_trace(self, name: str) -> None:
        """Record the update of the current trace name.

        Parameters
        ----------
        name
            The new name for the current trace.
        """

        self.last_name = name
        self.updated = True


class DummyWorkspaceDB:
    """Simple stand-in for WorkspaceDB for testing."""

    pass


class FakeBackgroundTasks:
    """Simple stand-in for FastAPI BackgroundTasks that records added tasks."""

    def __init__(self) -> None:
        """Initialize the fake background tasks."""

        self.tasks: list[tuple[object, tuple, dict]] = []

    def add_task(self, func: Any, *args: Any, **kwargs: Any) -> None:
        """Record a task to be run later.

        Parameters
        ----------
        func
            The function to be called as a background task.
        args
            Positional arguments for the function.
        kwargs
            Keyword arguments for the function.
        """

        self.tasks.append((func, args, kwargs))


def make_request_with_app() -> Request:
    """Create a minimal FastAPI app and Request with app.state attributes.

    Returns
    -------
    Request
        A FastAPI Request object with a minimal app and state.
    """

    app = FastAPI()
    app.state.redis = object()
    app.state.httpx_client = object()

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
        "root_path": "",
        "app": app,
    }

    return Request(scope)


@pytest.mark.asyncio
async def test_chat_schedules_task_and_returns_ack_when_using_turnio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When using Turn.io, chat() should:

        1. Assign a random session_id if missing.
        2. Enqueue _chat via background_tasks.add_task(...).
        3. Return an immediate QueryResponse "ack" with the same session_id,

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture for mocking functions.
    """

    request = make_request_with_app()
    workspace = DummyWorkspaceDB()
    background_tasks = FakeBackgroundTasks()

    # user_query without a session_id so that get_random_int32 is used.
    user_query = QueryBase(
        generate_llm_response=True,
        query_text="hello",
        session_id=None,
        turnio_api_key="test-turn-key",
        wa_id="whatsapp:+1234567890",
    )

    # Always return this session id from get_random_int32.
    monkeypatch.setattr(routers, "get_random_int32", lambda: 424242)

    # In this branch, _chat is only scheduled, not awaited.
    result = await chat.__wrapped__(  # type: ignore[misc]
        background_tasks=background_tasks,
        user_query=user_query,
        request=request,
        workspace_db=workspace,
        reset_chat_history=False,
    )

    # Session ID should now be set from get_random_int32.
    assert user_query.session_id == 424242

    # Background task should have been scheduled exactly once.
    assert len(background_tasks.tasks) == 1
    func, args, kwargs = background_tasks.tasks[0]

    # Function scheduled should be the module's _chat.
    assert func is routers._chat

    # _chat is called via kwargs.
    assert kwargs["request"] is request
    assert kwargs["reset_chat_history"] is False
    assert kwargs["user_query"] is user_query
    assert kwargs["workspace_db"] is workspace

    # The endpoint should return a QueryResponse "ack" object.
    assert isinstance(result, QueryResponse)
    assert result.llm_response == "Hang on tight while we process your request!"
    assert result.session_id == user_query.session_id
    assert result.feedback_secret_key is None
    assert result.query_id is None
    assert result.search_results is None


@pytest.mark.asyncio
async def test__chat_whatsapp_sends_turn_message_and_merges_payload_with_query_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When wa_id and turnio_api_key are present and search returns QueryResponse,
    _chat should:

    1. Build a TurnTextMessage from response.llm_response.
    2. Send a Turn.io text message using send_turn_text_message.
    3. Return a dict that merges TurnTextMessage payload + Turn.io JSON response.
    4. Update the langfuse trace name to "chat".

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture for mocking functions.
    """

    request = make_request_with_app()
    workspace = DummyWorkspaceDB()

    user_query = QueryBase(
        generate_llm_response=True,
        query_text="hello via WhatsApp",
        session_id=456,
        turnio_api_key="test-turn-key",
        wa_id="whatsapp:+1234567890",
    )

    async def fake_init_user_query_and_chat_histories(
        *, redis_client: Any, reset_chat_history: bool, user_query: QueryBase
    ) -> QueryBase:
        """Fake init_user_query_and_chat_histories that just returns user_query.

        Parameters
        ----------
        redis_client
            The Redis client from app.state.
        reset_chat_history
            Whether to reset chat history.
        user_query
            The user query object.

        Returns
        -------
        QueryBase
            The unmodified user_query.
        """

        # For this test we don't need to modify user_query, just return it.
        return user_query

    async def fake_search(
        *,
        user_query: QueryBase,
        request: Request,
        asession: Any,
        workspace_db: DummyWorkspaceDB,
    ) -> QueryResponse:
        """Fake search that always returns a QueryResponse with llm_response.

        Parameters
        ----------
        user_query
            The user query object.
        request
            The FastAPI request object.
        asession
            The async session (e.g. HTTPX client).
        workspace_db
            The workspace database object.

        Returns
        -------
        QueryResponse
            A dummy QueryResponse with llm_response set.
        """

        return QueryResponse(
            debug_info={},
            feedback_secret_key=None,
            llm_response="WhatsApp reply text",
            message_type=None,
            query_id=None,
            search_results=None,
            session_id=user_query.session_id,
        )

    recorded_send_args: dict[str, object] = {}

    async def fake_send_turn_text_message(
        *, httpx_client: object, text: str, turnio_api_key: str, whatsapp_id: str
    ) -> dict[str, str]:
        """Fake send_turn_text_message that records its arguments and simulates
        a Turn.io JSON response.

        Parameters
        ----------
        httpx_client
            The HTTPX client to use for sending the message.
        text
            The text message to send.
        turnio_api_key
            The Turn.io API key.
        whatsapp_id
            The WhatsApp ID to send the message to.

        Returns
        -------
        dict[str, str]
            Simulated Turn.io JSON response.
        """

        # Capture what _chat passes to the Turn client.
        recorded_send_args["httpx_client"] = httpx_client
        recorded_send_args["text"] = text
        recorded_send_args["turnio_api_key"] = turnio_api_key
        recorded_send_args["whatsapp_id"] = whatsapp_id

        # Simulate Turn.io JSON response.
        return {"id": "turn-msg-123", "status": "queued"}

    dummy_langfuse_context = DummyLangfuseContext()
    monkeypatch.setattr(
        routers,
        "init_user_query_and_chat_histories",
        fake_init_user_query_and_chat_histories,
    )
    monkeypatch.setattr(routers, "search", fake_search)
    monkeypatch.setattr(
        routers,
        "send_turn_text_message",
        fake_send_turn_text_message,
    )
    monkeypatch.setattr(routers, "langfuse_context", dummy_langfuse_context)

    result = await _chat.__wrapped__(  # type: ignore
        request=request,
        reset_chat_history=False,
        user_query=user_query,
        workspace_db=workspace,
    )

    # _chat should return a plain dict payload for WhatsApp.
    assert isinstance(result, dict)

    # It should contain the TurnTextMessage fields ("to"/"text") plus the Turn.io
    # response fields.
    assert result["to"] == user_query.wa_id
    assert result["text"]["body"] == "WhatsApp reply text"
    assert result["id"] == "turn-msg-123"
    assert result["status"] == "queued"

    # send_turn_text_message should have been called with proper arguments.
    assert recorded_send_args["httpx_client"] is request.app.state.httpx_client
    assert recorded_send_args["text"] == "WhatsApp reply text"
    assert recorded_send_args["turnio_api_key"] == user_query.turnio_api_key
    assert recorded_send_args["whatsapp_id"] == user_query.wa_id

    # langfuse trace should be updated.
    assert dummy_langfuse_context.updated is True
    assert dummy_langfuse_context.last_name == "chat"


@pytest.mark.asyncio
async def test__chat_whatsapp_uses_error_message_when_search_returns_jsonresponse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When wa_id and turnio_api_key are present and search returns JSONResponse
    (e.g. guardrail failure), _chat should:

    1. Use the 'error_message' from the JSONResponse body as the WhatsApp text.
    2. Send that text via Turn.io.
    3. Return the merged payload dict.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture for mocking functions.
    """

    request = make_request_with_app()
    workspace = DummyWorkspaceDB()

    user_query = QueryBase(
        generate_llm_response=True,
        query_text="hello via WhatsApp",
        session_id=999,
        turnio_api_key="test-turn-key",
        wa_id="whatsapp:+1234567890",
    )

    async def fake_init_user_query_and_chat_histories(
        *, redis_client: Any, reset_chat_history: bool, user_query: QueryBase
    ) -> QueryBase:
        """Fake init_user_query_and_chat_histories that just returns user_query.

        Parameters
        ----------
        redis_client
            The Redis client from app.state.
        reset_chat_history
            Whether to reset chat history.
        user_query
            The user query object.

        Returns
        -------
        QueryBase
            The unmodified user_query.
        """

        # Just return user_query as-is for this test.
        return user_query

    async def fake_search(
        *,
        user_query: QueryBase,
        request: Request,
        asession: Any,
        workspace_db: DummyWorkspaceDB,
    ) -> JSONResponse:
        """Fake search that simulates a guardrail / validation error by returning
        a JSONResponse with an error message.

        Parameters
        ----------
        user_query
            The user query object.
        request
            The FastAPI request object.
        asession
            The async session (e.g. HTTPX client).
        workspace_db
            The workspace database object.

        Returns
        -------
        JSONResponse
            A simulated JSONResponse indicating a guardrail failure.
        """

        # Simulate a guardrail/validation error response from the search endpoint.
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error_message": "Guardrail failure: bad query"},
        )

    recorded_send_args: dict[str, object] = {}

    async def fake_send_turn_text_message(
        *, httpx_client: object, text: str, turnio_api_key: str, whatsapp_id: str
    ) -> dict[str, str]:
        """Fake send_turn_text_message that records its arguments and simulates a
        Turn.io JSON response.

        Parameters
        ----------
        httpx_client
            The HTTPX client to use for sending the message.
        text
            The text message to send.
        turnio_api_key
            The Turn.io API key.
        whatsapp_id
            The WhatsApp ID to send the message to.

        Returns
        -------
        dict[str, str]
            Simulated Turn.io JSON response.
        """

        recorded_send_args["httpx_client"] = httpx_client
        recorded_send_args["text"] = text
        recorded_send_args["turnio_api_key"] = turnio_api_key
        recorded_send_args["whatsapp_id"] = whatsapp_id
        return {"id": "turn-msg-error-1", "status": "queued"}

    dummy_langfuse_context = DummyLangfuseContext()
    monkeypatch.setattr(
        routers,
        "init_user_query_and_chat_histories",
        fake_init_user_query_and_chat_histories,
    )
    monkeypatch.setattr(routers, "search", fake_search)
    monkeypatch.setattr(
        routers,
        "send_turn_text_message",
        fake_send_turn_text_message,
    )
    monkeypatch.setattr(routers, "langfuse_context", dummy_langfuse_context)

    result = await _chat.__wrapped__(  # type: ignore
        request=request,
        reset_chat_history=False,
        user_query=user_query,
        workspace_db=workspace,
    )

    assert isinstance(result, dict)

    # WhatsApp payload text should be the error_message from the JSONResponse.
    assert result["to"] == user_query.wa_id
    assert result["text"]["body"] == "Guardrail failure: bad query"
    assert result["id"] == "turn-msg-error-1"
    assert result["status"] == "queued"

    # send_turn_text_message called with error message text.
    assert recorded_send_args["httpx_client"] is request.app.state.httpx_client
    assert recorded_send_args["text"] == "Guardrail failure: bad query"
    assert recorded_send_args["turnio_api_key"] == user_query.turnio_api_key
    assert recorded_send_args["whatsapp_id"] == user_query.wa_id

    assert dummy_langfuse_context.updated is True
    assert dummy_langfuse_context.last_name == "chat"
