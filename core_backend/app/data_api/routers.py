from datetime import date, datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..auth.dependencies import authenticate_key
from ..database import get_async_session
from ..question_answer.models import QueryDB
from ..users.models import UserDB
from ..utils import setup_logger
from .schemas import (
    ContentFeedbackExtract,
    QueryExtract,
    QueryResponseErrorExtract,
    QueryResponseExtract,
    ResponseFeedbackExtract,
)

logger = setup_logger()

router = APIRouter(
    prefix="/data-api",
    dependencies=[Depends(authenticate_key)],
    tags=["Data API"],
)


@router.get("/queries", response_model=List[QueryExtract])
async def get_queries(
    start_date: Annotated[
        datetime | date,
        Query(
            description=(
                "Can be date or UTC datetime. "
                "Example: `2021-01-01` or `2021-01-01T00:00:00`"
            ),
        ),
    ],
    end_date: Annotated[
        datetime | date,
        Query(
            description=(
                "Can be date or UTC datetime. "
                "Example: `2021-01-01` or `2021-01-01T00:00:00`"
            ),
        ),
    ],
    user_db: Annotated[UserDB, Depends(authenticate_key)],
    asession: AsyncSession = Depends(get_async_session),
) -> List[QueryExtract]:
    """
    Get all queries including child records for a user between a start and end date.

    Note that the `start_date` and `end_date` can be provided as a date
    or datetime object.

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


def convert_to_pydantic_model(query: QueryDB) -> QueryExtract:
    """
    Convert a QueryDB object to a QueryExtract object
    """

    return QueryExtract(
        query_id=query.query_id,
        user_id=query.user_id,
        query_text=query.query_text,
        query_metadata=query.query_metadata,
        query_datetime_utc=query.query_datetime_utc,
        response=(
            QueryResponseExtract(
                response_id=query.response[0].response_id,
                search_results=query.response[0].search_results,
                llm_response=query.response[0].llm_response,
                response_datetime_utc=query.response[0].response_datetime_utc,
            )
            if query.response
            else None
        ),
        response_error=(
            QueryResponseErrorExtract(
                error_id=query.response_error[0].error_id,
                error_message=query.response_error[0].error_message,
                error_type=query.response_error[0].error_type,
                error_datetime_utc=query.response_error[0].error_datetime_utc,
            )
            if query.response_error
            else None
        ),
        response_feedback=[
            ResponseFeedbackExtract(
                feedback_id=feedback.feedback_id,
                feedback_sentiment=feedback.feedback_sentiment,
                feedback_text=feedback.feedback_text,
                feedback_datetime_utc=feedback.feedback_datetime_utc,
            )
            for feedback in query.response_feedback
        ],
        content_feedback=[
            ContentFeedbackExtract(
                feedback_id=feedback.feedback_id,
                feedback_sentiment=feedback.feedback_sentiment,
                feedback_text=feedback.feedback_text,
                feedback_datetime_utc=feedback.feedback_datetime_utc,
                content_id=feedback.content_id,
            )
            for feedback in query.content_feedback
        ],
    )
