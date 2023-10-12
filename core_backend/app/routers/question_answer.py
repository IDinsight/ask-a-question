from datetime import datetime
from typing import Dict
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from litellm import embedding
from qdrant_client import QdrantClient, models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import auth_bearer_token
from ..configs.app_config import (
    EMBEDDING_MODEL,
    QDRANT_COLLECTION_NAME,
    QDRANT_N_TOP_SIMILAR,
)
from ..db.db_models import Feedback, UserQuery, UserQueryResponsesDB
from ..db.engine import get_async_session
from ..db.vector_db import get_qdrant_client
from ..schemas import (
    FeedbackBase,
    UserQueryBase,
    UserQueryResponse,
    UserQuerySearchResult,
)

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

    # add to query database
    feedback_secret_key = generate_secret_key()
    user_query_db = UserQuery(
        feedback_secret_key=feedback_secret_key,
        query_datetime_utc=datetime.utcnow(),
        **user_query.model_dump(),
    )
    asession.add(user_query_db)
    await asession.commit()
    await asession.refresh(user_query_db)

    # get FAQs from vector db
    responses = UserQueryResponse(
        query_id=user_query_db.query_id,
        responses=get_similar_content(
            user_query, qdrant_client, int(QDRANT_N_TOP_SIMILAR)
        ),
        feedback_secret_key=feedback_secret_key,
    )

    # add FAQs to responses database
    user_query_responses_db = UserQueryResponsesDB(
        query_id=user_query_db.query_id,
        responses="HELLO",  # responses.dict()["responses"]
        response_datetime_utc=datetime.utcnow(),
    )
    asession.add(user_query_responses_db)
    await asession.commit()
    await asession.refresh(user_query_responses_db)

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
        feedback_db = Feedback(
            feedback_datetime_utc=datetime.utcnow(),
            query_id=feedback.query_id,
            feedback_text=feedback.feedback_text,
        )
        asession.add(feedback_db)
        await asession.commit()
        await asession.refresh(feedback_db)
        return JSONResponse(
            status_code=200,
            content={
                "message": (
                    f"Added Feedback: {feedback_db.feedback_id} "
                    f"for Query: {feedback_db.query_id}"
                )
            },
        )


async def check_secret_key_match(
    secret_key: str, query_id: int, asession: AsyncSession
) -> bool:
    """
    Check if the secret key matches the one generated for query id
    """
    stmt = select(UserQuery.feedback_secret_key).where(UserQuery.query_id == query_id)
    query_record = (await asession.execute(stmt)).first()

    if (query_record is not None) and (query_record[0] == secret_key):
        return True
    else:
        return False


def generate_secret_key() -> str:
    """
    Generate a secret key for the user query
    """
    return uuid4().hex


def get_similar_content(
    question: UserQueryBase,
    qdrant_client: QdrantClient,
    n_similar: int,
) -> Dict[int, UserQuerySearchResult]:
    """
    Get the most similar points in the vector db
    """

    question_embedding = (
        embedding(EMBEDDING_MODEL, question.query_text).data[0].embedding
    )

    search_result = qdrant_client.search(
        collection_name=QDRANT_COLLECTION_NAME,
        query_vector=question_embedding,
        limit=n_similar,
        with_payload=models.PayloadSelectorInclude(include=["content_text"]),
    )

    results_dict = {}
    for i, r in enumerate(search_result):
        if r.payload is None:
            raise ValueError("Payload is empty. No content text found.")
        else:
            results_dict[i] = UserQuerySearchResult(
                response_text=r.payload.get("content_text", ""),
                score=r.score,
            )

    return results_dict
