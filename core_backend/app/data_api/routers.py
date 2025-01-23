"""This module contains FastAPI routers for data API endpoints."""

from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..auth.dependencies import authenticate_key
from ..contents.models import ContentDB
from ..contents.schemas import ContentRetrieve
from ..database import get_async_session
from ..question_answer.models import QueryDB
from ..urgency_detection.models import UrgencyQueryDB
from ..urgency_rules.models import UrgencyRuleDB
from ..urgency_rules.schemas import UrgencyRuleRetrieve
from ..users.models import (
    UserDB,
    get_user_workspaces,
    user_has_required_role_in_workspace,
)
from ..users.schemas import UserRoles
from ..utils import setup_logger
from .schemas import (
    ContentFeedbackExtract,
    QueryExtract,
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


@router.get("/contents", response_model=list[ContentRetrieve])
async def get_contents(
    user_db: Annotated[UserDB, Depends(authenticate_key)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[ContentRetrieve]:
    """Get all contents for a user.

    Parameters
    ----------
    user_db
        The user object associated with the user retrieving the contents.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[ContentRetrieve]
        A list of ContentRetrieve objects containing all contents for the user.

    Raises
    ------
    HTTPException
        If the user is not in exactly one workspace.
        If the user does not have the correct user role to retrieve contents in the
        workspace.
    """

    user_workspaces = await get_user_workspaces(asession=asession, user_db=user_db)
    if len(user_workspaces) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be in exactly one workspace to retrieve contents.",
        )

    workspace_db = user_workspaces[0]

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN, UserRoles.READ_ONLY],
        asession=asession,
        user_db=user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must have a user role in the workspace to retrieve contents.",
        )


    result = await asession.execute(
        select(ContentDB)
        .filter(ContentDB.workspace_id == workspace_db.workspace_id)
        .options(
            joinedload(ContentDB.content_tags),
        )
    )
    contents = result.unique().scalars().all()
    contents_responses = [
        convert_content_to_pydantic_model(content=content) for content in contents
    ]

    return contents_responses


def convert_content_to_pydantic_model(*, content: ContentDB) -> ContentRetrieve:
    """Convert a `ContentDB` object to a `ContentRetrieve` object.

    Parameters
    ----------
    content
        The `ContentDB` object to convert.

    Returns
    -------
    ContentRetrieve
        The converted `ContentRetrieve` object.
    """

    return ContentRetrieve(
        content_id=content.content_id,
        content_metadata=content.content_metadata,
        content_tags=[content_tag.tag_name for content_tag in content.content_tags],
        content_text=content.content_text,
        content_title=content.content_title,
        created_datetime_utc=content.created_datetime_utc,
        is_archived=content.is_archived,
        negative_votes=content.negative_votes,
        positive_votes=content.positive_votes,
        updated_datetime_utc=content.updated_datetime_utc,
        workspace_id=content.workspace_id,
    )


@router.get("/urgency-rules", response_model=list[UrgencyRuleRetrieve])
async def get_urgency_rules(
    user_db: Annotated[UserDB, Depends(authenticate_key)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[UrgencyRuleRetrieve]:
    """
    Get all urgency rules for a user.
    """

    result = await asession.execute(
        select(UrgencyRuleDB).filter(UrgencyRuleDB.user_id == user_db.user_id)
    )
    urgency_rules = result.unique().scalars().all()
    urgency_rules_responses = [
        UrgencyRuleRetrieve.model_validate(urgency_rule)
        for urgency_rule in urgency_rules
    ]

    return urgency_rules_responses


@router.get("/queries", response_model=list[QueryExtract])
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
) -> list[QueryExtract]:
    """
    Get all queries including child records for a user between a start and end date.

    Note that the `start_date` and `end_date` can be provided as a date
    or datetime object.

    """
    if isinstance(start_date, date):
        start_date = datetime.combine(start_date, datetime.min.time())
    if isinstance(end_date, date):
        end_date = datetime.combine(end_date, datetime.max.time())

    start_date = start_date.replace(tzinfo=timezone.utc)
    end_date = end_date.replace(tzinfo=timezone.utc)

    result = await asession.execute(
        select(QueryDB)
        .filter(QueryDB.query_datetime_utc.between(start_date, end_date))
        .filter(QueryDB.user_id == user_db.user_id)
        .options(
            joinedload(QueryDB.response_feedback),
            joinedload(QueryDB.content_feedback),
            joinedload(QueryDB.response),
        )
    )
    queries = result.unique().scalars().all()
    queries_responses = [convert_query_to_pydantic_model(query) for query in queries]

    return queries_responses


@router.get("/urgency-queries", response_model=list[UrgencyQueryExtract])
async def get_urgency_queries(
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
) -> list[UrgencyQueryExtract]:
    """
    Get all urgency queries including child records for a user between
    a start and end date.

    Note that the `start_date` and `end_date` can be provided as a date
    or datetime object.

    """

    if isinstance(start_date, date):
        start_date = datetime.combine(start_date, datetime.min.time())
    if isinstance(end_date, date):
        end_date = datetime.combine(end_date, datetime.max.time())

    start_date = start_date.replace(tzinfo=timezone.utc)
    end_date = end_date.replace(tzinfo=timezone.utc)

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
        response_feedback=[
            ResponseFeedbackExtract.model_validate(feedback)
            for feedback in query.response_feedback
        ],
        content_feedback=[
            ContentFeedbackExtract.model_validate(feedback)
            for feedback in query.content_feedback
        ],
    )
