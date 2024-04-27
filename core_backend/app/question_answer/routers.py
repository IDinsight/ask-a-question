from typing import Tuple

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.config import USER1_USERNAME
from ..auth.dependencies import auth_bearer_token
from ..contents.models import get_similar_content_async, update_votes_in_db
from ..database import get_async_session
from ..llm_call.check_output import check_align_score__after
from ..llm_call.llm_prompts import SUMMARY_FAILURE_MESSAGE
from ..llm_call.llm_rag import get_llm_rag_answer
from ..llm_call.parse_input import (
    classify_safety__before,
    identify_language__before,
    paraphrase_question__before,
    translate_question__before,
)
from ..users.models import get_user_by_token
from ..utils import setup_logger
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
    QueryBase,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
    ResponseFeedbackBase,
    ResultState,
)
from .utils import (
    convert_search_results_to_schema,
    generate_secret_key,
    get_context_string_from_retrieved_contents,
)

logger = setup_logger()

router = APIRouter(dependencies=[Depends(auth_bearer_token)])


@router.post(
    "/llm-response",
    response_model=QueryResponse,
    responses={400: {"model": QueryResponseError, "description": "Bad Request"}},
)
async def llm_response(
    user_query: QueryBase,
    asession: AsyncSession = Depends(get_async_session),
    auth_token: str = Depends(auth_bearer_token),
) -> QueryResponse | JSONResponse:
    """
    LLM response creates a custom response to the question using LLM chat and the
    most similar embeddings to the user query in the vector db.
    """
    user = await get_user_by_token(auth_token, asession)
    if user is None:
        return JSONResponse(
            status_code=400,
            content={"message": "No user associated with the provided token."},
        )

    (
        user_query_db,
        user_query_refined,
        response,
    ) = await get_user_query_and_response(
        user_id=user.user_id, user_query=user_query, asession=asession
    )

    response = await get_llm_answer(
        question=user_query_refined,
        response=response,
        user_id=user.user_id,
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
@translate_question__before
@paraphrase_question__before
@classify_safety__before
async def get_llm_answer(
    question: QueryRefined,
    response: QueryResponse,
    user_id: str,
    n_similar: int,
    asession: AsyncSession,
) -> QueryResponse | QueryResponseError:
    """
    Get similar content and construct the LLM answer for the user query
    """
    if not isinstance(response, QueryResponseError):
        content_response = convert_search_results_to_schema(
            await get_similar_content_async(
                user_id=user_id,
                question=question.query_text,
                n_similar=n_similar,
                asession=asession,
            )
        )

        response.content_response = content_response
        context = get_context_string_from_retrieved_contents(content_response)

        llm_response = await get_llm_rag_answer(question.query_text, context)

        if llm_response == SUMMARY_FAILURE_MESSAGE:
            response.state = ResultState.ERROR
            response.llm_response = None
            response.debug_info["reason"] = "LLM Summary failed"
        else:
            response.state = ResultState.FINAL
            response.llm_response = llm_response

    return response


async def get_user_query_and_response(
    user_id: str, user_query: UserQueryBase, asession: AsyncSession
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
    "/embeddings-search",
    response_model=QueryResponse,
    responses={400: {"model": QueryResponseError, "description": "Bad Request"}},
)
async def embeddings_search(
    user_query: QueryBase,
    asession: AsyncSession = Depends(get_async_session),
    auth_token: str = Depends(auth_bearer_token),
) -> QueryResponse | JSONResponse:
    """
    Embeddings search finds the most similar embeddings to the user query
    from the vector db.
    """

    user = await get_user_by_token(auth_token, asession)
    if user is None:
        return JSONResponse(
            status_code=400,
            content={"message": "No user associated with the provided token."},
        )

    (
        user_query_db,
        user_query_refined,
        response,
    ) = await get_user_query_and_response(
        user_id=user.user_id, user_query=user_query, asession=asession
    )

    response = await get_semantic_matches(
        question=user_query_refined,
        response=response,
        user_id=user.user_id,
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
    user_id: str,
    n_similar: int,
    asession: AsyncSession,
) -> QueryResponse | QueryResponseError:
    """
    Get similar contents from content table
    """
    if not isinstance(response, QueryResponseError):
        content_response = convert_search_results_to_schema(
            await get_similar_content_async(
                user_id=user_id,
                question=question.query_text,
                n_similar=n_similar,
                asession=asession,
            )
        )

        response.content_response = content_response
    return response


@router.post("/response-feedback")
async def feedback(
    feedback: ResponseFeedbackBase, asession: AsyncSession = Depends(get_async_session)
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
    else:
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
    feedback: ContentFeedback, asession: AsyncSession = Depends(get_async_session)
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
            user_id=USER1_USERNAME,  # TEMPORARY HARDCODED USER ID
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
