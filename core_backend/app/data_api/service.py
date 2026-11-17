"""Business logic for the data API: fetch workspace records and convert them to
the export schemas."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.contents.models import ContentDB
from app.contents.schemas import ContentRetrieve
from app.data_api.repository import (
    get_contents_with_tags,
    get_queries_with_children,
    get_urgency_queries_with_response,
    get_urgency_rules_for_workspace,
)
from app.data_api.schemas import (
    ContentFeedbackExtract,
    QueryExtract,
    QueryResponseExtract,
    ResponseFeedbackExtract,
    UrgencyQueryExtract,
    UrgencyQueryResponseExtract,
)
from app.question_answer.models import QueryDB
from app.urgency_detection.models import UrgencyQueryDB
from app.urgency_rules.schemas import UrgencyRuleRetrieve


async def get_workspace_contents(
    *, asession: AsyncSession, workspace_id: int
) -> list[ContentRetrieve]:
    """Get all contents for a workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_id
        The ID of the workspace to get contents for.

    Returns
    -------
    list[ContentRetrieve]
        All contents in the workspace.
    """

    contents = await get_contents_with_tags(
        asession=asession, workspace_id=workspace_id
    )
    return [convert_content_to_pydantic_model(content=content) for content in contents]


async def get_workspace_urgency_rules(
    *, asession: AsyncSession, workspace_id: int
) -> list[UrgencyRuleRetrieve]:
    """Get all urgency rules for a workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_id
        The ID of the workspace to get urgency rules for.

    Returns
    -------
    list[UrgencyRuleRetrieve]
        All urgency rules in the workspace.
    """

    urgency_rules = await get_urgency_rules_for_workspace(
        asession=asession, workspace_id=workspace_id
    )
    return [
        UrgencyRuleRetrieve.model_validate(urgency_rule)
        for urgency_rule in urgency_rules
    ]


async def get_workspace_queries(
    *,
    asession: AsyncSession,
    end_date: datetime,
    start_date: datetime,
    workspace_id: int,
) -> list[QueryExtract]:
    """Get all queries, with child records, for a workspace between two dates.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    end_date
        The end date to filter queries by. Treated as UTC.
    start_date
        The start date to filter queries by. Treated as UTC.
    workspace_id
        The ID of the workspace to get queries for.

    Returns
    -------
    list[QueryExtract]
        The queries in the date range.
    """

    # The API documents its datetimes as UTC, so pin the timezone (overriding any
    # offset the client sent) before comparing against stored UTC timestamps.
    start_date = start_date.replace(tzinfo=timezone.utc)
    end_date = end_date.replace(tzinfo=timezone.utc)

    queries = await get_queries_with_children(
        asession=asession,
        end_date=end_date,
        start_date=start_date,
        workspace_id=workspace_id,
    )
    return [convert_query_to_pydantic_model(query=query) for query in queries]


async def get_workspace_urgency_queries(
    *,
    asession: AsyncSession,
    end_date: datetime,
    start_date: datetime,
    workspace_id: int,
) -> list[UrgencyQueryExtract]:
    """Get all urgency queries, with responses, for a workspace between two dates.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    end_date
        The end date to filter urgency queries by. Treated as UTC.
    start_date
        The start date to filter urgency queries by. Treated as UTC.
    workspace_id
        The ID of the workspace to get urgency queries for.

    Returns
    -------
    list[UrgencyQueryExtract]
        The urgency queries in the date range.
    """

    # See `get_workspace_queries`: the API's datetimes are always interpreted as UTC.
    start_date = start_date.replace(tzinfo=timezone.utc)
    end_date = end_date.replace(tzinfo=timezone.utc)

    urgency_queries = await get_urgency_queries_with_response(
        asession=asession,
        end_date=end_date,
        start_date=start_date,
        workspace_id=workspace_id,
    )
    return [
        convert_urgency_query_to_pydantic_model(query=query)
        for query in urgency_queries
    ]


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
        display_number=content.display_number,
        is_archived=content.is_archived,
        negative_votes=content.negative_votes,
        positive_votes=content.positive_votes,
        updated_datetime_utc=content.updated_datetime_utc,
        workspace_id=content.workspace_id,
    )


def convert_urgency_query_to_pydantic_model(
    *, query: UrgencyQueryDB
) -> UrgencyQueryExtract:
    """Convert a `UrgencyQueryDB` object to a `UrgencyQueryExtract` object.

    Parameters
    ----------
    query
        The `UrgencyQueryDB` object to convert.

    Returns
    -------
    UrgencyQueryExtract
        The converted `UrgencyQueryExtract` object.
    """

    return UrgencyQueryExtract(
        message_datetime_utc=query.message_datetime_utc,
        message_text=query.message_text,
        response=(
            UrgencyQueryResponseExtract.model_validate(query.response)
            if query.response
            else None
        ),
        urgency_query_id=query.urgency_query_id,
        workspace_id=query.workspace_id,
    )


def convert_query_to_pydantic_model(*, query: QueryDB) -> QueryExtract:
    """Convert a `QueryDB` object to a `QueryExtract` object.

    Parameters
    ----------
    query
        The `QueryDB` object to convert.

    Returns
    -------
    QueryExtract
        The converted `QueryExtract` object.
    """

    return QueryExtract(
        content_feedback=[
            ContentFeedbackExtract.model_validate(feedback)
            for feedback in query.content_feedback
        ],
        query_datetime_utc=query.query_datetime_utc,
        query_id=query.query_id,
        query_metadata=query.query_metadata,
        query_text=query.query_text,
        response=[
            QueryResponseExtract.model_validate(response) for response in query.response
        ],
        response_feedback=[
            ResponseFeedbackExtract.model_validate(feedback)
            for feedback in query.response_feedback
        ],
        workspace_id=query.workspace_id,
    )
