import os
from typing import Tuple

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import authenticate_key
from ..contents.models import get_similar_content_async, update_votes_in_db
from ..database import get_async_session
from ..llm_call.llm_prompts import RAG_FAILURE_MESSAGE
from ..llm_call.llm_rag import get_llm_rag_answer
from ..llm_call.process_input import (
    classify_safety__before,
    identify_language__before,
    paraphrase_question__before,
    translate_question__before,
)
from ..llm_call.process_output import check_align_score__after
from ..users.models import UserDB
from ..utils import create_langfuse_metadata, generate_secret_key, setup_logger
from ..voice_api.schemas import AudioQuery, AudioQueryError
from ..voice_api.voice import generate_speech, transcribe_audio
from .config import N_TOP_CONTENT_FOR_RAG, N_TOP_CONTENT_FOR_SEARCH
from .models import (
    QueryDB,
    check_secret_key_match,
    save_content_feedback_to_db,
    save_query_response_error_to_db,
    save_query_response_to_db,
    save_response_feedback_to_db,
    save_user_query_to_db,
)
from .schemas import (
    ContentFeedback,
    ErrorType,
    QueryBase,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
    ResponseFeedbackBase,
    ResultState,
)
from .utils import (
    convert_search_results_to_schema,
    get_context_string_from_retrieved_contents,
)

logger = setup_logger()

router = APIRouter(
    dependencies=[Depends(authenticate_key)], tags=["Question Answering"]
)


@router.post(
    "/llm-response",
    response_model=QueryResponse,
    responses={400: {"model": QueryResponseError, "description": "Bad Request"}},
)
async def llm_response(
    user_query: QueryBase,
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> QueryResponse | JSONResponse:
    """
    LLM response creates a custom response to the question using LLM chat and the
    most similar embeddings to the user query in the vector db.
    """
    (
        user_query_db,
        user_query_refined,
        response,
    ) = await get_user_query_and_response(
        user_id=user_db.user_id, user_query=user_query, asession=asession
    )

    response = await get_llm_answer(
        question=user_query_refined,
        response=response,
        user_id=user_db.user_id,
        n_similar=int(N_TOP_CONTENT_FOR_RAG),
        asession=asession,
    )

    if isinstance(response, QueryResponseError):
        await save_query_response_error_to_db(user_query_db, response, asession)
        return JSONResponse(status_code=400, content=response.model_dump())
    else:
        await save_query_response_to_db(user_query_db, response, asession)
        return response


@check_align_score__after
@identify_language__before
@classify_safety__before
async def get_llm_answer(
    question: QueryRefined,
    response: QueryResponse,
    user_id: int,
    n_similar: int,
    asession: AsyncSession,
) -> QueryResponse | QueryResponseError:
    """
    Get similar content and construct the LLM answer for the user query
    """
    if question.original_language is None:
        raise ValueError(
            (
                "Language hasn't been identified. "
                "Identify language before calling this function."
            )
        )

    if not isinstance(response, QueryResponseError):
        metadata = create_langfuse_metadata(query_id=response.query_id, user_id=user_id)
        content_response = convert_search_results_to_schema(
            await get_similar_content_async(
                user_id=user_id,
                question=question.query_text,
                n_similar=n_similar,
                asession=asession,
                metadata=metadata,
            )
        )

        response.content_response = content_response
        context = get_context_string_from_retrieved_contents(content_response)

        rag_response = await get_llm_rag_answer(
            question=question.query_text,
            context=context,
            response_language=question.original_language,
            metadata=metadata,
        )

        if rag_response.answer == RAG_FAILURE_MESSAGE:
            response.state = ResultState.ERROR
            response.llm_response = None
        else:
            response.state = ResultState.FINAL
            response.llm_response = rag_response.answer

        response.debug_info["extracted_info"] = rag_response.extracted_info

        tts_save_path = f"response_{response.query_id}.mp3"

        if question.generate_tts:
            try:
                tts_file_path = await generate_speech(
                    text=rag_response.answer,
                    language=question.original_language,
                    save_path=tts_save_path,
                )
                response.tts_file = tts_file_path
            except ValueError as e:
                return QueryResponseError(
                    query_id=response.query_id,
                    error_message=str(e),
                    error_type=ErrorType.TTS_ERROR,
                    debug_info=response.debug_info,
                )

    return response


async def get_user_query_and_response(
    user_id: int, user_query: QueryBase, asession: AsyncSession
) -> Tuple[QueryDB, QueryRefined, QueryResponse]:
    """
    Get the user query from the request and save it to the db.
    Construct an object for user query and a default response object.
    """
    feedback_secret_key = generate_secret_key()
    user_query_db = await save_user_query_to_db(
        user_id=user_id,
        feedback_secret_key=feedback_secret_key,
        user_query=user_query,
        asession=asession,
    )
    user_query_refined = QueryRefined(
        **user_query.model_dump(), query_text_original=user_query.query_text
    )
    response = QueryResponse(
        query_id=user_query_db.query_id,
        content_response=None,
        llm_response=None,
        feedback_secret_key=feedback_secret_key,
    )

    return user_query_db, user_query_refined, response


@router.post(
    "/stt-llm-response",
    response_model=QueryResponse,
    responses={
        400: {"model": QueryResponseError, "description": "Bad Request"},
        500: {"model": AudioQueryError, "description": "Internal Server Error"},
    },
)
async def stt_llm_response(
    audio_file: AudioQuery,
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> QueryResponse | JSONResponse:
    """
    Transcribes the provided MP3 file to text using Vosk ASR,
    then generates a custom response using LLM and returns it.
    """
    file_path = f"temp/{audio_file.file.filename}"
    try:

        with open(file_path, "wb") as f:
            f.write(await audio_file.file.read())

        transcription = await transcribe_audio(file_path)

        user_query = QueryBase(
            query_text=transcription, query_metadata=audio_file.audio_metadata
        )
        user_query_db, user_query_refined, response = await get_user_query_and_response(
            user_id=user_db.user_id, user_query=user_query, asession=asession
        )

        response = await get_llm_answer(
            question=user_query_refined,
            response=response,
            user_id=user_db.user_id,
            n_similar=int(N_TOP_CONTENT_FOR_RAG),
            asession=asession,
        )

        if isinstance(response, QueryResponseError):
            await save_query_response_error_to_db(user_query_db, response, asession)
            return JSONResponse(status_code=400, content=response.model_dump())
        else:
            await save_query_response_to_db(user_query_db, response, asession)
            return response

    except Exception as e:
        error_msg = f"Failed to process request: {str(e)}"
        logger.error(error_msg)
        error_response = AudioQueryError(
            error_message=error_msg,
            error_type=ErrorType.STT_ERROR,
            debug_info={},
        )
        return JSONResponse(status_code=500, content=error_response.model_dump())

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post(
    "/embeddings-search",
    response_model=QueryResponse,
    responses={400: {"model": QueryResponseError, "description": "Bad Request"}},
)
async def embeddings_search(
    user_query: QueryBase,
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> QueryResponse | JSONResponse:
    """
    Embeddings search finds the most similar embeddings to the user query
    from the vector db.
    """

    (
        user_query_db,
        user_query_refined,
        response,
    ) = await get_user_query_and_response(
        user_id=user_db.user_id, user_query=user_query, asession=asession
    )

    response = await get_semantic_matches(
        question=user_query_refined,
        response=response,
        user_id=user_db.user_id,
        n_similar=int(N_TOP_CONTENT_FOR_SEARCH),
        asession=asession,
    )
    if isinstance(response, QueryResponseError):
        await save_query_response_error_to_db(user_query_db, response, asession)
        return JSONResponse(status_code=400, content=response.model_dump())
    else:
        await save_query_response_to_db(user_query_db, response, asession)
        return response


@identify_language__before
@translate_question__before
@paraphrase_question__before
async def get_semantic_matches(
    question: QueryRefined,
    response: QueryResponse | QueryResponseError,
    user_id: int,
    n_similar: int,
    asession: AsyncSession,
) -> QueryResponse | QueryResponseError:
    """
    Get similar contents from content table
    """
    if not isinstance(response, QueryResponseError):
        metadata = create_langfuse_metadata(query_id=response.query_id, user_id=user_id)
        content_response = convert_search_results_to_schema(
            await get_similar_content_async(
                user_id=user_id,
                question=question.query_text,
                n_similar=n_similar,
                asession=asession,
                metadata=metadata,
            )
        )

        response.content_response = content_response
    return response


@router.post("/response-feedback")
async def feedback(
    feedback: ResponseFeedbackBase,
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> JSONResponse:
    """
    Feedback endpoint used to capture user feedback on the results returned.
    <BR>
    <B>Note</B>: If you wish to only provide `feedback_text`, don't include
    `feedback_sentiment` in the payload.
    """

    is_matched = await check_secret_key_match(
        feedback.feedback_secret_key, feedback.query_id, asession
    )
    if is_matched is False:
        return JSONResponse(
            status_code=400,
            content={
                "message": f"Secret key does not match query id: {feedback.query_id}"
            },
        )

    feedback_db = await save_response_feedback_to_db(feedback, asession)
    return JSONResponse(
        status_code=200,
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
    Feedback endpoint used to capture user feedback on specific content
    <BR>
    <B>Note</B>: If you wish to only provide `feedback_text`, don't include
    `feedback_sentiment` in the payload.
    """

    is_matched = await check_secret_key_match(
        feedback.feedback_secret_key, feedback.query_id, asession
    )
    if is_matched is False:
        return JSONResponse(
            status_code=400,
            content={
                "message": f"Secret key does not match query id: {feedback.query_id}"
            },
        )
    else:
        try:
            feedback_db = await save_content_feedback_to_db(feedback, asession)
        except IntegrityError as e:
            return JSONResponse(
                status_code=400,
                content={
                    "message": (f"Content id: {feedback.content_id} does not exist."),
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
            status_code=200,
            content={
                "message": (
                    f"Added Feedback: {feedback_db.feedback_id} "
                    f"for Query: {feedback_db.query_id} "
                    f"for Content: {feedback_db.content_id}"
                )
            },
        )
