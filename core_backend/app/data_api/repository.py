"""Database queries for the data API.

Each function returns ORM records (with the child relationships the data API exports
already loaded); conversion to response schemas happens in `app.data_api.service`.
"""

from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.contents.models import ContentDB
from app.question_answer.models import QueryDB
from app.urgency_detection.models import UrgencyQueryDB
from app.urgency_rules.models import UrgencyRuleDB


async def get_contents_with_tags(
    *, asession: AsyncSession, workspace_id: int
) -> Sequence[ContentDB]:
    """Get all contents for a workspace, with their tags loaded.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_id
        The ID of the workspace to get contents for.

    Returns
    -------
    Sequence[ContentDB]
        All contents in the workspace.
    """

    result = await asession.execute(
        select(ContentDB)
        .filter(ContentDB.workspace_id == workspace_id)
        .options(joinedload(ContentDB.content_tags))
    )
    return result.unique().scalars().all()


async def get_urgency_rules_for_workspace(
    *, asession: AsyncSession, workspace_id: int
) -> Sequence[UrgencyRuleDB]:
    """Get all urgency rules for a workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_id
        The ID of the workspace to get urgency rules for.

    Returns
    -------
    Sequence[UrgencyRuleDB]
        All urgency rules in the workspace.
    """

    result = await asession.execute(
        select(UrgencyRuleDB).filter(UrgencyRuleDB.workspace_id == workspace_id)
    )
    return result.unique().scalars().all()


async def get_queries_with_children(
    *,
    asession: AsyncSession,
    end_date: datetime,
    start_date: datetime,
    workspace_id: int,
) -> Sequence[QueryDB]:
    """Get all queries in a date range, with feedback and responses loaded.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    end_date
        The end of the date range (inclusive).
    start_date
        The start of the date range (inclusive).
    workspace_id
        The ID of the workspace to get queries for.

    Returns
    -------
    Sequence[QueryDB]
        The queries in the date range.
    """

    result = await asession.execute(
        select(QueryDB)
        .filter(QueryDB.query_datetime_utc.between(start_date, end_date))
        .filter(QueryDB.workspace_id == workspace_id)
        .options(
            joinedload(QueryDB.response_feedback),
            joinedload(QueryDB.content_feedback),
            joinedload(QueryDB.response),
        )
    )
    return result.unique().scalars().all()


async def get_urgency_queries_with_response(
    *,
    asession: AsyncSession,
    end_date: datetime,
    start_date: datetime,
    workspace_id: int,
) -> Sequence[UrgencyQueryDB]:
    """Get all urgency queries in a date range, with their responses loaded.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    end_date
        The end of the date range (inclusive).
    start_date
        The start of the date range (inclusive).
    workspace_id
        The ID of the workspace to get urgency queries for.

    Returns
    -------
    Sequence[UrgencyQueryDB]
        The urgency queries in the date range.
    """

    result = await asession.execute(
        select(UrgencyQueryDB)
        .filter(UrgencyQueryDB.message_datetime_utc.between(start_date, end_date))
        .filter(UrgencyQueryDB.workspace_id == workspace_id)
        .options(
            joinedload(UrgencyQueryDB.response),
        )
    )
    return result.unique().scalars().all()
