"""This module contains the ORM for managing urgency detection queries in the
`UrgencyQueryDB` database and functions for interacting with the database.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.urgency_detection.models import UrgencyQueryDB, UrgencyResponseDB
from app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse


async def save_urgency_query_to_db(
    *,
    asession: AsyncSession,
    feedback_secret_key: str,
    urgency_query: UrgencyQuery,
    workspace_id: int,
) -> UrgencyQueryDB:
    """Save an urgent user query to the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    feedback_secret_key
        The secret key for the feedback.
    urgency_query
        The urgency query to save to the database.
    workspace_id
        The ID of the workspace to save the urgent user query to.

    Returns
    -------
    UrgencyQueryDB
        The urgency query object that was saved to the database.
    """

    urgency_query_db = UrgencyQueryDB(
        feedback_secret_key=feedback_secret_key,
        message_datetime_utc=datetime.now(timezone.utc),
        workspace_id=workspace_id,
        **urgency_query.model_dump(),
    )
    asession.add(urgency_query_db)
    await asession.commit()
    await asession.refresh(urgency_query_db)
    return urgency_query_db


async def check_secret_key_match(
    secret_key: str, query_id: int, asession: AsyncSession
) -> bool:
    """Check if the secret key matches the one generated for the query ID.

    Parameters
    ----------
    secret_key
        The key to check.
    query_id
        The ID of the query to check.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    bool
        `True` if the secret key matches the one generated for the query ID, `False`
        otherwise.
    """

    stmt = select(UrgencyQueryDB.feedback_secret_key).where(
        UrgencyQueryDB.urgency_query_id == query_id
    )
    query_record = (await asession.execute(stmt)).first()
    return (query_record is not None) and (query_record[0] == secret_key)


async def save_urgency_response_to_db(
    *,
    asession: AsyncSession,
    response: UrgencyResponse,
    urgency_query_db: UrgencyQueryDB,
) -> UrgencyResponseDB:
    """Saves the urgent user query response to the database.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    response
        The urgency response object to save to the database.
    urgency_query_db
        The urgency query database object.

    Returns
    -------
    UrgencyResponseDB
        The urgency response object that was saved to the database.
    """

    urgency_query_responses_db = UrgencyResponseDB(
        details=response.model_dump()["details"],
        is_urgent=response.is_urgent,
        matched_rules=response.matched_rules,
        query_id=urgency_query_db.urgency_query_id,
        response_datetime_utc=datetime.now(timezone.utc),
        workspace_id=urgency_query_db.workspace_id,
    )
    asession.add(urgency_query_responses_db)
    await asession.commit()
    await asession.refresh(urgency_query_responses_db)
    return urgency_query_responses_db
