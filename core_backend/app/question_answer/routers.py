"""This module contains the FastAPI router for the content search and AI response
endpoints.
"""

import os
from io import BytesIO
from typing import Tuple

from fastapi import APIRouter, Depends, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import authenticate_key, rate_limiter
from ..config import (
    CUSTOM_SPEECH_ENDPOINT,
    GCS_SPEECH_BUCKET,
    TOGGLE_VOICE,
    USE_CROSS_ENCODER,
)
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
from ..schemas import QuerySearchResult
from ..users.models import UserDB
from ..utils import (
    create_langfuse_metadata,
    generate_random_filename,
    get_file_extension_from_mime_type,
    get_http_client,
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
    request: Request,
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
        n_to_crossencoder=int(N_TOP_CONTENT_TO_CROSSENCODER),
        asession=asession,
        exclude_archived=True,
        request=request,
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
        session_id=user_query.session_id,
        query_id=response.query_id,
        contents=response.search_results,
        asession=asession,
    )

    if type(response) is QueryResponse:
        return response

    if type(response) is QueryResponseError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content=response.model_dump()
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal server error"},
    )


if TOGGLE_VOICE is not None:

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
        file_url: str,
        request: Request,
        asession: AsyncSession = Depends(get_async_session),
        user_db: UserDB = Depends(authenticate_key),
    ) -> QueryAudioResponse | JSONResponse:
        """
        Endpoint to transcribe audio from a provided URL,
        generate an LLM response, by default generate_tts is
        set to true and return a public random URL of an audio
        file containing the spoken version of the generated response.
        """
        try:
            file_stream, content_type, file_extension = await download_file_from_url(
                file_url
            )

            unique_filename = generate_random_filename(file_extension)
            destination_blob_name = f"stt-voice-notes/{unique_filename}"

            await upload_file_to_gcs(
                GCS_SPEECH_BUCKET, file_stream, destination_blob_name, content_type
            )

            file_path = f"temp/{unique_filename}"
            with open(file_path, "wb") as f:
                file_stream.seek(0)
                f.write(file_stream.read())
            file_stream.seek(0)

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
                n_to_crossencoder=int(N_TOP_CONTENT_TO_CROSSENCODER),
                asession=asession,
                exclude_archived=True,
                request=request,
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

            if type(response) is QueryResponseError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=response.model_dump(),
                )

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

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error"},
            )


async def download_file_from_url(file_url: str) -> tuple[BytesIO, str, str]:
    """
    Asynchronously download a file from a given URL using the
    global aiohttp ClientSession and return its content as a BytesIO object,
    along with its content type and file extension.
    """
    async with get_http_client() as client:
        try:
            async with client.get(file_url) as response:
                if response.status != 200:
                    error_content = await response.text()
                    logger.error(f"Failed to download file: {error_content}")
                    raise ValueError(f"Failed to download file: {error_content}")

                content_type = response.headers.get("Content-Type")
                if not content_type:
                    logger.error("Content-Type header missing in response")
                    raise ValueError("Unable to determine file content type")

                file_stream = BytesIO(await response.read())
                file_extension = get_file_extension_from_mime_type(content_type)

        except Exception as e:
            logger.error(f"Error during file download: {str(e)}")
            raise ValueError(f"Unable to fetch file: {str(e)}") from None

    return file_stream, content_type, file_extension


async def post_to_speech(file_path: str, endpoint_url: str) -> dict:
    """
    Post request the file to the speech endpoint to get the transcription
    """
    async with get_http_client() as client:
        async with client.post(endpoint_url, json={"file_path": file_path}) as response:
            if response.status != 200:
                error_content = await response.json()
                logger.error(f"Error from CUSTOM_SPEECH_ENDPOINT: {error_content}")
                raise ValueError(f"Error from CUSTOM_SPEECH_ENDPOINT: {error_content}")
            return await response.json()


@identify_language__before
@classify_safety__before
@translate_question__before
@paraphrase_question__before
async def get_search_response(
    query_refined: QueryRefined,
    response: QueryResponse,
    user_id: int,
    n_similar: int,
    n_to_crossencoder: int,
    asession: AsyncSession,
    request: Request,
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
    n_to_crossencoder
        The number of similar contents to send to the cross-encoder.
    asession
        `AsyncSession` object for database transactions.
    request
        The FastAPI request object.
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

    if USE_CROSS_ENCODER == "True" and (n_to_crossencoder < n_similar):
        raise ValueError(
            "`n_to_crossencoder` must be less than or equal to `n_similar`."
        )

    search_results = await get_similar_content_async(
        user_id=user_id,
        question=query_refined.query_text,  # use latest transformed version of the text
        n_similar=n_to_crossencoder if USE_CROSS_ENCODER == "True" else n_similar,
        asession=asession,
        metadata=metadata,
        exclude_archived=exclude_archived,
    )

    if USE_CROSS_ENCODER and (len(search_results) > 1):
        search_results = rerank_search_results(
            n_similar=n_similar,
            search_results=search_results,
            query_text=query_refined.query_text,
            request=request,
        )

    response.search_results = search_results

    return response


def rerank_search_results(
    search_results: dict[int, QuerySearchResult],
    n_similar: int,
    query_text: str,
    request: Request,
) -> dict[int, QuerySearchResult]:
    """
    Rerank search results based on the similarity of the content to the query text
    """
    encoder = request.app.state.crossencoder
    contents = search_results.values()
    scores = encoder.predict(
        [(query_text, content.title + "\n" + content.text) for content in contents]
    )

    sorted_by_score = [v for _, v in sorted(zip(scores, contents), reverse=True)][
        :n_similar
    ]
    reranked_search_results = dict(enumerate(sorted_by_score))

    return reranked_search_results


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
    generate_tts
        Specifies whether to generate a TTS audio response

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
