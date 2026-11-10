"""Tests for `app.contents.repository` against a real Postgres database.

Every test runs inside the `rollback_asession` transaction and creates its own
workspace, so nothing is persisted and other tests' rows never interfere. Embeddings
come from the session-wide fake in `tests/conftest.py` (`patch_llm_call`).
"""

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contents.models import ContentDB
from app.contents.repository import (
    archive_content_from_db,
    delete_content_from_db,
    get_content_from_db,
    get_latest_display_number,
    get_list_of_content_from_db,
    get_next_unvalidated_content_card,
    get_search_results,
    get_similar_content_async,
    get_unvalidated_count,
    increment_query_count,
    mark_content_as_validated,
    save_content_to_db,
    update_content_in_db,
    update_votes_in_db,
    validate_related_contents,
)
from app.contents.schemas import ContentCreate, QuerySearchResult
from app.core.config import PGVECTOR_VECTOR_SIZE
from app.question_answer.schemas import FeedbackSentiment
from app.tags.models import TagDB, content_tags_table
from app.workspaces.models import WorkspaceDB

VECTOR_SIZE = int(PGVECTOR_VECTOR_SIZE)


def _unit_vector(index: int) -> list[float]:
    """Return a one-hot embedding so cosine distances are predictable.

    Parameters
    ----------
    index
        Position of the 1.0 entry.

    Returns
    -------
    list[float]
        The embedding.
    """

    vector = np.zeros(VECTOR_SIZE, dtype=np.float32)
    vector[index] = 1.0
    return vector.tolist()


@pytest.fixture
async def workspace_id(rollback_asession: AsyncSession) -> int:
    """Create a throw-away workspace inside the rolled-back transaction.

    Parameters
    ----------
    rollback_asession
        Async session whose writes are rolled back after the test.

    Returns
    -------
    int
        The new workspace's ID.
    """

    now = datetime.now(timezone.utc)
    workspace_db = WorkspaceDB(
        content_quota=None,
        created_datetime_utc=now,
        doc_language="ENGLISH",
        updated_datetime_utc=now,
        workspace_name="contents_repository_test_workspace",
    )
    rollback_asession.add(workspace_db)
    await rollback_asession.flush()
    return workspace_db.workspace_id


async def _save(
    asession: AsyncSession, workspace_id: int, **overrides: Any
) -> ContentDB:
    """Save a content row through the repository.

    Parameters
    ----------
    asession
        The async session.
    workspace_id
        The workspace to save the content in.
    overrides
        `ContentCreate` fields that replace the defaults.

    Returns
    -------
    ContentDB
        The saved content.
    """

    values: dict[str, Any] = {"content_text": "text", "content_title": "title"}
    values.update(overrides)
    return await save_content_to_db(
        asession=asession,
        content=ContentCreate(**values),
        exclude_archived=False,
        workspace_id=workspace_id,
    )


async def _insert(
    asession: AsyncSession, workspace_id: int, *, embedding_index: int, **overrides: Any
) -> ContentDB:
    """Insert a content row directly, with a known embedding.

    Parameters
    ----------
    asession
        The async session.
    workspace_id
        The workspace to insert the content in.
    embedding_index
        Index of the one-hot embedding (see `_unit_vector`).
    overrides
        Column values that replace the defaults.

    Returns
    -------
    ContentDB
        The inserted content.
    """

    now = datetime.now(timezone.utc)
    values: dict[str, Any] = {
        "content_embedding": _unit_vector(embedding_index),
        "content_metadata": {},
        "content_text": f"text {embedding_index}",
        "content_title": f"title {embedding_index}",
        "created_datetime_utc": now,
        "updated_datetime_utc": now,
        "workspace_id": workspace_id,
    }
    values.update(overrides)
    content_db = ContentDB(**values)
    asession.add(content_db)
    await asession.flush()
    return content_db


class TestSaveAndUpdate:
    """Tests for `save_content_to_db`, `update_content_in_db` and display numbers."""

    async def test_display_numbers_increase_per_workspace(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """The first content gets display number 1 and each new one increments it.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        assert (
            await get_latest_display_number(
                asession=rollback_asession, workspace_id=workspace_id
            )
            == 0
        )
        first = await _save(rollback_asession, workspace_id, content_title="a")
        second = await _save(rollback_asession, workspace_id, content_title="b")

        assert (first.display_number, second.display_number) == (1, 2)
        assert first.content_embedding is not None
        assert (
            await get_latest_display_number(
                asession=rollback_asession, workspace_id=workspace_id
            )
            == 2
        )

    async def test_save_returns_tags_and_archived_content(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """Saved content is reloaded with its tags, even when it is archived.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        now = datetime.now(timezone.utc)
        tag = TagDB(
            created_datetime_utc=now,
            tag_name="REPO_TAG",
            updated_datetime_utc=now,
            workspace_id=workspace_id,
        )
        rollback_asession.add(tag)
        await rollback_asession.flush()

        saved = await _save(
            rollback_asession, workspace_id, content_tags=[tag], is_archived=True
        )

        assert [t.tag_id for t in saved.content_tags] == [tag.tag_id]
        assert saved.workspace_id == workspace_id

    async def test_save_without_commit(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """With `commit=False` the pending row is still flushed and returned.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        saved = await save_content_to_db(
            asession=rollback_asession,
            content=ContentCreate(content_text="t", content_title="uncommitted"),
            workspace_id=workspace_id,
            commit=False,
        )

        # The look-up after saving autoflushes, so the row has an ID.
        assert saved.content_id is not None
        assert saved.content_title == "uncommitted"

    async def test_update_content(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """Updating replaces the editable fields but keeps the display number.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        original = await _save(rollback_asession, workspace_id)
        content_id, display_number = original.content_id, original.display_number

        updated = await update_content_in_db(
            asession=rollback_asession,
            content=ContentCreate(
                content_metadata={"k": "v"},
                content_text="new text",
                content_title="new title",
                is_archived=True,
            ),
            content_id=content_id,
            workspace_id=workspace_id,
        )

        assert updated.content_id == content_id
        assert updated.content_title == "new title"
        assert updated.content_metadata == {"k": "v"}
        # Archived content is still returned after an update.
        assert updated.is_archived is True
        assert updated.display_number == display_number


class TestGetContent:
    """Tests for single and list look-ups and their exclusion filters."""

    @pytest.mark.parametrize(
        "is_archived, is_validated, exclude_archived, exclude_unvalidated, found",
        [
            (False, True, True, True, True),
            (True, True, True, True, False),
            (True, True, False, True, True),
            (False, False, True, True, False),
            (False, False, True, False, True),
        ],
        ids=[
            "active",
            "archived_excluded",
            "archived_included",
            "unvalidated_excluded",
            "unvalidated_included",
        ],
    )
    async def test_get_content_filters(
        self,
        exclude_archived: bool,
        exclude_unvalidated: bool,
        found: bool,
        is_archived: bool,
        is_validated: bool,
        rollback_asession: AsyncSession,
        workspace_id: int,
    ) -> None:
        """`get_content_from_db` honours the archived/unvalidated filters.

        Parameters
        ----------
        exclude_archived
            Whether to exclude archived content.
        exclude_unvalidated
            Whether to exclude unvalidated content.
        found
            Whether the content is expected to be returned.
        is_archived
            The stored archive flag.
        is_validated
            The stored validation flag.
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        content = await _insert(
            rollback_asession,
            workspace_id,
            embedding_index=0,
            is_archived=is_archived,
            is_validated=is_validated,
        )

        result = await get_content_from_db(
            asession=rollback_asession,
            content_id=content.content_id,
            exclude_archived=exclude_archived,
            exclude_unvalidated=exclude_unvalidated,
            workspace_id=workspace_id,
        )

        assert (result is not None) is found

    async def test_get_content_other_workspace(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """Content is not visible from another workspace.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        content = await _insert(rollback_asession, workspace_id, embedding_index=0)
        result = await get_content_from_db(
            asession=rollback_asession,
            content_id=content.content_id,
            workspace_id=workspace_id + 1,
        )
        assert result is None

    @pytest.mark.parametrize(
        "kwargs, expected_titles",
        [
            ({}, ["title 0", "title 1", "title 2"]),
            ({"offset": 1}, ["title 1", "title 2"]),
            ({"limit": 2}, ["title 0", "title 1"]),
            ({"offset": 1, "limit": 1}, ["title 1"]),
            ({"limit": 0}, ["title 0", "title 1", "title 2"]),
            (
                {"exclude_archived": False},
                ["title 0", "title 1", "title 2", "title 3"],
            ),
            (
                {"exclude_unvalidated": False},
                ["title 0", "title 1", "title 2", "title 4"],
            ),
        ],
        ids=[
            "all",
            "offset",
            "limit",
            "offset_limit",
            "zero_limit_means_all",
            "with_archived",
            "with_unvalidated",
        ],
    )
    async def test_list_content(
        self,
        expected_titles: list[str],
        kwargs: dict[str, Any],
        rollback_asession: AsyncSession,
        workspace_id: int,
    ) -> None:
        """Listing is ordered by display number and supports paging and filters.

        Parameters
        ----------
        expected_titles
            The expected content titles, in order.
        kwargs
            Extra arguments for `get_list_of_content_from_db`.
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        for i in range(3):
            await _insert(
                rollback_asession, workspace_id, embedding_index=i, display_number=i
            )
        await _insert(
            rollback_asession,
            workspace_id,
            embedding_index=3,
            display_number=3,
            is_archived=True,
        )
        await _insert(
            rollback_asession,
            workspace_id,
            embedding_index=4,
            display_number=4,
            is_validated=False,
        )

        result = await get_list_of_content_from_db(
            asession=rollback_asession, workspace_id=workspace_id, **kwargs
        )

        assert [c.content_title for c in result] == expected_titles

    async def test_list_content_empty(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """An empty workspace returns an empty list.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        assert (
            await get_list_of_content_from_db(
                asession=rollback_asession, workspace_id=workspace_id
            )
            == []
        )


class TestArchiveValidateDelete:
    """Tests for archiving, validating and deleting content."""

    async def test_archive_content(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """Archived content is hidden by default but still stored.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        content = await _insert(rollback_asession, workspace_id, embedding_index=0)
        content_id = content.content_id
        await archive_content_from_db(
            asession=rollback_asession,
            content_id=content_id,
            workspace_id=workspace_id,
        )
        # The bulk UPDATE bypasses the identity map, so drop cached state.
        rollback_asession.expire_all()

        common: dict[str, Any] = {
            "asession": rollback_asession,
            "content_id": content_id,
            "workspace_id": workspace_id,
        }
        assert await get_content_from_db(**common) is None
        archived = await get_content_from_db(**common, exclude_archived=False)
        assert archived is not None and archived.is_archived is True

    async def test_unvalidated_count_and_queue(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """The queue returns the lowest display number first; archived cards are
        ignored; validating a card removes it from the queue.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        common: dict[str, Any] = {
            "asession": rollback_asession,
            "workspace_id": workspace_id,
        }
        assert await get_unvalidated_count(**common) == 0
        assert await get_next_unvalidated_content_card(**common) is None

        await _insert(
            rollback_asession,
            workspace_id,
            embedding_index=0,
            display_number=1,
            is_archived=True,
            is_validated=False,
        )
        later = await _insert(
            rollback_asession,
            workspace_id,
            embedding_index=1,
            display_number=3,
            is_validated=False,
        )
        first = await _insert(
            rollback_asession,
            workspace_id,
            embedding_index=2,
            display_number=2,
            is_validated=False,
        )

        # Read IDs now: `expire_all()` below would force a (sync) reload later.
        first_id, later_id = first.content_id, later.content_id

        assert await get_unvalidated_count(**common) == 2
        next_card = await get_next_unvalidated_content_card(**common)
        assert next_card is not None and next_card.content_id == first_id

        await mark_content_as_validated(content_id=first_id, **common)
        rollback_asession.expire_all()

        assert await get_unvalidated_count(**common) == 1
        next_card = await get_next_unvalidated_content_card(**common)
        assert next_card is not None and next_card.content_id == later_id

    async def test_delete_content_removes_tag_links(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """Deleting content also removes its rows in the content-tag link table.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        now = datetime.now(timezone.utc)
        tag = TagDB(
            created_datetime_utc=now,
            tag_name="DELETE_ME",
            updated_datetime_utc=now,
            workspace_id=workspace_id,
        )
        content = await _insert(
            rollback_asession, workspace_id, embedding_index=0, content_tags=[tag]
        )
        content_id = content.content_id

        await delete_content_from_db(
            asession=rollback_asession, content_id=content_id, workspace_id=workspace_id
        )
        rollback_asession.expunge_all()

        links = (
            await rollback_asession.execute(
                select(content_tags_table).where(
                    content_tags_table.c.content_id == content_id
                )
            )
        ).all()
        assert links == []
        assert (
            await get_content_from_db(
                asession=rollback_asession,
                content_id=content_id,
                exclude_archived=False,
                exclude_unvalidated=False,
                workspace_id=workspace_id,
            )
            is None
        )


class TestSearch:
    """Tests for vector search and its filters."""

    async def test_results_ordered_by_distance(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """The closest content comes first and `n_similar` caps the results.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        far = await _insert(rollback_asession, workspace_id, embedding_index=1)
        near = await _insert(rollback_asession, workspace_id, embedding_index=0)

        # Mostly along axis 0, so `near` is closer than `far`.
        question = _unit_vector(0)
        question[1] = 0.5

        results = await get_search_results(
            asession=rollback_asession,
            n_similar=10,
            question_embedding=question,
            workspace_id=workspace_id,
        )
        assert [r.id for r in results.values()] == [near.content_id, far.content_id]
        assert results[0].distance < results[1].distance
        assert results[0].title == near.content_title

        top_one = await get_search_results(
            asession=rollback_asession,
            n_similar=1,
            question_embedding=question,
            workspace_id=workspace_id,
        )
        assert list(top_one) == [0]

    @pytest.mark.parametrize(
        "flag, exclude_kwarg",
        [("is_archived", "exclude_archived"), ("is_validated", "exclude_unvalidated")],
    )
    async def test_excluded_content_not_in_results(
        self,
        exclude_kwarg: str,
        flag: str,
        rollback_asession: AsyncSession,
        workspace_id: int,
    ) -> None:
        """Archived/unvalidated content only appears when explicitly included.

        This keeps archived and unvalidated content out of search and AI responses.

        Parameters
        ----------
        exclude_kwarg
            The `get_search_results` argument that controls the filter.
        flag
            The content column that marks the content as excluded.
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        # Archived means is_archived=True; unvalidated means is_validated=False.
        await _insert(
            rollback_asession,
            workspace_id,
            embedding_index=0,
            **{flag: flag == "is_archived"},
        )
        common: dict[str, Any] = {
            "asession": rollback_asession,
            "n_similar": 10,
            "question_embedding": _unit_vector(0),
            "workspace_id": workspace_id,
        }

        assert len(await get_search_results(**{**common, exclude_kwarg: False})) == 1
        assert len(await get_search_results(**{**common, exclude_kwarg: True})) == 0

    async def test_get_similar_content_async(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """The question is embedded and searched within the workspace.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        content = await _insert(rollback_asession, workspace_id, embedding_index=0)

        results = await get_similar_content_async(
            asession=rollback_asession,
            n_similar=5,
            question="any question",
            workspace_id=workspace_id,
        )

        assert [r.id for r in results.values()] == [content.content_id]


class TestCountersAndVotes:
    """Tests for query counts and feedback votes."""

    async def test_increment_query_count(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """Each returned search result has its query count bumped; unknown IDs and
        `None` are ignored.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        content = await _insert(rollback_asession, workspace_id, embedding_index=0)
        common: dict[str, Any] = {
            "asession": rollback_asession,
            "workspace_id": workspace_id,
        }

        await increment_query_count(contents=None, **common)
        await increment_query_count(
            contents={
                0: QuerySearchResult(
                    distance=0.0, id=content.content_id, text="t", title="t"
                ),
                1: QuerySearchResult(distance=0.1, id=-1, text="t", title="t"),
            },
            **common,
        )

        assert content.query_count == 1

    @pytest.mark.parametrize(
        "vote, expected",
        [
            (FeedbackSentiment.POSITIVE, (1, 0)),
            (FeedbackSentiment.NEGATIVE, (0, 1)),
            (FeedbackSentiment.UNKNOWN, (0, 0)),
        ],
    )
    async def test_update_votes(
        self,
        expected: tuple[int, int],
        rollback_asession: AsyncSession,
        vote: FeedbackSentiment,
        workspace_id: int,
    ) -> None:
        """Positive/negative votes increment the matching counter only.

        Parameters
        ----------
        expected
            Expected `(positive_votes, negative_votes)`.
        rollback_asession
            Async session whose writes are rolled back after the test.
        vote
            The feedback sentiment.
        workspace_id
            The throw-away workspace ID.
        """

        content = await _insert(rollback_asession, workspace_id, embedding_index=0)

        result = await update_votes_in_db(
            asession=rollback_asession,
            content_id=content.content_id,
            vote=vote,
            workspace_id=workspace_id,
        )

        assert result is not None
        assert (result.positive_votes, result.negative_votes) == expected

    async def test_update_votes_missing_content(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """Voting on unknown content returns `None`.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        result = await update_votes_in_db(
            asession=rollback_asession,
            content_id=-1,
            vote=FeedbackSentiment.POSITIVE,
            workspace_id=workspace_id,
        )
        assert result is None


class TestValidateRelatedContents:
    """Tests for `validate_related_contents`."""

    async def test_all_valid(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """Existing, active contents are all valid and returned unchanged.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        ids = [
            (
                await _insert(rollback_asession, workspace_id, embedding_index=i)
            ).content_id
            for i in range(2)
        ]
        assert await validate_related_contents(
            asession=rollback_asession, related_contents=ids, workspace_id=workspace_id
        ) == (True, ids)

    async def test_unknown_and_archived_are_invalid(
        self, rollback_asession: AsyncSession, workspace_id: int
    ) -> None:
        """Unknown and archived IDs are dropped and the result is flagged invalid.

        Parameters
        ----------
        rollback_asession
            Async session whose writes are rolled back after the test.
        workspace_id
            The throw-away workspace ID.
        """

        active = await _insert(rollback_asession, workspace_id, embedding_index=0)
        archived = await _insert(
            rollback_asession, workspace_id, embedding_index=1, is_archived=True
        )

        is_valid, valid_ids = await validate_related_contents(
            asession=rollback_asession,
            related_contents=[active.content_id, archived.content_id, -1],
            workspace_id=workspace_id,
        )

        assert is_valid is False
        assert valid_ids == [active.content_id]
