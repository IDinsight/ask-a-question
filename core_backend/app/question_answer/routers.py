"""This module contains FastAPI routers for the content search and AI response
endpoints.
"""

import json
import os
from io import BytesIO

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from langfuse.decorators import langfuse_context, observe  # type: ignore
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import authenticate_key, rate_limiter
from ..config import (
    CUSTOM_STT_ENDPOINT,
    GCS_SPEECH_BUCKET,
    REDIS_CHAT_CACHE_EXPIRY_TIME,
    USE_CROSS_ENCODER,
)
from ..contents.models import (
    get_similar_content_async,
    increment_query_count,
    update_votes_in_db,
)
from ..database import get_async_session
from ..llm_call.llm_prompts import ChatHistory
from ..llm_call.process_input import (
    classify_safety__before,
    identify_language__before,
    paraphrase_question__before,
    translate_question__before,
)
from ..llm_call.process_output import (
    check_align_score__after,
    generate_llm_query_response,
    generate_tts__after,
)
from ..llm_call.utils import (
    LLMCallException,
    append_message_content_to_chat_history,
    get_chat_response,
    init_chat_history,
)
from ..schemas import QuerySearchResult
from ..users.models import WorkspaceDB
from ..utils import (
    generate_random_filename,
    get_random_int32,
    setup_logger,
    upload_file_to_gcs,
)
from .config import N_TOP_CONTENT, N_TOP_CONTENT_TO_CROSSENCODER
from .models import (
    QueryDB,
    check_secret_key_match,
    save_content_feedback_to_db,
    save_content_for_query_to_db,
    save_query_response_to_db,
    save_response_feedback_to_db,
    save_user_query_to_db,
)
from .schemas import (
    ContentFeedback,
    QueryAudioResponse,
    QueryBase,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
    ResponseFeedbackBase,
)
from .speech_components.external_voice_components import transcribe_audio
from .speech_components.utils import download_file_from_url, post_to_speech_stt

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
    user_query: QueryBase,
    request: Request,
    asession: AsyncSession = Depends(get_async_session),
    workspace_db: WorkspaceDB = Depends(authenticate_key),
    reset_chat_history: bool = False,
) -> QueryResponse | JSONResponse:
    """Chat endpoint manages a conversation between the user and the LLM agent. The
    conversation history is stored in a Redis cache. The process is as follows:

    1. Initialize chat histories and update the user query object.
    2. Call the search function to get the appropriate response.

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
    reset_chat_history
        Specifies whether to reset the chat history.

    Returns
    -------
    QueryResponse | JSONResponse
        The query response object or an appropriate JSON response.
    """
    try:
        # 1.
        user_query = await init_user_query_and_chat_histories(
            redis_client=request.app.state.redis,
            reset_chat_history=reset_chat_history,
            user_query=user_query,
        )

        # 2

        response = await search(
            user_query=user_query,
            request=request,
            asession=asession,
            workspace_db=workspace_db,
        )
        langfuse_context.update_current_trace(name="chat")
        return response
    except LLMCallException:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error_message": (
                    "LLM call returned an error: Please check LLM configuration"
                )
            },
        )


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
        workspace_id = workspace_db.workspace_id
        user_query_db, user_query_refined_template, response_template = (
            await get_user_query_and_response(
                asession=asession,
                generate_tts=False,
                user_query=user_query,
                workspace_id=workspace_id,
            )
        )
        assert isinstance(user_query_db, QueryDB)

        response = await get_search_response(
            asession=asession,
            exclude_archived=True,
            n_similar=int(N_TOP_CONTENT),
            n_to_crossencoder=int(N_TOP_CONTENT_TO_CROSSENCODER),
            query_refined=user_query_refined_template,
            request=request,
            response=response_template,
            workspace_id=workspace_id,
        )

        if user_query.generate_llm_response:
            response = await get_generation_response(
                query_refined=user_query_refined_template, response=response
            )

        langfuse_context.update_current_trace(
            name="search",
            session_id=user_query_refined_template.session_id,
            metadata={"query_id": response.query_id, "workspace_id": workspace_id},
        )

        await save_query_response_to_db(
            asession=asession,
            response=response,
            user_query_db=user_query_db,
            workspace_id=workspace_id,
        )
        await increment_query_count(
            asession=asession,
            contents=response.search_results,
            workspace_id=workspace_id,
        )
        await save_content_for_query_to_db(
            asession=asession,
            contents=response.search_results,
            query_id=response.query_id,
            session_id=user_query.session_id,
            workspace_id=workspace_id,
        )

        if isinstance(response, QueryResponseError):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST, content=response.model_dump()
            )

        if isinstance(response, QueryResponse):
            return response

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error_message": "Internal server error"},
        )
    except LLMCallException:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error_message": (
                    "LLM call returned an error: Please check LLM configuration"
                )
            },
        )


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

    workspace_id = workspace_db.workspace_id

    try:
        file_stream, content_type, file_extension = await download_file_from_url(
            file_url=file_url
        )
        assert isinstance(file_stream, BytesIO)

        unique_filename = generate_random_filename(extension=file_extension)
        destination_blob_name = f"stt-voice-notes/{unique_filename}"

        await upload_file_to_gcs(
            bucket_name=GCS_SPEECH_BUCKET,
            content_type=content_type,
            destination_blob_name=destination_blob_name,
            file_stream=file_stream,
        )

        file_path = f"temp/{unique_filename}"
        with open(file_path, "wb") as f:
            file_stream.seek(0)
            f.write(file_stream.read())
        file_stream.seek(0)

        if CUSTOM_STT_ENDPOINT is not None:
            transcription = await post_to_speech_stt(
                file_path=file_path, endpoint_url=CUSTOM_STT_ENDPOINT
            )
            transcription_result = transcription["text"]
        else:
            transcription_result = await transcribe_audio(audio_filename=file_path)

        user_query = QueryBase(
            generate_llm_response=True,
            query_metadata={},
            query_text=transcription_result,
        )

        (
            user_query_db,
            user_query_refined_template,
            response_template,
        ) = await get_user_query_and_response(
            asession=asession,
            generate_tts=True,
            user_query=user_query,
            workspace_id=workspace_id,
        )
        assert isinstance(user_query_db, QueryDB)

        response = await get_search_response(
            asession=asession,
            exclude_archived=True,
            n_similar=int(N_TOP_CONTENT),
            n_to_crossencoder=int(N_TOP_CONTENT_TO_CROSSENCODER),
            query_refined=user_query_refined_template,
            request=request,
            response=response_template,
            workspace_id=workspace_id,
        )

        if user_query.generate_llm_response:
            response = await get_generation_response(
                query_refined=user_query_refined_template, response=response
            )

        langfuse_context.update_current_trace(
            name="voice-search",
            session_id=user_query_refined_template.session_id,
            metadata={"query_id": response.query_id, "workspace_id": workspace_id},
        )

        await save_query_response_to_db(
            asession=asession,
            response=response,
            user_query_db=user_query_db,
            workspace_id=workspace_id,
        )
        await increment_query_count(
            asession=asession,
            contents=response.search_results,
            workspace_id=workspace_id,
        )
        await save_content_for_query_to_db(
            asession=asession,
            contents=response.search_results,
            query_id=response.query_id,
            session_id=user_query.session_id,
            workspace_id=workspace_id,
        )

        if os.path.exists(file_path):
            os.remove(file_path)
            file_stream.close()

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

    except ValueError as ve:
        logger.error(f"ValueError: {str(ve)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Value error: {str(ve)}"},
        )

    except Exception as e:  # pylint: disable=W0718
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )


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

    workspace_id = workspace_db.workspace_id

    try:
        file_stream, content_type, file_extension = await download_file_from_url(
            file_url=file_url
        )
        assert isinstance(file_stream, BytesIO)

        unique_filename = generate_random_filename(extension=file_extension)
        destination_blob_name = f"stt-voice-notes/{unique_filename}"

        await upload_file_to_gcs(
            bucket_name=GCS_SPEECH_BUCKET,
            content_type=content_type,
            destination_blob_name=destination_blob_name,
            file_stream=file_stream,
        )

        file_path = f"temp/{unique_filename}"
        with open(file_path, "wb") as f:
            file_stream.seek(0)
            f.write(file_stream.read())
        file_stream.seek(0)

        if CUSTOM_STT_ENDPOINT is not None:
            transcription = await post_to_speech_stt(
                file_path=file_path, endpoint_url=CUSTOM_STT_ENDPOINT
            )
            transcription_result = transcription["text"]
        else:
            transcription_result = await transcribe_audio(audio_filename=file_path)

        user_query = QueryBase(
            generate_llm_response=True,
            query_metadata={},
            query_text=transcription_result,
            session_id=session_id,
        )

        # 1.
        user_query = await init_user_query_and_chat_histories(
            redis_client=request.app.state.redis,
            reset_chat_history=reset_chat_history,
            user_query=user_query,
        )

        # 2.
        (
            user_query_db,
            user_query_refined_template,
            response_template,
        ) = await get_user_query_and_response(
            asession=asession,
            generate_tts=True,
            user_query=user_query,
            workspace_id=workspace_id,
        )
        assert isinstance(user_query_db, QueryDB)

        response = await get_search_response(
            asession=asession,
            exclude_archived=True,
            n_similar=int(N_TOP_CONTENT),
            n_to_crossencoder=int(N_TOP_CONTENT_TO_CROSSENCODER),
            query_refined=user_query_refined_template,
            request=request,
            response=response_template,
            workspace_id=workspace_id,
        )

        if user_query.generate_llm_response:  # Should be always true in this case
            response = await get_generation_response(
                query_refined=user_query_refined_template, response=response
            )

        langfuse_context.update_current_trace(
            name="voice-chat",
            session_id=user_query_refined_template.session_id,
            metadata={"query_id": response.query_id, "workspace_id": workspace_id},
        )

        await save_query_response_to_db(
            asession=asession,
            response=response,
            user_query_db=user_query_db,
            workspace_id=workspace_id,
        )
        await increment_query_count(
            asession=asession,
            contents=response.search_results,
            workspace_id=workspace_id,
        )
        await save_content_for_query_to_db(
            asession=asession,
            contents=response.search_results,
            query_id=response.query_id,
            session_id=user_query.session_id,
            workspace_id=workspace_id,
        )

        if os.path.exists(file_path):
            os.remove(file_path)
            file_stream.close()

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

    # Unsure where to place this
    except LLMCallException:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error_message": (
                    "LLM call returned an error: Please check LLM configuration"
                )
            },
        )

    except ValueError as ve:
        logger.error(f"ValueError: {str(ve)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Value error: {str(ve)}"},
        )

    except Exception as e:  # pylint: disable=W0718
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )


@identify_language__before
@classify_safety__before
@translate_question__before
@paraphrase_question__before
async def get_search_response(
    query_refined: QueryRefined,
    response: QueryResponse,
    asession: AsyncSession,
    n_similar: int,
    n_to_crossencoder: int,
    request: Request,
    workspace_id: int,
    exclude_archived: bool = True,
    exclude_unvalidated: bool = True,
) -> QueryResponse | QueryResponseError:
    """Get similar content and construct the LLM answer for the user query.

    If any guardrails fail, the embeddings search is still done and a
    `QueryResponseError` object is returned that includes the search results as well as
    the details of the failure.

    Parameters
    ----------
    query_refined
        The refined query object.
    response
        The query response object.
    asession
        The SQLAlchemy async session to use for all database connections.
    n_similar
        The number of similar contents to retrieve.
    n_to_crossencoder
        The number of similar contents to send to the cross-encoder.
    request
        The FastAPI request object.
    workspace_id
        The ID of the workspace that the contents of the search query belong to.
    exclude_archived
        Specifies whether to exclude archived content.
    exclude_unvalidated
        Specifies whether to exclude unvalidated content.

    Returns
    -------
    QueryResponse | QueryResponseError
        An appropriate query response object.

    Raises
    ------
    ValueError
        If the cross encoder is being used and `n_to_crossencoder` is greater than
        `n_similar`.
    """

    # No checks for errors: always do the embeddings search even if some guardrails
    # have failed.
    if USE_CROSS_ENCODER == "True" and (n_to_crossencoder < n_similar):
        raise ValueError(
            f"`n_to_crossencoder`({n_to_crossencoder}) must be less than or equal to "
            f"`n_similar`({n_similar})."
        )

    search_results = await get_similar_content_async(
        asession=asession,
        exclude_archived=exclude_archived,
        exclude_unvalidated=exclude_unvalidated,
        n_similar=n_to_crossencoder if USE_CROSS_ENCODER == "True" else n_similar,
        question=query_refined.query_text,  # Use latest transformed version of the text
        workspace_id=workspace_id,
    )

    if USE_CROSS_ENCODER and len(search_results) > 1:
        search_results = rerank_search_results(
            n_similar=n_similar,
            query_text=query_refined.query_text,
            request=request,
            search_results=search_results,
        )

    response.search_results = search_results

    return response


def rerank_search_results(
    *,
    n_similar: int,
    query_text: str,
    request: Request,
    search_results: dict[int, QuerySearchResult],
) -> dict[int, QuerySearchResult]:
    """Rerank search results based on the similarity of the content to the query text.

    Parameters
    ----------
    n_similar
        The number of similar contents retrieved.
    query_text
        The query text.
    request
        The FastAPI request object.
    search_results
        The search results.

    Returns
    -------
    dict[int, QuerySearchResult]
        The reranked search results.
    """

    encoder = request.app.state.crossencoder
    contents = search_results.values()
    scores = encoder.predict(
        [(query_text, content.title + "\n" + content.text) for content in contents]
    )

    sorted_by_score = [
        v for _, v in sorted(zip(scores, contents), key=lambda x: x[0], reverse=True)
    ][:n_similar]
    reranked_search_results = dict(enumerate(sorted_by_score))

    return reranked_search_results


@generate_tts__after
@check_align_score__after
async def get_generation_response(
    query_refined: QueryRefined, response: QueryResponse
) -> QueryResponse | QueryResponseError:
    """Generate a response using an LLM given a query with search results.

    Only runs if the `generate_llm_response` flag is set to `True`.

    Requires "search_results" and "original_language" in the response.

    NB: This function will also update the user assistant chat cache with the updated
    chat history. There is no need to update the search query chat cache since the chat
    history for the search query conversation uses the chat history from the user
    assistant chat.

    Parameters
    ----------
    query_refined
        The refined query object.
    response
        The query response object.

    Returns
    -------
    QueryResponse | QueryResponseError
        The appropriate query response object.
    """

    if not query_refined.generate_llm_response:
        return response

    response, chat_history = await generate_llm_query_response(
        query_refined=query_refined,
        response=response,
    )
    if query_refined.chat_query_params and chat_history:
        chat_cache_key = query_refined.chat_query_params["chat_cache_key"]
        redis_client = query_refined.chat_query_params["redis_client"]
        await redis_client.set(
            chat_cache_key, json.dumps(chat_history), ex=REDIS_CHAT_CACHE_EXPIRY_TIME
        )

    return response


async def get_user_query_and_response(
    *,
    asession: AsyncSession,
    generate_tts: bool,
    user_query: QueryBase,
    workspace_id: int,
) -> tuple[QueryDB, QueryRefined, QueryResponse]:
    """Save the user query to the `QueryDB` database and construct placeholder query
    and response objects to pass on.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    generate_tts
        Specifies whether to generate a TTS audio response
    workspace_id
        The ID of the workspace that the user belongs to.
    user_query
        The user query database object.

    Returns
    -------
    tuple[QueryDB, QueryRefined, QueryResponse]
        The user query database object, the refined query object, and the response
        object.
    """

    # Save the query to the `QueryDB` database.
    user_query_db = await save_user_query_to_db(
        asession=asession, user_query=user_query, workspace_id=workspace_id
    )

    # Prepare the refined query object.
    user_query_refined = QueryRefined(
        **user_query.model_dump(),
        generate_tts=generate_tts,
        query_text_original=user_query.query_text,
        workspace_id=workspace_id,
    )

    # Prepare the placeholder response object.
    response_template = QueryResponse(
        debug_info={},
        feedback_secret_key=user_query_db.feedback_secret_key,
        llm_response=None,
        query_id=user_query_db.query_id,
        search_results=None,
        session_id=user_query.session_id,
    )
    return user_query_db, user_query_refined, response_template


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

    is_matched = await check_secret_key_match(
        asession=asession,
        query_id=feedback_.query_id,
        secret_key=feedback_.feedback_secret_key,
    )

    if is_matched is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": f"Secret key does not match query id: {feedback_.query_id}"
            },
        )

    feedback_db = await save_response_feedback_to_db(
        asession=asession, feedback=feedback_
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": (
                f"Added Feedback: {feedback_db.feedback_id} "
                f"for Query: {feedback_db.query_id}"
            )
        },
    )


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

    is_matched = await check_secret_key_match(
        asession=asession,
        query_id=feedback_.query_id,
        secret_key=feedback_.feedback_secret_key,
    )
    if is_matched is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": f"Secret key does not match query ID: {feedback_.query_id}"
            },
        )

    try:
        feedback_db = await save_content_feedback_to_db(
            asession=asession, feedback=feedback_
        )
    except IntegrityError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": f"Content ID: {feedback_.content_id} does not exist.",
                "details": {
                    "content_id": feedback_.content_id,
                    "query_id": feedback_.query_id,
                    "exception": "IntegrityError",
                    "exception_details": str(e),
                },
            },
        )

    await update_votes_in_db(
        asession=asession,
        content_id=feedback_.content_id,
        vote=feedback_.feedback_sentiment,
        workspace_id=workspace_db.workspace_id,
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": (
                f"Added Feedback: {feedback_db.feedback_id} "
                f"for Query: {feedback_db.query_id} "
                f"for Content: {feedback_db.content_id}"
            )
        },
    )


async def init_user_query_and_chat_histories(
    *,
    redis_client: aioredis.Redis,
    reset_chat_history: bool = False,
    user_query: QueryBase,
) -> QueryBase:
    """Initialize chat histories. The process is as follows:

    1. Assign a random int32 session ID if not provided.
    2. Initialize the user assistant chat history and the user assistant chat
        parameters.
    3. Initialize the search query chat history. NB: The chat parameters for the search
        query chat are the same as the chat parameters for the user assistant chat.
    4. Invoke the LLM to construct a relevant database search query that is
        contextualized on the latest user message and the user assistant chat history.
        The search query chat contains a system message that instructs the LLM to
        construct a refined search query using the latest user message and the
        conversation history from the user assistant chat (**without** the user
        assistant chat's system message).
    5. Update the user query object with the chat query parameters, set the flag to
        generate the LLM response, and assign the session ID. For the chat endpoint,
        the LLM response generation is always done.

    Parameters
    ----------
    redis_client
        The Redis client.
    reset_chat_history
        Specifies whether to reset the chat history.
    user_query
        The user query object.

    Returns
    -------
    QueryBase
        The updated user query object.
    """

    # 1.
    session_id = str(user_query.session_id or get_random_int32())

    # 2.
    chat_cache_key = f"chatCache:{session_id}"
    chat_params_cache_key = f"chatParamsCache:{session_id}"
    _, _, user_assistant_chat_history, chat_params = await init_chat_history(
        chat_cache_key=chat_cache_key,
        chat_params_cache_key=chat_params_cache_key,
        redis_client=redis_client,
        reset=reset_chat_history,
        session_id=session_id,
    )
    assert isinstance(chat_params, dict)
    assert isinstance(user_assistant_chat_history, list)

    # 3.
    search_query_chat_history: list[dict[str, str | None]] = []
    append_message_content_to_chat_history(
        chat_history=search_query_chat_history,
        message_content=ChatHistory.system_message_construct_search_query,
        model=str(chat_params["model"]),
        model_context_length=int(chat_params["max_input_tokens"]),
        name=session_id,
        role="system",
        total_tokens_for_next_generation=int(chat_params["max_output_tokens"]),
    )

    # 4.
    index = 1 if user_assistant_chat_history[0]["role"] == "system" else 0
    search_query_chat_history += user_assistant_chat_history[index:]
    search_query_json_str = await get_chat_response(
        chat_history=search_query_chat_history,
        chat_params=chat_params,
        message_params=user_query.query_text,
        session_id=session_id,
    )
    search_query_json_response = ChatHistory.parse_json(
        chat_type="search", json_str=search_query_json_str
    )

    # 5.
    user_query.chat_query_params = {
        "chat_cache_key": chat_cache_key,
        "chat_history": user_assistant_chat_history,
        "chat_params": chat_params,
        "message_type": search_query_json_response["message_type"],
        "redis_client": redis_client,
        "search_query": search_query_json_response["query"],
        "session_id": session_id,
    }
    user_query.generate_llm_response = True
    user_query.session_id = int(session_id)

    return user_query
