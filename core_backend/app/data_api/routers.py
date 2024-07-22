from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..auth.dependencies import authenticate_key
from ..database import get_async_session
from ..question_answer.models import QueryDB
from ..users.models import UserDB
from ..utils import setup_logger
from .schemas import (
    ContentFeedbackModel,
    QueryModel,
    QueryResponseErrorModel,
    QueryResponseModel,
    ResponseFeedbackModel,
)

logger = setup_logger()

router = APIRouter(
    prefix="/data-api",
    dependencies=[Depends(authenticate_key)],
    tags=["Data API"],
)


@router.get("/queries", response_model=List[QueryModel])
async def get_queries(
    start_date: datetime,
    end_date: datetime,
    user_db: Annotated[UserDB, Depends(authenticate_key)],
    asession: AsyncSession = Depends(get_async_session),
) -> List[QueryModel]:
    """
    Get all queries including child records for a user between a start and end date
    """

    result = await asession.execute(
        select(QueryDB)
        .filter(QueryDB.query_datetime_utc.between(start_date, end_date))
        .filter(QueryDB.user_id == user_db.user_id)
        .options(
            joinedload(QueryDB.response_feedback),
            joinedload(QueryDB.content_feedback),
            joinedload(QueryDB.response),
            joinedload(QueryDB.response_error),
        )
    )
    queries = result.unique().scalars().all()
    queries_responses = [convert_to_pydantic_model(query) for query in queries]

    return queries_responses


def convert_to_pydantic_model(query: QueryDB) -> QueryModel:
    """
    Convert a QueryDB object to a QueryModel object
    """

    return QueryModel(
        query_id=query.query_id,
        user_id=query.user_id,
        query_text=query.query_text,
        query_metadata=query.query_metadata,
        query_datetime_utc=query.query_datetime_utc,
        response=(
            QueryResponseModel(
                response_id=query.response[0].response_id,
                content_response=query.response[0].content_response,
                llm_response=query.response[0].llm_response,
                response_datetime_utc=query.response[0].response_datetime_utc,
            )
            if query.response
            else None
        ),
        response_error=(
            QueryResponseErrorModel(
                error_id=query.response_error[0].error_id,
                error_message=query.response_error[0].error_message,
                error_type=query.response_error[0].error_type,
                error_datetime_utc=query.response_error[0].error_datetime_utc,
            )
            if query.response_error
            else None
        ),
        response_feedback=[
            ResponseFeedbackModel(
                feedback_id=feedback.feedback_id,
                feedback_sentiment=feedback.feedback_sentiment,
                feedback_text=feedback.feedback_text,
                feedback_datetime_utc=feedback.feedback_datetime_utc,
            )
            for feedback in query.response_feedback
        ],
        content_feedback=[
            ContentFeedbackModel(
                feedback_id=feedback.feedback_id,
                feedback_sentiment=feedback.feedback_sentiment,
                feedback_text=feedback.feedback_text,
                feedback_datetime_utc=feedback.feedback_datetime_utc,
                content_id=feedback.content_id,
            )
            for feedback in query.content_feedback
        ],
    )
