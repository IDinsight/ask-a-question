"""This module contains FastAPI routers for the content search and AI response
endpoints.

Handlers only do HTTP work: they read shared clients off `request.app.state`, call
the matching function in `app.question_answer.service`, and turn the result (or a
failure) into the HTTP response.
"""

from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.background import BackgroundTasks
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from langfuse.decorators import observe  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import authenticate_key, rate_limiter
from app.core.database import get_async_session
from app.core.observability import setup_logger
from app.core.utils import LLMCallException
from app.question_answer.schemas import (
    ContentFeedback,
    QueryAudioResponse,
    QueryBase,
    QueryResponse,
    QueryResponseError,
    ResponseFeedbackBase,
)
from app.question_answer.service import (
    INTERNAL_SERVER_ERROR_MESSAGE,
    LLM_CALL_ERROR_MESSAGE,
    FeedbackRejectedError,
    assign_chat_session_id,
    build_turnio_ack_response,
    is_turnio_chat,
    process_chat,
    process_turnio_chat,
    save_content_feedback,
    save_response_feedback,
    search_and_respond,
    voice_chat_and_respond,
    voice_search_and_respond,
)
from app.workspaces.models import WorkspaceDB

logger = setup_logger()


TAG_METADATA = {
    "name": "Question-answering and feedback",
    "description": "_Requires API key._ LLM-powered question answering based on "
    "your content plus feedback collection.",
}


router = APIRouter(
    dependencies=[Depends(authenticate_key), Depends(rate_limiter)],
    tags=[TAG_METADATA["name"]],
)


def _get_crossencoder(request: Request) -> Any:
    """Return the cross-encoder loaded at startup, if any.

    The cross-encoder is only loaded when `USE_CROSS_ENCODER == "True"`, so it may be
    missing from `app.state`.

    Parameters
    ----------
    request
        The FastAPI request object.

    Returns
    -------
    Any
        The cross-encoder model, or `None` if it was not loaded.
    """

    return getattr(request.app.state, "crossencoder", None)


def _llm_call_error_response() -> JSONResponse:
    """Build the 502 response returned when an LLM call fails.

    Returns
    -------
    JSONResponse
        The error response.
    """

    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"error_message": LLM_CALL_ERROR_MESSAGE},
    )


def _search_http_response(
    response: QueryResponse | QueryResponseError,
) -> QueryResponse | JSONResponse:
    """Turn a search/chat pipeline result into the HTTP response.

    Parameters
    ----------
    response
        The pipeline result.

    Returns
    -------
    QueryResponse | JSONResponse
        The response object on success, a 400 with the error details if a guardrail
        failed, or a 500 for an unexpected result.
    """

    # `QueryResponseError` subclasses `QueryResponse`, so check it first.
    if isinstance(response, QueryResponseError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content=response.model_dump()
        )

    if isinstance(response, QueryResponse):
        return response

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error_message": INTERNAL_SERVER_ERROR_MESSAGE},
    )


def _voice_http_response(
    response: QueryResponse | QueryResponseError,
) -> QueryAudioResponse | JSONResponse:
    """Turn a voice pipeline result into the HTTP response.

    Parameters
    ----------
    response
        The pipeline result.

    Returns
    -------
    QueryAudioResponse | JSONResponse
        The audio response on success, a 400 with the error details if a guardrail
        failed, or a 500 for an unexpected result.
    """

    if isinstance(response, QueryResponseError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content=response.model_dump()
        )

    if isinstance(response, QueryAudioResponse):
        return response

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"},
    )


def _voice_error_response(error: Exception) -> JSONResponse:
    """Log an unexpected voice endpoint failure and build the 500 response.

    Parameters
    ----------
    error
        The exception raised by the voice service.

    Returns
    -------
    JSONResponse
        The error response. `ValueError`s include their message.
    """

    if isinstance(error, ValueError):
        logger.error(f"ValueError: {str(error)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Value error: {str(error)}"},
        )

    logger.error(f"Unexpected error: {str(error)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"},
    )


@router.post(
    "/chat",
    response_model=QueryResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": QueryResponseError,
            "description": "Guardrail failure",
        }
    },
)
@observe()
async def chat(
    background_tasks: BackgroundTasks,
    user_query: QueryBase,
    request: Request,
    workspace_db: WorkspaceDB = Depends(authenticate_key),
    reset_chat_history: bool = False,
) -> QueryResponse | JSONResponse | dict[str, Any]:
    """Chat endpoint manages a conversation between the user and the LLM agent. The
    conversation history is stored in a Redis cache.

    The process is as follows:

    1. Assign a random int32 session ID for the chat session if not provided.
    2. If `use_callback_url` is `True`, add the chat processing task to the background
         tasks and return an immediate response to the user.
    3. If `use_callback_url` is `False`, process the chat request asynchronously and
        return the response.

    Parameters
    ----------
    background_tasks
        The FastAPI background tasks object.
    user_query
        The user query object.
    request
        The FastAPI request object.
    workspace_db
        The authenticated workspace object.
    reset_chat_history
        Specifies whether to reset the chat history.

    Returns
    -------
    QueryResponse | JSONResponse | dict[str, Any]
        The query response object, an appropriate JSON response, or a dictionary
        (for WhatsApp responses).
    """

    crossencoder = _get_crossencoder(request)
    redis_client = request.app.state.redis

    # 1.
    assign_chat_session_id(user_query=user_query)

    # 2.
    if is_turnio_chat(user_query=user_query):
        background_tasks.add_task(
            process_turnio_chat,
            crossencoder=crossencoder,
            httpx_client=request.app.state.httpx_client,
            redis_client=redis_client,
            reset_chat_history=reset_chat_history,
            user_query=user_query,
            workspace_db=workspace_db,
        )
        return build_turnio_ack_response(session_id=user_query.session_id)

    # 3.
    try:
        response = await process_chat(
            crossencoder=crossencoder,
            redis_client=redis_client,
            reset_chat_history=reset_chat_history,
            user_query=user_query,
            workspace_db=workspace_db,
        )
    except LLMCallException:
        return _llm_call_error_response()

    return _search_http_response(response)


@router.post(
    "/search",
    response_model=QueryResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": QueryResponseError,
            "description": "Guardrail failure",
        }
    },
)
@observe()
async def search(
    user_query: QueryBase,
    request: Request,
    asession: AsyncSession = Depends(get_async_session),
    workspace_db: WorkspaceDB = Depends(authenticate_key),
) -> QueryResponse | JSONResponse:
    """Search endpoint finds the most similar content to the user query and optionally
    generates a single-turn LLM response.

    If any guardrails fail, the embeddings search is still done and an error 400 is
    returned that includes the search results as well as the details of the failure.

    Parameters
    ----------
    user_query
        The user query object.
    request
        The FastAPI request object.
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_db
        The authenticated workspace object.

    Returns
    -------
    QueryResponse | JSONResponse
        The query response object or an appropriate JSON response.
    """
    try:
        response = await search_and_respond(
            asession=asession,
            crossencoder=_get_crossencoder(request),
            user_query=user_query,
            workspace_db=workspace_db,
        )
    except LLMCallException:
        return _llm_call_error_response()

    return _search_http_response(response)


@router.post(
    "/voice-search",
    response_model=QueryAudioResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": QueryResponseError,
            "description": "Bad Request",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": QueryResponseError,
            "description": "Internal Server Error",
        },
    },
)
@observe()
async def voice_search(
    file_url: str,
    request: Request,
    asession: AsyncSession = Depends(get_async_session),
    workspace_db: WorkspaceDB = Depends(authenticate_key),
) -> QueryAudioResponse | JSONResponse:
    """Endpoint to transcribe audio from a provided URL, generate an LLM response, by
    default `generate_tts` is set to `True`, and return a public random URL of an audio
    file containing the spoken version of the generated response.

    Parameters
    ----------
    file_url
        The URL of the audio file.
    request
        The FastAPI request object.
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_db
        The authenticated workspace object.

    Returns
    -------
    QueryAudioResponse | JSONResponse
        The query audio response object or an appropriate JSON response.
    """

    # NB: Unlike `/voice-chat`, LLM call failures here are reported as a generic 500.
    try:
        response = await voice_search_and_respond(
            asession=asession,
            crossencoder=_get_crossencoder(request),
            file_url=file_url,
            workspace_db=workspace_db,
        )
    except Exception as e:  # pylint: disable=W0718
        return _voice_error_response(e)

    return _voice_http_response(response)


@router.post(
    "/voice-chat",
    response_model=QueryAudioResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": QueryResponseError,
            "description": "Bad Request",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": QueryResponseError,
            "description": "Internal Server Error",
        },
    },
)
@observe()
async def voice_chat(
    file_url: str,
    request: Request,
    session_id: int | None = None,
    reset_chat_history: bool = False,
    asession: AsyncSession = Depends(get_async_session),
    workspace_db: WorkspaceDB = Depends(authenticate_key),
) -> QueryAudioResponse | JSONResponse:
    """Endpoint to transcribe audio from a provided URL, generate an LLM response, by
    default `generate_tts` is set to `True`, and return a public random URL of an audio
    file containing the spoken version of the generated response.

    Parameters
    ----------
    file_url
        The URL of the audio file.
    request
        The FastAPI request object.
    session_id
        The session ID for the chat, in case of a continuation of a previous chat.
    reset_chat_history
        Specifies whether to reset the chat history.
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_db
        The authenticated workspace object.

    Returns
    -------
    QueryAudioResponse | JSONResponse
        The query audio response object or an appropriate JSON response.
    """

    try:
        response = await voice_chat_and_respond(
            asession=asession,
            crossencoder=_get_crossencoder(request),
            file_url=file_url,
            redis_client=request.app.state.redis,
            reset_chat_history=reset_chat_history,
            session_id=session_id,
            workspace_db=workspace_db,
        )
    except LLMCallException:
        return _llm_call_error_response()
    except Exception as e:  # pylint: disable=W0718
        return _voice_error_response(e)

    return _voice_http_response(response)


@router.post("/response-feedback")
async def feedback(
    feedback_: ResponseFeedbackBase,
    asession: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    """Feedback endpoint used to capture user feedback on the results returned by QA
    endpoints.

    <B>Note</B>: This endpoint accepts `feedback_sentiment` ("positive" or "negative")
    and/or `feedback_text` (free-text). If you wish to only provide one of these, don't
    include the other in the payload.

    Parameters
    ----------
    feedback_
        The feedback object.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    JSONResponse
        The appropriate feedback response object.
    """

    try:
        message = await save_response_feedback(asession=asession, feedback=feedback_)
    except FeedbackRejectedError as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e.content)

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": message})


@router.post("/content-feedback")
async def content_feedback(
    feedback_: ContentFeedback,
    asession: AsyncSession = Depends(get_async_session),
    workspace_db: WorkspaceDB = Depends(authenticate_key),
) -> JSONResponse:
    """Feedback endpoint used to capture user feedback on specific content after it has
    been returned by the QA endpoints.

    <B>Note</B>: This endpoint accepts `feedback_sentiment` ("positive" or "negative")
    and/or `feedback_text` (free-text). If you wish to only provide one of these, don't
    include the other in the payload.

    Parameters
    ----------
    feedback_
        The feedback object.
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_db
        The authenticated workspace object.

    Returns
    -------
    JSONResponse
        The appropriate feedback response object.
    """

    try:
        message = await save_content_feedback(
            asession=asession,
            feedback=feedback_,
            workspace_id=workspace_db.workspace_id,
        )
    except FeedbackRejectedError as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=e.content)

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": message})
