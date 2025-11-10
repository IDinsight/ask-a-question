"""This module contains tests for question_answer/routers.py."""

from typing import Any

import pytest
from fastapi import FastAPI, Request

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
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "method": "POST",
        "path": "/chat",
        "raw_path": b"/chat",
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

    # We don't want the background task to actually run real _chat logic. In this
    # branch, _chat is only scheduled, not awaited, so we only need to assert that it
    # was passed correctly to add_task.
    result = await chat.__wrapped__(
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
async def test__chat_whatsapp_sends_turn_message_and_merges_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When wa_id and turnio_api_key are present, _chat should:

    1. Send a Turn.io text message using send_turn_text_message.
    2. Return a dict that merges TurnTextMessage payload + Turn.io JSON response.
    3. Update the langfuse trace name to "chat".
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
        """Fake init_user_query_and_chat_histories that returns the user_query as-is.
        For this test we don't need to modify user_query, just return it.

        Parameters
        ----------
        redis_client
            The Redis client (not used in this fake).
        reset_chat_history
            Whether to reset chat history (not used in this fake).
        user_query
            The user query to initialize.

        Returns
        -------
        QueryBase
            The initialized user query (unchanged).
        """

        return user_query

    async def fake_search(
        *,
        user_query: QueryBase,
        request: Request,
        asession: Any,
        workspace_db: DummyWorkspaceDB
    ) -> QueryResponse:
        """Fake search that returns a dummy QueryResponse.

        Parameters
        ----------
        user_query
            The user query for which to perform the search.
        request
            The FastAPI request object.
        asession
            The async session (not used in this fake).
        workspace_db
            The workspace database (not used in this fake).

        Returns
        -------
        QueryResponse
            A dummy QueryResponse with a preset llm_response.
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
        """Fake send_turn_text_message that records its arguments and returns a
        simulated Turn.io response.

        Parameters
        ----------
        httpx_client
            The HTTPX client used to send the message.
        text
            The text message to send.
        turnio_api_key
            The Turn.io API key.
        whatsapp_id
            The recipient WhatsApp ID.

        Returns
        -------
        dict[str, str]
            A simulated Turn.io JSON response.
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
