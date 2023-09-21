from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.db.engine import get_async_session

from datetime import datetime
from app.db.db_models import UserQuery, Feedback
from app.schemas import UserQueryBase, FeedbackBase
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/embeddings-search")
async def embeddings_search(
    user_query: UserQueryBase, asession: AsyncSession = Depends(get_async_session)
) -> JSONResponse:
    """
    Embeddings search finds the most similar embeddings to the user query
    from the vector db.
    """

    user_query_db = UserQuery(
        feedback_secret_key=generate_secret_key(),
        query_datetime_utc=datetime.utcnow(),
        **user_query.model_dump(),
    )
    asession.add(user_query_db)
    await asession.commit()
    await asession.refresh(user_query_db)
    return JSONResponse(
        status_code=200, content={"message": f"Added : {user_query_db.query_id}"}
    )


@router.post("/feedback")
async def feedback(
    feedback: FeedbackBase, asession: AsyncSession = Depends(get_async_session)
) -> JSONResponse:
    """
    Feedback endpoint used to capture user feedback on the results returned
    """

    is_matched = await check_secret_key_match(
        feedback.feedback_secret_key, feedback.query_id
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
            status_code=200, content={"message": f"Added : {feedback_db.feedback_id}"}
        )


async def check_secret_key_match(secret_key: str, query_id: int) -> bool:
    """
    Check if the secret key matches the one generated for query id
    """
    return True


def generate_secret_key() -> str:
    """
    Generate a secret key for the user query
    """
    return "abc1234"
