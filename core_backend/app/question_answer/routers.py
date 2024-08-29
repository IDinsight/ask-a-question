"""This module contains the FastAPI router for the content search and AI response
endpoints.
"""

import os
from io import BytesIO
from typing import Tuple

import backoff
from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import authenticate_key, rate_limiter
from ..config import ALIGN_SCORE_N_RETRIES, CUSTOM_SPEECH_ENDPOINT, GCS_SPEECH_BUCKET
from ..contents.models import (
    get_similar_content_async,
    increment_query_count,
    update_votes_in_db,
)
from ..database import get_async_session
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
from ..users.models import UserDB
from ..utils import (
    create_langfuse_metadata,
    generate_random_filename,
    get_file_extension_from_mime_type,
    setup_logger,
    upload_file_to_gcs,
)
from .config import N_TOP_CONTENT
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
    ErrorType,
    QueryAudioResponse,
    QueryBase,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
    ResponseFeedbackBase,
)
from .speech_components.external_voice_components import transcribe_audio
from .speech_components.utils import post_to_speech

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
    "/search",
    response_model=QueryResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": QueryResponseError,
            "description": "Guardrail failure",
        }
    },
)
async def search(
    user_query: QueryBase,
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> QueryResponse | JSONResponse:
    """
    Search endpoint finds the most similar content to the user query and optionally
    generates a single-turn LLM response.

    If any guardrails fail, the embeddings search is still done and an error 400 is
    returned that includes the search results as well as the details of the failure.
    """

    (
        user_query_db,
        user_query_refined_template,
        response_template,
    ) = await get_user_query_and_response(
        user_id=user_db.user_id,
        user_query=user_query,
        asession=asession,
        generate_tts=False,
    )
    response = await get_search_response(
        query_refined=user_query_refined_template,
        response=response_template,
        user_id=user_db.user_id,
        n_similar=int(N_TOP_CONTENT),
        asession=asession,
        exclude_archived=True,
    )

    if user_query.generate_llm_response:
        response = await get_generation_response(
            query_refined=user_query_refined_template,
            response=response,
        )
        if is_unable_to_generate_response(response):
            failure_reason = response.debug_info["factual_consistency"]
            response = await retry_search(
                query_refined=user_query_refined_template, response=response
            )
            response.debug_info["past_failure"] = failure_reason

    await save_query_response_to_db(user_query_db, response, asession)
    await increment_query_count(
        user_id=user_db.user_id,
        contents=response.search_results,
        asession=asession,
    )
    await save_content_for_query_to_db(
        user_id=user_db.user_id,
        session_id=user_query.session_id,
        query_id=response.query_id,
        contents=response.search_results,
        asession=asession,
    )

    if type(response) is QueryResponse:
        return response
    elif type(response) is QueryResponseError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content=response.model_dump()
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
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
async def voice_search(
    file: UploadFile = File(...),
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> QueryAudioResponse | JSONResponse:
    """
    Endpoint to transcribe audio from the provided file,
    generate an LLM response, by default generate_tts is
    set to true and return a public signed URL of an audio
    file containing the spoken version of the generated response
    """
    file_stream = BytesIO(await file.read())

    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        file_stream.seek(0)
        f.write(file_stream.read())

    file_stream.seek(0)

    content_type = file.content_type

    file_extension = get_file_extension_from_mime_type(content_type)
    unique_filename = generate_random_filename(file_extension)

    destination_blob_name = f"stt-voice-notes/{unique_filename}"

    await upload_file_to_gcs(
        GCS_SPEECH_BUCKET, file_stream, destination_blob_name, content_type
    )

    if CUSTOM_SPEECH_ENDPOINT is not None:
        transcription = await post_to_speech(file_path, CUSTOM_SPEECH_ENDPOINT)
        transcription_result = transcription["text"]

    else:
        transcription_result = await transcribe_audio(file_path)

    user_query = QueryBase(
        generate_llm_response=True,
        query_text=transcription_result,
        query_metadata={},
    )

    (
        user_query_db,
        user_query_refined_template,
        response_template,
    ) = await get_user_query_and_response(
        user_id=user_db.user_id,
        user_query=user_query,
        asession=asession,
        generate_tts=True,
    )

    response = await get_search_response(
        query_refined=user_query_refined_template,
        response=response_template,
        user_id=user_db.user_id,
        n_similar=int(N_TOP_CONTENT),
        asession=asession,
        exclude_archived=True,
    )
    if user_query.generate_llm_response:
        response = await get_generation_response(
            query_refined=user_query_refined_template,
            response=response,
        )

    await save_query_response_to_db(user_query_db, response, asession)
    await increment_query_count(
        user_id=user_db.user_id,
        contents=response.search_results,
        asession=asession,
    )
    await save_content_for_query_to_db(
        user_id=user_db.user_id,
        query_id=response.query_id,
        session_id=user_query.session_id,
        contents=response.search_results,
        asession=asession,
    )

    if os.path.exists(file_path):
        os.remove(file_path)
        file_stream.close()

    if type(response) is QueryAudioResponse:
        return response
    elif type(response) is QueryResponseError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content=response.model_dump()
        )
    else:
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
    user_id: int,
    n_similar: int,
    asession: AsyncSession,
    exclude_archived: bool = True,
) -> QueryResponse | QueryResponseError:
    """Get similar content and construct the LLM answer for the user query.

    If any guardrails fail, the embeddings search is still done and a
    `QueryResponseError` object is returned that includes the search
    results as well as the details of the failure.

    Parameters
    ----------
    query_refined
        The refined query object.
    response
        The query response object.
    user_id
        The ID of the user making the query.
    n_similar
        The number of similar contents to retrieve.
    asession
        `AsyncSession` object for database transactions.
    exclude_archived
        Specifies whether to exclude archived content.

    Returns
    -------
    QueryResponse | QueryResponseError
        An appropriate query response object.

    """
    # No checks for errors:
    #   always do the embeddings search even if some guardrails have failed
    metadata = create_langfuse_metadata(query_id=response.query_id, user_id=user_id)

    search_results = await get_similar_content_async(
        user_id=user_id,
        question=query_refined.query_text,  # use latest transformed version of the text
        n_similar=n_similar,
        asession=asession,
        metadata=metadata,
        exclude_archived=exclude_archived,
    )
    response.search_results = search_results

    return response


def is_unable_to_generate_response(response: QueryResponse) -> bool:
    """
    Check if the response is of type QueryResponseError and caused
    by low alignment score.
    """
    return (
        isinstance(response, QueryResponseError)
        and response.error_type == ErrorType.ALIGNMENT_TOO_LOW
    )


@backoff.on_predicate(
    backoff.expo,
    max_tries=int(ALIGN_SCORE_N_RETRIES),
    predicate=is_unable_to_generate_response,
)
async def retry_search(
    query_refined: QueryRefined,
    response: QueryResponse | QueryResponseError,
) -> QueryResponse | QueryResponseError:
    """
    Retry wrapper for get_generation_response.
    """

    metadata = query_refined.query_metadata
    metadata["failure_reason"] = response.debug_info["factual_consistency"]["reason"]
    query_refined.query_metadata = metadata
    return await get_generation_response(query_refined, response)


@generate_tts__after
@check_align_score__after
async def get_generation_response(
    query_refined: QueryRefined,
    response: QueryResponse,
) -> QueryResponse | QueryResponseError:
    """
    Generate a response using an LLM given a query with search results.

    Only runs if the generate_llm_response flag is set to True.
    Requires "search_results" and "original_language" in the response.
    """
    if not query_refined.generate_llm_response:
        return response

    metadata = create_langfuse_metadata(
        query_id=response.query_id, user_id=query_refined.user_id
    )

    metadata["failure_reason"] = query_refined.query_metadata.get(
        "failure_reason", None
    )

    response = await generate_llm_query_response(
        query_refined=query_refined, response=response, metadata=metadata
    )
    return response


async def get_user_query_and_response(
    user_id: int,
    user_query: QueryBase,
    asession: AsyncSession,
    generate_tts: bool,
) -> Tuple[QueryDB, QueryRefined, QueryResponse]:
    """Save the user query to the `QueryDB` database and construct placeholder query
    and response objects to pass on.

    Parameters
    ----------
    user_id
        The ID of the user making the query.
    user_query
        The user query database object.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    Tuple[QueryDB, QueryRefined, QueryResponse]
        The user query database object, the refined query object, and the response
        object.
    """

    # save query to db
    user_query_db = await save_user_query_to_db(
        user_id=user_id,
        user_query=user_query,
        asession=asession,
    )
    # prepare refined query object
    user_query_refined = QueryRefined(
        **user_query.model_dump(),
        user_id=user_id,
        generate_tts=generate_tts,
        query_text_original=user_query.query_text,
    )
    # prepare placeholder response object
    response_template = QueryResponse(
        query_id=user_query_db.query_id,
        session_id=user_query.session_id,
        feedback_secret_key=user_query_db.feedback_secret_key,
        llm_response=None,
        search_results=None,
        debug_info={},
    )
    return user_query_db, user_query_refined, response_template


@router.post("/response-feedback")
async def feedback(
    feedback: ResponseFeedbackBase,
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> JSONResponse:
    """
    Feedback endpoint used to capture user feedback on the results returned by QA
    endpoints.


    <B>Note</B>: This endpoint accepts `feedback_sentiment` ("positive" or "negative")
    and/or `feedback_text` (free-text). If you wish to only provide one of these, don't
    include the other in the payload.
    """

    is_matched = await check_secret_key_match(
        feedback.feedback_secret_key, feedback.query_id, asession
    )
    if is_matched is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": f"Secret key does not match query id: {feedback.query_id}"
            },
        )

    feedback_db = await save_response_feedback_to_db(feedback, asession)
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
    feedback: ContentFeedback,
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> JSONResponse:
    """
    Feedback endpoint used to capture user feedback on specific content after it has
    been returned by the QA endpoints.


    <B>Note</B>: This endpoint accepts `feedback_sentiment` ("positive" or "negative")
    and/or `feedback_text` (free-text). If you wish to only provide one of these, don't
    include the other in the payload.
    """

    is_matched = await check_secret_key_match(
        feedback.feedback_secret_key, feedback.query_id, asession
    )
    if is_matched is False:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": f"Secret key does not match query id: {feedback.query_id}"
            },
        )

    try:
        feedback_db = await save_content_feedback_to_db(feedback, asession)
    except IntegrityError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": f"Content id: {feedback.content_id} does not exist.",
                "details": {
                    "content_id": feedback.content_id,
                    "query_id": feedback.query_id,
                    "exception": "IntegrityError",
                    "exception_details": str(e),
                },
            },
        )
    await update_votes_in_db(
        user_id=user_db.user_id,
        content_id=feedback.content_id,
        vote=feedback.feedback_sentiment,
        asession=asession,
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
