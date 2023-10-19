from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import auth_bearer_token
from ..configs.app_config import QDRANT_N_TOP_SIMILAR
from ..db.db_models import (
    check_secret_key_match,
    save_feedback_to_db,
    save_query_response_to_db,
    save_user_query_to_db,
)
from ..db.engine import get_async_session
from ..db.vector_db import get_qdrant_client, get_similar_content
from ..schemas import FeedbackBase, UserQueryBase, UserQueryResponse

router = APIRouter(dependencies=[Depends(auth_bearer_token)])


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

    feedback_secret_key = generate_secret_key()

    # add to query database
    user_query_db = await save_user_query_to_db(
        asession, feedback_secret_key, user_query
    )

    # get FAQs from vector db
    responses = UserQueryResponse(
        query_id=user_query_db.query_id,
        responses=get_similar_content(
            user_query, qdrant_client, int(QDRANT_N_TOP_SIMILAR)
        ),
        feedback_secret_key=feedback_secret_key,
    )

    # add FAQs to responses database
    await save_query_response_to_db(asession, user_query_db, responses)

    # repond to user
    return responses


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
