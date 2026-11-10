"""Tests for the urgency detection repository against a real Postgres database.

Every test runs inside `rollback_asession`, so the rows written here are rolled
back when the test ends and no clean-up is needed.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.urgency_detection.models import UrgencyQueryDB
from app.urgency_detection.repository import (
    check_secret_key_match,
    save_urgency_query_to_db,
    save_urgency_response_to_db,
)
from app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse
from app.urgency_rules.schemas import UrgencyRuleCosineDistance
from app.workspaces.models import WorkspaceDB

SECRET_KEY = "feedback-secret"  # pragma: allowlist secret


@pytest.fixture
async def workspace_id(rollback_asession: AsyncSession) -> int:
    """Create a throwaway workspace inside the rolled-back transaction.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.

    Returns
    -------
    int
        The new workspace ID.
    """

    now = datetime.now(timezone.utc)
    workspace_db = WorkspaceDB(
        created_datetime_utc=now,
        doc_language="ENGLISH",
        updated_datetime_utc=now,
        workspace_name="urgency_detection_repository_workspace",
    )
    rollback_asession.add(workspace_db)
    await rollback_asession.flush()
    return workspace_db.workspace_id


@pytest.fixture
async def urgency_query_db(
    rollback_asession: AsyncSession, workspace_id: int
) -> UrgencyQueryDB:
    """Save an urgency query in the throwaway workspace.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_id
        The throwaway workspace ID.

    Returns
    -------
    UrgencyQueryDB
        The saved urgency query.
    """

    return await save_urgency_query_to_db(
        asession=rollback_asession,
        feedback_secret_key=SECRET_KEY,
        urgency_query=UrgencyQuery(message_text="I have a fever"),
        workspace_id=workspace_id,
    )


async def test_save_urgency_query_to_db(
    urgency_query_db: UrgencyQueryDB, workspace_id: int
) -> None:
    """The query is stored with an ID and a UTC timestamp.

    Parameters
    ----------
    urgency_query_db
        The saved urgency query.
    workspace_id
        The throwaway workspace ID.
    """

    assert urgency_query_db.urgency_query_id is not None
    assert urgency_query_db.message_text == "I have a fever"
    assert urgency_query_db.feedback_secret_key == SECRET_KEY
    assert urgency_query_db.workspace_id == workspace_id
    assert urgency_query_db.message_datetime_utc.tzinfo is not None
    assert "message_text=I have a fever" in repr(urgency_query_db)


@pytest.mark.parametrize(
    "secret_key, query_id_offset, expected",
    [(SECRET_KEY, 0, True), ("wrong-key", 0, False), (SECRET_KEY, 1000, False)],
    ids=["match", "wrong_key", "unknown_query"],
)
async def test_check_secret_key_match(
    expected: bool,
    query_id_offset: int,
    rollback_asession: AsyncSession,
    secret_key: str,
    urgency_query_db: UrgencyQueryDB,
) -> None:
    """Only the key generated for an existing query matches.

    Parameters
    ----------
    expected
        The expected match result.
    query_id_offset
        Added to the saved query ID; non-zero points at a query that does not exist.
    rollback_asession
        Async session that is rolled back on teardown.
    secret_key
        The key to check.
    urgency_query_db
        The saved urgency query.
    """

    assert (
        await check_secret_key_match(
            secret_key=secret_key,
            query_id=urgency_query_db.urgency_query_id + query_id_offset,
            asession=rollback_asession,
        )
        is expected
    )


async def test_save_urgency_response_to_db(
    rollback_asession: AsyncSession, urgency_query_db: UrgencyQueryDB
) -> None:
    """The response is linked to its query and workspace, with details as JSON.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.
    urgency_query_db
        The saved urgency query.
    """

    response = UrgencyResponse(
        details={0: UrgencyRuleCosineDistance(distance=0.2, urgency_rule="fever")},
        is_urgent=True,
        matched_rules=["fever"],
    )

    response_db = await save_urgency_response_to_db(
        asession=rollback_asession,
        response=response,
        urgency_query_db=urgency_query_db,
    )

    assert response_db.urgency_response_id is not None
    assert response_db.query_id == urgency_query_db.urgency_query_id
    assert response_db.workspace_id == urgency_query_db.workspace_id
    assert response_db.is_urgent is True
    assert response_db.matched_rules == ["fever"]
    # JSON round-trip turns the integer key into a string.
    assert response_db.details == {"0": {"distance": 0.2, "urgency_rule": "fever"}}
    assert "is_urgent=True" in repr(response_db)
