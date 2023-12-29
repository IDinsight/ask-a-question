from typing import Tuple
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import auth_bearer_token
from ..configs.app_config import QDRANT_N_TOP_SIMILAR
from ..db.db_models import (
    UserQueryDB,
    check_secret_key_match,
    save_feedback_to_db,
    save_query_response_to_db,
    save_user_query_to_db,
)
from ..db.engine import get_async_session
from ..db.vector_db import get_qdrant_client, get_similar_content
from ..llm_call.llm_rag import get_llm_rag_answer
from ..llm_call.parse_input import (
    classify_safety,
    identify_language,
    paraphrase_question,
    translate_question,
)
from ..schemas import (
    FeedbackBase,
    ResultState,
    UserQueryBase,
    UserQueryRefined,
    UserQueryResponse,
)

router = APIRouter(dependencies=[Depends(auth_bearer_token)])


@router.post("/llm-response")
async def llm_response(
    user_query: UserQueryBase,
    asession: AsyncSession = Depends(get_async_session),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> UserQueryResponse:
    """
    LLM response creates a custom response to the question using LLM chat and the
    most similar embeddings to the user query in the vector db.
    """
    (
        user_query_db,
        user_query_refined,
        response,
    ) = await get_user_query_and_response(user_query, asession)

    response = await get_llm_answer(user_query_refined, response, qdrant_client)
    await save_query_response_to_db(asession, user_query_db, response)

    return response


@classify_safety
@paraphrase_question
@translate_question
@identify_language
async def get_llm_answer(
    user_query_refined: UserQueryRefined,
    response: UserQueryResponse,
    qdrant_client: QdrantClient,
) -> UserQueryResponse:
    """
    Get similar content and construct the LLM answer for the user query
    """
    if response.state == ResultState.ERROR:
        return response
    content_response = get_similar_content(
        user_query_refined, qdrant_client, int(QDRANT_N_TOP_SIMILAR)
    )
    response.content_response = content_response
    response.llm_response = get_llm_rag_answer(
        user_query_refined.query_text, content_response[0].response_text
    )

    return response


async def get_user_query_and_response(
    user_query: UserQueryBase, asession: AsyncSession
) -> Tuple[UserQueryDB, UserQueryRefined, UserQueryResponse]:
    """
    Get the user query from the request and save it to the db.
    Construct an object for user query and a default response object.
    """
    feedback_secret_key = generate_secret_key()
    user_query_db = await save_user_query_to_db(
        asession, feedback_secret_key, user_query
    )
    user_query_refined = UserQueryRefined(
        **user_query.model_dump(), query_text_original=user_query.query_text
    )
    response = UserQueryResponse(
        query_id=user_query_db.query_id,
        content_response=None,
        llm_response="Sorry, we cannot do that.",
        feedback_secret_key=feedback_secret_key,
    )

    return user_query_db, user_query_refined, response


@router.post("/embeddings-search")
async def embeddings_search(
    user_query: UserQueryBase,
    asession: AsyncSession = Depends(get_async_session),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> UserQueryResponse:
    """
    Embeddings search finds the most similar embeddings to the user query
    from the vector db.
    """
    (
        user_query_db,
        user_query_refined,
        response,
    ) = await get_user_query_and_response(user_query, asession)

    response = await get_semantic_matches(
        user_query_refined, response, qdrant_client, int(QDRANT_N_TOP_SIMILAR)
    )
    await save_query_response_to_db(asession, user_query_db, response)

    return response


@paraphrase_question
@translate_question
async def get_semantic_matches(
    user_query_refined: UserQueryRefined,
    response: UserQueryResponse,
    qdrant_client: QdrantClient,
    n_top_similar: int,
) -> UserQueryResponse:
    """
    Get similar contents from vector db
    """
    if response.state == ResultState.ERROR:
        return response
    content_response = get_similar_content(
        user_query_refined, qdrant_client, n_top_similar
    )
    response.content_response = content_response
    return response


@router.post("/feedback")
async def feedback(
    feedback: FeedbackBase, asession: AsyncSession = Depends(get_async_session)
) -> JSONResponse:
    """
    Feedback endpoint used to capture user feedback on the results returned
    """

    is_matched = await check_secret_key_match(
        feedback.feedback_secret_key, feedback.query_id, asession
    )

    if is_matched is False:
        return JSONResponse(
            status_code=400,
            content={
                "message": f"Secret key does not match query id : {feedback.query_id}"
            },
        )
    else:
        feedback_db = await save_feedback_to_db(asession, feedback)
        return JSONResponse(
            status_code=200,
            content={
                "message": (
                    f"Added Feedback: {feedback_db.feedback_id} "
                    f"for Query: {feedback_db.query_id}"
                )
            },
        )


def generate_secret_key() -> str:
    """
    Generate a secret key for the user query
    """
    return uuid4().hex
