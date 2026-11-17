"""Tests for `app.data_api.repository`, run against Postgres in a rolled-back
transaction (`rollback_asession`).

Every test writes into a workspace it creates itself, so results are not affected
by rows other tests left in the shared workspaces.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contents.models import ContentDB
from app.core.config import PGVECTOR_VECTOR_SIZE
from app.data_api.repository import (
    get_contents_with_tags,
    get_queries_with_children,
    get_urgency_queries_with_response,
    get_urgency_rules_for_workspace,
)
from app.question_answer.models import (
    ContentFeedbackDB,
    QueryDB,
    QueryResponseDB,
    ResponseFeedbackDB,
)
from app.tags.models import TagDB
from app.urgency_detection.models import UrgencyQueryDB, UrgencyResponseDB
from app.urgency_rules.models import UrgencyRuleDB
from app.workspaces.models import WorkspaceDB

NOW = datetime.now(timezone.utc)
START = NOW - timedelta(days=7)
VECTOR = [0.0] * int(PGVECTOR_VECTOR_SIZE)


async def add_workspace(asession: AsyncSession) -> int:
    """Insert an empty workspace.

    Parameters
    ----------
    asession
        The session to insert with.

    Returns
    -------
    int
        The new workspace's ID.
    """

    workspace = WorkspaceDB(
        created_datetime_utc=NOW,
        doc_language="ENGLISH",
        updated_datetime_utc=NOW,
        workspace_name=f"data_api_repo_{uuid.uuid4().hex[:8]}",
    )
    asession.add(workspace)
    await asession.flush()
    return workspace.workspace_id


@pytest.fixture
async def workspace_ids(rollback_asession: AsyncSession) -> tuple[int, int]:
    """Create two empty workspaces visible only to this test.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.

    Returns
    -------
    tuple[int, int]
        The IDs of the workspace under test and of another workspace.
    """

    return (
        await add_workspace(rollback_asession),
        await add_workspace(rollback_asession),
    )


async def test_contents_with_tags(
    rollback_asession: AsyncSession, workspace_ids: tuple[int, int]
) -> None:
    """Contents come back once each, with tags loaded, for the workspace only.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.
    workspace_ids
        The workspace under test and another workspace.
    """

    workspace_id, other_id = workspace_ids
    tags = [
        TagDB(
            created_datetime_utc=NOW,
            tag_name=name,
            updated_datetime_utc=NOW,
            workspace_id=workspace_id,
        )
        for name in ("A", "B")
    ]
    for owner, title, content_tags in [
        (workspace_id, "tagged", tags),
        (workspace_id, "untagged", []),
        (other_id, "other", []),
    ]:
        rollback_asession.add(
            ContentDB(
                content_embedding=VECTOR,
                content_metadata={},
                content_tags=content_tags,
                content_text="text",
                content_title=title,
                created_datetime_utc=NOW,
                updated_datetime_utc=NOW,
                workspace_id=owner,
            )
        )
    await rollback_asession.flush()
    # Drop the identity map so relationships must be loaded by the query itself.
    rollback_asession.expunge_all()

    contents = await get_contents_with_tags(
        asession=rollback_asession, workspace_id=workspace_id
    )

    # The joined tag rows must not duplicate the tagged content.
    by_title = {
        c.content_title: sorted(t.tag_name for t in c.content_tags) for c in contents
    }
    assert by_title == {"tagged": ["A", "B"], "untagged": []}


async def test_urgency_rules_for_workspace(
    rollback_asession: AsyncSession, workspace_ids: tuple[int, int]
) -> None:
    """Only the workspace's own urgency rules are returned.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.
    workspace_ids
        The workspace under test and another workspace.
    """

    workspace_id, other_id = workspace_ids
    rollback_asession.add_all(
        UrgencyRuleDB(
            created_datetime_utc=NOW,
            updated_datetime_utc=NOW,
            urgency_rule_metadata={},
            urgency_rule_text=text,
            urgency_rule_vector=VECTOR,
            workspace_id=owner,
        )
        for owner, text in [(workspace_id, "mine"), (other_id, "theirs")]
    )
    await rollback_asession.flush()

    rules = await get_urgency_rules_for_workspace(
        asession=rollback_asession, workspace_id=workspace_id
    )

    assert [r.urgency_rule_text for r in rules] == ["mine"]


async def test_queries_with_children(
    rollback_asession: AsyncSession, workspace_ids: tuple[int, int]
) -> None:
    """Queries in the window come back once each with all child records loaded.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.
    workspace_ids
        The workspace under test and another workspace.
    """

    workspace_id, other_id = workspace_ids
    content = ContentDB(
        content_embedding=VECTOR,
        content_metadata={},
        content_text="text",
        content_title="title",
        created_datetime_utc=NOW,
        updated_datetime_utc=NOW,
        workspace_id=workspace_id,
    )
    queries = {
        text: QueryDB(
            feedback_secret_key="abc123",
            query_datetime_utc=when,
            query_generate_llm_response=False,
            query_metadata={},
            query_text=text,
            workspace_id=owner,
        )
        for text, when, owner in [
            ("in window", NOW - timedelta(days=1), workspace_id),
            ("too old", NOW - timedelta(days=30), workspace_id),
            ("other workspace", NOW - timedelta(days=1), other_id),
        ]
    }
    rollback_asession.add_all([content, *queries.values()])
    await rollback_asession.flush()

    query = queries["in window"]
    # Two children of each kind, so a missing `unique()` would duplicate the query.
    for i in range(2):
        rollback_asession.add_all(
            [
                QueryResponseDB(
                    debug_info={},
                    is_error=False,
                    llm_response=f"answer {i}",
                    query_id=query.query_id,
                    response_datetime_utc=NOW,
                    search_results={},
                    workspace_id=workspace_id,
                ),
                ResponseFeedbackDB(
                    feedback_datetime_utc=NOW,
                    feedback_sentiment="positive",
                    query_id=query.query_id,
                    workspace_id=workspace_id,
                ),
                ContentFeedbackDB(
                    content_id=content.content_id,
                    feedback_datetime_utc=NOW,
                    feedback_sentiment="negative",
                    query_id=query.query_id,
                    workspace_id=workspace_id,
                ),
            ]
        )
    await rollback_asession.flush()
    rollback_asession.expunge_all()

    [result] = await get_queries_with_children(
        asession=rollback_asession,
        end_date=NOW,
        start_date=START,
        workspace_id=workspace_id,
    )

    assert result.query_text == "in window"
    assert len(result.response) == 2
    assert len(result.response_feedback) == 2
    assert len(result.content_feedback) == 2


async def test_urgency_queries_with_response(
    rollback_asession: AsyncSession, workspace_ids: tuple[int, int]
) -> None:
    """Urgency queries in the window are returned with their response, if any.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.
    workspace_ids
        The workspace under test and another workspace.
    """

    workspace_id, other_id = workspace_ids
    queries = {
        text: UrgencyQueryDB(
            feedback_secret_key="abc123",
            message_datetime_utc=when,
            message_text=text,
            workspace_id=owner,
        )
        for text, when, owner in [
            ("answered", NOW - timedelta(days=1), workspace_id),
            ("pending", NOW - timedelta(days=2), workspace_id),
            ("too old", NOW - timedelta(days=30), workspace_id),
            ("other workspace", NOW - timedelta(days=1), other_id),
        ]
    }
    rollback_asession.add_all(queries.values())
    await rollback_asession.flush()
    rollback_asession.add(
        UrgencyResponseDB(
            details={},
            is_urgent=True,
            matched_rules=["rule"],
            query_id=queries["answered"].urgency_query_id,
            response_datetime_utc=NOW,
            workspace_id=workspace_id,
        )
    )
    await rollback_asession.flush()
    rollback_asession.expunge_all()

    results = await get_urgency_queries_with_response(
        asession=rollback_asession,
        end_date=NOW,
        start_date=START,
        workspace_id=workspace_id,
    )

    responses = {r.message_text: r.response for r in results}
    assert set(responses) == {"answered", "pending"}
    assert responses["answered"].is_urgent is True
    assert responses["pending"] is None
