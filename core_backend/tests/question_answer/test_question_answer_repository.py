"""Tests for the question-answer repository against a real Postgres database.

Every test runs inside `rollback_asession`, so the rows written here are rolled
back when the test ends and no clean-up is needed.
"""

from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.contents.models import ContentDB
from app.contents.schemas import QuerySearchResult
from app.core.config import PGVECTOR_VECTOR_SIZE
from app.question_answer.models import QueryDB, QueryResponseContentDB
from app.question_answer.repository import (
    check_secret_key_match,
    save_content_feedback_to_db,
    save_content_for_query_to_db,
    save_query_response_to_db,
    save_response_feedback_to_db,
    save_user_query_to_db,
)
from app.question_answer.schemas import (
    ContentFeedback,
    ErrorType,
    FeedbackSentiment,
    QueryAudioResponse,
    QueryBase,
    QueryResponse,
    QueryResponseError,
    ResponseFeedbackBase,
)
from app.workspaces.models import WorkspaceDB

SESSION_ID = 4242


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
        workspace_name="question_answer_repository_workspace",
    )
    rollback_asession.add(workspace_db)
    await rollback_asession.flush()
    return workspace_db.workspace_id


@pytest.fixture
async def content_id(rollback_asession: AsyncSession, workspace_id: int) -> int:
    """Create a content row in the throwaway workspace.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_id
        The throwaway workspace ID.

    Returns
    -------
    int
        The new content ID.
    """

    now = datetime.now(timezone.utc)
    content_db = ContentDB(
        # The vector values are irrelevant here; only the dimension must match.
        content_embedding=[0.1] * int(PGVECTOR_VECTOR_SIZE),
        content_metadata={},
        content_text="Drink water.",
        content_title="Hydration",
        created_datetime_utc=now,
        updated_datetime_utc=now,
        workspace_id=workspace_id,
    )
    rollback_asession.add(content_db)
    await rollback_asession.flush()
    return content_db.content_id


@pytest.fixture
async def query_db(rollback_asession: AsyncSession, workspace_id: int) -> QueryDB:
    """Save a user query in the throwaway workspace.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_id
        The throwaway workspace ID.

    Returns
    -------
    QueryDB
        The saved user query.
    """

    return await save_user_query_to_db(
        asession=rollback_asession,
        user_query=QueryBase(
            generate_llm_response=True,
            query_metadata={"source": "test"},
            query_text="How much water should I drink?",
            session_id=SESSION_ID,
        ),
        workspace_id=workspace_id,
    )


async def test_save_user_query_to_db(query_db: QueryDB, workspace_id: int) -> None:
    """The saved query keeps the request fields and gets an ID and a secret key.

    Parameters
    ----------
    query_db
        The saved user query.
    workspace_id
        The throwaway workspace ID.
    """

    assert query_db.query_id is not None
    assert query_db.feedback_secret_key
    assert query_db.query_generate_llm_response is True
    assert query_db.query_metadata == {"source": "test"}
    assert query_db.query_text == "How much water should I drink?"
    assert query_db.session_id == SESSION_ID
    assert query_db.workspace_id == workspace_id


@pytest.mark.parametrize(
    "use_correct_key, use_existing_query, expected",
    [(True, True, True), (False, True, False), (True, False, False)],
)
async def test_check_secret_key_match(
    use_correct_key: bool,
    use_existing_query: bool,
    expected: bool,
    query_db: QueryDB,
    rollback_asession: AsyncSession,
) -> None:
    """Only the secret key generated for the query matches, and only for that query.

    Parameters
    ----------
    use_correct_key
        Whether to pass the query's real secret key.
    use_existing_query
        Whether to pass the query's real ID (otherwise an ID that does not exist).
    expected
        The expected result.
    query_db
        The saved user query.
    rollback_asession
        Async session that is rolled back on teardown.
    """

    secret_key = query_db.feedback_secret_key if use_correct_key else "wrong-key"
    query_id = query_db.query_id if use_existing_query else query_db.query_id + 10_000

    assert (
        await check_secret_key_match(
            asession=rollback_asession, query_id=query_id, secret_key=secret_key
        )
        is expected
    )


def _build_response(kind: str, query_id: int) -> QueryResponse:
    """Build one of the three response types `save_query_response_to_db` accepts.

    Parameters
    ----------
    kind
        One of "response", "audio" or "error".
    query_id
        The query ID to attach to the response.

    Returns
    -------
    QueryResponse
        The response object.
    """

    common: dict[str, Any] = {
        "debug_info": {"step": kind},
        "feedback_secret_key": "irrelevant",
        "llm_response": None if kind == "error" else "Drink 2 litres.",
        "query_id": query_id,
        "search_results": {
            0: QuerySearchResult(distance=0.1, id=1, text="Drink water.", title="H")
        },
        "session_id": SESSION_ID,
    }
    if kind == "audio":
        return QueryAudioResponse(**common, tts_filepath="https://example.com/a.wav")
    if kind == "error":
        return QueryResponseError(
            **common,
            error_message="Alignment score too low",
            error_type=ErrorType.ALIGNMENT_TOO_LOW,
        )
    return QueryResponse(**common)


@pytest.mark.parametrize(
    "kind, is_error, tts_filepath, error_type",
    [
        ("response", False, None, None),
        ("audio", False, "https://example.com/a.wav", None),
        ("error", True, None, ErrorType.ALIGNMENT_TOO_LOW),
    ],
)
async def test_save_query_response_to_db(
    kind: str,
    is_error: bool,
    tts_filepath: str | None,
    error_type: ErrorType | None,
    query_db: QueryDB,
    rollback_asession: AsyncSession,
    workspace_id: int,
) -> None:
    """Each response type is stored with the matching error and TTS fields.

    Parameters
    ----------
    kind
        The response type to save.
    is_error
        Expected `is_error` flag.
    tts_filepath
        Expected TTS file path.
    error_type
        Expected error type.
    query_db
        The saved user query.
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_id
        The throwaway workspace ID.
    """

    response = _build_response(kind, query_db.query_id)

    response_db = await save_query_response_to_db(
        asession=rollback_asession,
        response=response,
        user_query_db=query_db,
        workspace_id=workspace_id,
    )

    assert response_db.response_id is not None
    assert response_db.query_id == query_db.query_id
    assert response_db.session_id == SESSION_ID
    assert response_db.workspace_id == workspace_id
    assert response_db.is_error is is_error
    assert response_db.tts_filepath == tts_filepath
    assert response_db.error_type == error_type
    assert response_db.debug_info == {"step": kind}
    # Search results are stored as JSON, so integer keys come back as strings.
    assert response_db.search_results["0"]["id"] == 1  # type: ignore[index]


async def test_save_query_response_to_db_rejects_unknown_type(
    query_db: QueryDB, rollback_asession: AsyncSession, workspace_id: int
) -> None:
    """Anything that is not a query response model is rejected.

    Parameters
    ----------
    query_db
        The saved user query.
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_id
        The throwaway workspace ID.
    """

    with pytest.raises(ValueError, match="Invalid response type"):
        await save_query_response_to_db(
            asession=rollback_asession,
            response={"llm_response": "not a model"},  # type: ignore[arg-type]
            user_query_db=query_db,
            workspace_id=workspace_id,
        )


async def test_save_response_feedback_to_db(
    query_db: QueryDB, rollback_asession: AsyncSession, workspace_id: int
) -> None:
    """Response feedback is saved against the query's workspace.

    Parameters
    ----------
    query_db
        The saved user query.
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_id
        The throwaway workspace ID.
    """

    feedback_db = await save_response_feedback_to_db(
        asession=rollback_asession,
        feedback=ResponseFeedbackBase(
            feedback_secret_key=query_db.feedback_secret_key,
            feedback_sentiment=FeedbackSentiment.NEGATIVE,
            feedback_text="Not helpful",
            query_id=query_db.query_id,
            session_id=SESSION_ID,
        ),
    )

    assert feedback_db.feedback_id is not None
    assert feedback_db.query_id == query_db.query_id
    assert feedback_db.workspace_id == workspace_id
    assert feedback_db.feedback_sentiment == FeedbackSentiment.NEGATIVE
    assert feedback_db.feedback_text == "Not helpful"
    assert feedback_db.session_id == SESSION_ID


async def test_save_content_feedback_to_db(
    content_id: int,
    query_db: QueryDB,
    rollback_asession: AsyncSession,
    workspace_id: int,
) -> None:
    """Content feedback is saved against the query's workspace and the content.

    Parameters
    ----------
    content_id
        The content row ID.
    query_db
        The saved user query.
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_id
        The throwaway workspace ID.
    """

    feedback_db = await save_content_feedback_to_db(
        asession=rollback_asession,
        feedback=ContentFeedback(
            content_id=content_id,
            feedback_secret_key=query_db.feedback_secret_key,
            feedback_sentiment=FeedbackSentiment.POSITIVE,
            feedback_text=None,
            query_id=query_db.query_id,
        ),
    )

    assert feedback_db.feedback_id is not None
    assert feedback_db.content_id == content_id
    assert feedback_db.query_id == query_db.query_id
    assert feedback_db.workspace_id == workspace_id
    assert feedback_db.feedback_sentiment == FeedbackSentiment.POSITIVE
    assert feedback_db.feedback_text is None


async def test_save_content_feedback_to_db_unknown_content(
    query_db: QueryDB, rollback_asession: AsyncSession
) -> None:
    """A content ID that does not exist violates the foreign key.

    The service relies on this `IntegrityError` to answer with a 400.

    Parameters
    ----------
    query_db
        The saved user query.
    rollback_asession
        Async session that is rolled back on teardown.
    """

    with pytest.raises(IntegrityError):
        await save_content_feedback_to_db(
            asession=rollback_asession,
            feedback=ContentFeedback(
                content_id=999_999,
                feedback_secret_key=query_db.feedback_secret_key,
                feedback_sentiment=FeedbackSentiment.UNKNOWN,
                feedback_text=None,
                query_id=query_db.query_id,
            ),
        )


async def test_save_content_for_query_to_db(
    content_id: int,
    query_db: QueryDB,
    rollback_asession: AsyncSession,
    workspace_id: int,
) -> None:
    """One link row is saved per returned content.

    Parameters
    ----------
    content_id
        The content row ID.
    query_db
        The saved user query.
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_id
        The throwaway workspace ID.
    """

    await save_content_for_query_to_db(
        asession=rollback_asession,
        contents={
            0: QuerySearchResult(distance=0.1, id=content_id, text="t", title="T")
        },
        query_id=query_db.query_id,
        session_id=SESSION_ID,
        workspace_id=workspace_id,
    )

    rows = (
        (
            await rollback_asession.execute(
                select(QueryResponseContentDB).where(
                    QueryResponseContentDB.query_id == query_db.query_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert [(r.content_id, r.session_id, r.workspace_id) for r in rows] == [
        (content_id, SESSION_ID, workspace_id)
    ]


async def test_save_content_for_query_to_db_without_contents(
    query_db: QueryDB, rollback_asession: AsyncSession, workspace_id: int
) -> None:
    """`None` contents (e.g. a failed search) save nothing.

    Parameters
    ----------
    query_db
        The saved user query.
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_id
        The throwaway workspace ID.
    """

    await save_content_for_query_to_db(
        asession=rollback_asession,
        contents=None,
        query_id=query_db.query_id,
        session_id=SESSION_ID,
        workspace_id=workspace_id,
    )

    rows = (
        await rollback_asession.execute(
            select(QueryResponseContentDB).where(
                QueryResponseContentDB.query_id == query_db.query_id
            )
        )
    ).all()
    assert rows == []
