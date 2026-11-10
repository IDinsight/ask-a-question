"""Tests for `app.tags.repository` against a real Postgres database.

Every test runs inside the `rollback_asession` transaction and creates its own
workspace, so nothing is persisted and other tests' rows never interfere.
"""

from datetime import datetime, timezone
from typing import Any, cast

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contents.models import ContentDB
from app.core.config import PGVECTOR_VECTOR_SIZE
from app.tags.models import TagDB, content_tags_table
from app.tags.repository import (
    delete_tag_from_db,
    get_list_of_tag_from_db,
    get_tag_from_db,
    is_tag_name_unique,
    save_tag_to_db,
    update_tag_in_db,
    validate_tags,
)
from app.tags.schemas import TagCreate
from app.workspaces.models import WorkspaceDB


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
        workspace_name="tags_repository_test_workspace",
    )
    rollback_asession.add(workspace_db)
    await rollback_asession.flush()
    return workspace_db.workspace_id


async def _save(asession: AsyncSession, workspace_id: int, tag_name: str) -> TagDB:
    """Save a tag through the repository.

    Parameters
    ----------
    asession
        The async session.
    workspace_id
        The workspace to save the tag in.
    tag_name
        The tag name.

    Returns
    -------
    TagDB
        The saved tag.
    """

    return await save_tag_to_db(
        asession=asession, tag=TagCreate(tag_name=tag_name), workspace_id=workspace_id
    )


async def test_save_and_get_tag(
    rollback_asession: AsyncSession, workspace_id: int
) -> None:
    """A saved tag can be read back, but only from its own workspace.

    Parameters
    ----------
    rollback_asession
        Async session whose writes are rolled back after the test.
    workspace_id
        The throw-away workspace ID.
    """

    tag = await _save(rollback_asession, workspace_id, "SAVED")

    assert tag.tag_id is not None
    assert tag.created_datetime_utc is not None
    found = await get_tag_from_db(
        asession=rollback_asession, tag_id=tag.tag_id, workspace_id=workspace_id
    )
    assert found is not None and found.tag_name == "SAVED"
    assert (
        await get_tag_from_db(
            asession=rollback_asession, tag_id=tag.tag_id, workspace_id=workspace_id + 1
        )
        is None
    )


async def test_save_tag_without_commit(
    rollback_asession: AsyncSession, workspace_id: int
) -> None:
    """With `commmit=False` the tag is only added to the session (no ID yet).

    Parameters
    ----------
    rollback_asession
        Async session whose writes are rolled back after the test.
    workspace_id
        The throw-away workspace ID.
    """

    # NB: the keyword really is spelt `commmit` in the repository.
    tag = await save_tag_to_db(
        asession=rollback_asession,
        tag=TagCreate(tag_name="PENDING"),
        workspace_id=workspace_id,
        commmit=False,
    )

    assert tag.tag_id is None
    assert tag in rollback_asession.new
    await rollback_asession.flush()
    assert tag.tag_id is not None


async def test_update_tag(rollback_asession: AsyncSession, workspace_id: int) -> None:
    """Updating renames the tag and keeps its creation time.

    Parameters
    ----------
    rollback_asession
        Async session whose writes are rolled back after the test.
    workspace_id
        The throw-away workspace ID.
    """

    tag = await _save(rollback_asession, workspace_id, "BEFORE")
    created = tag.created_datetime_utc

    updated = await update_tag_in_db(
        asession=rollback_asession,
        tag=TagCreate(tag_name="AFTER"),
        tag_id=tag.tag_id,
        workspace_id=workspace_id,
    )

    assert updated.tag_id == tag.tag_id
    assert updated.tag_name == "AFTER"
    assert updated.created_datetime_utc == created


async def test_delete_tag_removes_content_links(
    rollback_asession: AsyncSession, workspace_id: int
) -> None:
    """Deleting a tag removes it and its content links, but not the content.

    Parameters
    ----------
    rollback_asession
        Async session whose writes are rolled back after the test.
    workspace_id
        The throw-away workspace ID.
    """

    tag = await _save(rollback_asession, workspace_id, "LINKED")
    now = datetime.now(timezone.utc)
    content = ContentDB(
        content_embedding=np.zeros(int(PGVECTOR_VECTOR_SIZE)).tolist(),
        content_metadata={},
        content_tags=[tag],
        content_text="text",
        content_title="title",
        created_datetime_utc=now,
        updated_datetime_utc=now,
        workspace_id=workspace_id,
    )
    rollback_asession.add(content)
    await rollback_asession.flush()
    tag_id, content_id = tag.tag_id, content.content_id

    await delete_tag_from_db(
        asession=rollback_asession, tag_id=tag_id, workspace_id=workspace_id
    )
    rollback_asession.expunge_all()

    assert (
        await get_tag_from_db(
            asession=rollback_asession, tag_id=tag_id, workspace_id=workspace_id
        )
        is None
    )
    links = (
        await rollback_asession.execute(
            select(content_tags_table).where(content_tags_table.c.tag_id == tag_id)
        )
    ).all()
    assert links == []
    assert await rollback_asession.get(ContentDB, content_id) is not None


@pytest.mark.parametrize(
    "limit, offset, expected",
    [
        (None, 0, ["A", "B", "C"]),
        (2, 0, ["A", "B"]),
        (None, 1, ["B", "C"]),
        (1, 1, ["B"]),
    ],
    ids=["all", "limit", "offset", "limit_offset"],
)
async def test_list_tags(
    expected: list[str],
    limit: int | None,
    offset: int,
    rollback_asession: AsyncSession,
    workspace_id: int,
) -> None:
    """Tags are listed in ID order with optional paging.

    Parameters
    ----------
    expected
        The expected tag names, in order.
    limit
        Maximum number of tags to return.
    offset
        Number of tags to skip.
    rollback_asession
        Async session whose writes are rolled back after the test.
    workspace_id
        The throw-away workspace ID.
    """

    for name in ["A", "B", "C"]:
        await _save(rollback_asession, workspace_id, name)

    result = await get_list_of_tag_from_db(
        asession=rollback_asession,
        limit=limit,
        offset=offset,
        workspace_id=workspace_id,
    )

    assert [t.tag_name for t in result] == expected


async def test_list_tags_empty(
    rollback_asession: AsyncSession, workspace_id: int
) -> None:
    """An empty workspace has no tags.

    Parameters
    ----------
    rollback_asession
        Async session whose writes are rolled back after the test.
    workspace_id
        The throw-away workspace ID.
    """

    assert (
        await get_list_of_tag_from_db(
            asession=rollback_asession, workspace_id=workspace_id
        )
        == []
    )


async def test_validate_tags(
    rollback_asession: AsyncSession, workspace_id: int
) -> None:
    """Known tags resolve to `TagDB` objects; otherwise the unknown IDs are returned.

    Parameters
    ----------
    rollback_asession
        Async session whose writes are rolled back after the test.
    workspace_id
        The throw-away workspace ID.
    """

    tag_a = await _save(rollback_asession, workspace_id, "A")
    tag_b = await _save(rollback_asession, workspace_id, "B")
    common: dict[str, Any] = {
        "asession": rollback_asession,
        "workspace_id": workspace_id,
    }

    is_valid, tags = await validate_tags(tags=[tag_a.tag_id, tag_b.tag_id], **common)
    assert is_valid is True
    # On success `validate_tags` returns `TagDB` rows rather than IDs.
    assert all(isinstance(t, TagDB) for t in tags)
    assert {t.tag_id for t in cast(list[TagDB], tags)} == {tag_a.tag_id, tag_b.tag_id}

    assert await validate_tags(tags=[], **common) == (True, [])

    is_valid, invalid = await validate_tags(tags=[tag_a.tag_id, -1, -2], **common)
    assert is_valid is False
    # On failure `validate_tags` returns the unknown tag IDs.
    assert sorted(cast(list[int], invalid)) == [-2, -1]


async def test_is_tag_name_unique(
    rollback_asession: AsyncSession, workspace_id: int
) -> None:
    """Names are unique per workspace and the comparison is case-sensitive.

    Parameters
    ----------
    rollback_asession
        Async session whose writes are rolled back after the test.
    workspace_id
        The throw-away workspace ID.
    """

    await _save(rollback_asession, workspace_id, "TAKEN")

    async def _unique(name: str, workspace: int = workspace_id) -> bool:
        return await is_tag_name_unique(
            asession=rollback_asession, tag_name=name, workspace_id=workspace
        )

    assert await _unique("TAKEN") is False
    assert await _unique("FREE") is True
    # The service upper-cases names; the repository itself compares exactly.
    assert await _unique("taken") is True
    assert await _unique("TAKEN", workspace_id + 1) is True
