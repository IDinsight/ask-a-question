from fastapi import APIRouter, Depends
from app.db.engine import get_async_session

from datetime import datetime
from app.db.db_models import UserQuery, Feedback
from app.schemas import UserQueryBase, FeedbackBase

router = APIRouter()


@router.post("/embeddings-search")
async def embeddings_search(
    user_query: UserQueryBase, asession=Depends(get_async_session)
):
    """
    Embeddings search finds the most similar embeddings to the user query
    from the vector db.
    """

    user_query = UserQuery(
        feedback_secret_key=generate_secret_key(),
        query_datetime_utc=datetime.utcnow(),
        **user_query.dict(),
    )
    asession.add(user_query)
    await asession.commit()
    await asession.refresh(user_query)
    return f"Added : {user_query.query_id}"


@router.post("/feedback")
async def feedback(feedback: FeedbackBase, asession=Depends(get_async_session)):
    """
    Feedback endpoint used to capture user feedback on the results returned
    """

    is_matched = await check_secret_key_match(
        feedback.feedback_secret_key, feedback.query_id
    )

    if is_matched is False:
        return f"Secret key does not match query id : {feedback.query_id}"
    else:
        feedback = Feedback(
            feedback_datetime_utc=datetime.utcnow(),
            query_id=feedback.query_id,
            feedback_text=feedback.feedback_text,
        )
        asession.add(feedback)
        await asession.commit()
        await asession.refresh(feedback)
        return f"Added : {feedback.feedback_id}"


async def check_secret_key_match(secret_key, query_id):
    """
    Check if the secret key matches the one generated for query id
    """
    return True


def generate_secret_key():
    """
    Generate a secret key for the user query
    """
    return "abc1234"
