"""This module contains the FastAPI router for the content search and AI response
endpoints.
"""

import os
from typing import Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import authenticate_key, rate_limiter
from ..config import SPEECH_ENDPOINT
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
    generate_llm_response__after,
)
from ..users.models import UserDB
from ..utils import create_langfuse_metadata, get_http_client, setup_logger
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
    QueryBase,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
    ResponseFeedbackBase,
)

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
    "/stt-llm-response",
    response_model=QueryResponse,
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
async def stt_llm_response(
    generate_tts: bool = Form(...),
    file: UploadFile = File(...),
    exclude_archived: bool = Form(True),
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> QueryResponse | JSONResponse:
    """
    Endpoint to transcribe audio from the provided file and generate an LLM response.
    """
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    transcription_result = await post_to_speech(file_path, SPEECH_ENDPOINT)
    user_query = QueryBase(
        generate_llm_response=True,
        query_text=transcription_result["text"],
        query_metadata={},
        generate_tts=generate_tts,
    )

    (
        user_query_db,
        user_query_refined_template,
        response_template,
    ) = await get_user_query_and_response(
        user_id=user_db.user_id,
        user_query=user_query,
        asession=asession,
    )

    response = await search_base(
        query_refined=user_query_refined_template,
        response=response_template,
        user_id=user_db.user_id,
        n_similar=int(N_TOP_CONTENT),
        asession=asession,
        exclude_archived=exclude_archived,
    )
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

    if os.path.exists(file_path):
        os.remove(file_path)

    if type(response) is QueryResponse:
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


async def post_to_speech(file_path: str, endpoint_url: str) -> dict:
    """
    Post request the file to the speech endpoint to get the transcription
    """
    async with get_http_client() as client:
        async with client.post(endpoint_url, json={"file_path": file_path}) as response:
            if response.status != 200:
                error_content = await response.json()
                logger.error(f"Error from SPEECH_ENDPOINT: {error_content}")
                raise HTTPException(status_code=response.status, detail=error_content)
            return await response.json()


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
    )
    response = await search_base(
        query_refined=user_query_refined_template,
        response=response_template,
        user_id=user_db.user_id,
        n_similar=int(N_TOP_CONTENT),
        asession=asession,
        exclude_archived=True,
    )

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


@identify_language__before
@classify_safety__before
@translate_question__before
@paraphrase_question__before
@generate_llm_response__after
@check_align_score__after
async def search_base(
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

    Raises
    ------
    ValueError
        If the question language is not identified.
    """

    # always do the embeddings search even if some guardrails have failed
    metadata = create_langfuse_metadata(query_id=response.query_id, user_id=user_id)
    search_results = await get_similar_content_async(
        user_id=user_id,
        # use latest version of the text
        question=query_refined.query_text,
        n_similar=n_similar,
        asession=asession,
        metadata=metadata,
        exclude_archived=exclude_archived,
    )
    response.search_results = search_results

    return response


async def get_user_query_and_response(
    user_id: int, user_query: QueryBase, asession: AsyncSession
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
        query_text_original=user_query.query_text,
    )
    # prepare placeholder response object
    response_template = QueryResponse(
        query_id=user_query_db.query_id,
        session_id=user_query.session_id,
        feedback_secret_key=user_query_db.feedback_secret_key,
        llm_response=None,
        tts_file=None,
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
