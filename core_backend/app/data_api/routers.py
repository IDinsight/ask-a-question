from datetime import date, datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..auth.dependencies import authenticate_key
from ..database import get_async_session
from ..question_answer.models import QueryDB
from ..urgency_detection.models import UrgencyQueryDB
from ..users.models import UserDB
from ..utils import setup_logger
from .schemas import (
    ContentFeedbackExtract,
    QueryExtract,
    QueryResponseErrorExtract,
    QueryResponseExtract,
    ResponseFeedbackExtract,
    UrgencyQueryExtract,
    UrgencyQueryResponseExtract,
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
    queries_responses = [convert_query_to_pydantic_model(query) for query in queries]

    return queries_responses


@router.get("/urgency-queries", response_model=List[UrgencyQueryExtract])
async def get_urgency_queries(
    start_date: Annotated[
        datetime | date,
        Query(
            description=(
                "Can be date or datetime. "
                "Example: `2021-01-01` or `2021-01-01T00:00:00`"
            ),
        ),
    ],
    end_date: Annotated[
        datetime | date,
        Query(
            description=(
                "Can be date or datetime. "
                "Example: `2021-01-01` or `2021-01-01T00:00:00`"
            ),
        ),
    ],
    user_db: Annotated[UserDB, Depends(authenticate_key)],
    asession: AsyncSession = Depends(get_async_session),
) -> List[UrgencyQueryExtract]:
    """
    Get all urgency queries including child records for a user between
    a start and end date.

    Note that the `start_date` and `end_date` can be provided as a date
    or datetime object.

    """
    result = await asession.execute(
        select(UrgencyQueryDB)
        .filter(UrgencyQueryDB.message_datetime_utc.between(start_date, end_date))
        .filter(UrgencyQueryDB.user_id == user_db.user_id)
        .options(
            joinedload(UrgencyQueryDB.response),
        )
    )
    urgency_queries = result.unique().scalars().all()
    urgency_queries_responses = [
        convert_urgency_query_to_pydantic_model(query) for query in urgency_queries
    ]

    return urgency_queries_responses


def convert_urgency_query_to_pydantic_model(
    query: UrgencyQueryDB,
) -> UrgencyQueryExtract:
    """
    Convert a UrgencyQueryDB object to a UrgencyQueryExtract object
    """

    return UrgencyQueryExtract(
        urgency_query_id=query.urgency_query_id,
        user_id=query.user_id,
        message_text=query.message_text,
        message_datetime_utc=query.message_datetime_utc,
        response=(
            UrgencyQueryResponseExtract.model_validate(query.response)
            if query.response
            else None
        ),
    )


def convert_query_to_pydantic_model(query: QueryDB) -> QueryExtract:
    """
    Convert a QueryDB object to a QueryExtract object
    """

    return QueryExtract(
        query_id=query.query_id,
        user_id=query.user_id,
        query_text=query.query_text,
        query_metadata=query.query_metadata,
        query_datetime_utc=query.query_datetime_utc,
        response=[
            QueryResponseExtract.model_validate(response) for response in query.response
        ],
        response_error=[
            QueryResponseErrorExtract.model_validate(response_error)
            for response_error in query.response_error
        ],
        response_feedback=[
            ResponseFeedbackExtract.model_validate(feedback)
            for feedback in query.response_feedback
        ],
        content_feedback=[
            ContentFeedbackExtract.model_validate(feedback)
            for feedback in query.content_feedback
        ],
    )
