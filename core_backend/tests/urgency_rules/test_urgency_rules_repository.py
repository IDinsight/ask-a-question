"""Tests for the urgency rules repository against a real Postgres database.

Every test runs inside `rollback_asession`, so the rows written here are rolled
back when the test ends and no clean-up is needed. The embedding call is replaced
with a deterministic fake so cosine distances are predictable.
"""

from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PGVECTOR_VECTOR_SIZE
from app.urgency_rules.models import UrgencyRuleDB
from app.urgency_rules.repository import (
    delete_urgency_rule_from_db,
    get_cosine_distances_from_rules,
    get_urgency_rule_by_id_from_db,
    get_urgency_rules_from_db,
    save_urgency_rule_to_db,
    update_urgency_rule_in_db,
)
from app.urgency_rules.schemas import UrgencyRuleCreate
from app.workspaces.models import WorkspaceDB

# Each known text embeds to its own unit axis, so two texts are either identical
# (cosine distance 0) or orthogonal (cosine distance 1).
AXES = {"fever": 0, "bleeding": 1, "headache": 2}


async def fake_embedding(*, text_to_embed: str, **kwargs: Any) -> list[float]:
    """Embed a known text as a one-hot vector.

    Parameters
    ----------
    text_to_embed
        The text to embed; must be a key of `AXES`.
    kwargs
        Ignored (e.g. Langfuse metadata).

    Returns
    -------
    list[float]
        The one-hot vector.
    """

    vector = [0.0] * int(PGVECTOR_VECTOR_SIZE)
    vector[AXES[text_to_embed]] = 1.0
    return vector


@pytest.fixture(autouse=True)
def deterministic_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the (session-wide random) fake embedding with `fake_embedding`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    monkeypatch.setattr("app.urgency_rules.repository.embedding", fake_embedding)


@pytest.fixture
async def workspace_ids(rollback_asession: AsyncSession) -> tuple[int, int]:
    """Create two throwaway workspaces inside the rolled-back transaction.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.

    Returns
    -------
    tuple[int, int]
        The two workspace IDs.
    """

    now = datetime.now(timezone.utc)
    workspaces = [
        WorkspaceDB(
            created_datetime_utc=now,
            doc_language="ENGLISH",
            updated_datetime_utc=now,
            workspace_name=f"urgency_rules_repository_workspace_{i}",
        )
        for i in range(2)
    ]
    rollback_asession.add_all(workspaces)
    await rollback_asession.flush()
    return workspaces[0].workspace_id, workspaces[1].workspace_id


async def _save(
    asession: AsyncSession, workspace_id: int, text: str, metadata: dict | None = None
) -> UrgencyRuleDB:
    """Save a rule through the repository.

    Parameters
    ----------
    asession
        The session to save with.
    workspace_id
        The workspace to save the rule in.
    text
        The rule text; must be a key of `AXES`.
    metadata
        Optional rule metadata.

    Returns
    -------
    UrgencyRuleDB
        The saved rule.
    """

    return await save_urgency_rule_to_db(
        asession=asession,
        urgency_rule=UrgencyRuleCreate(
            urgency_rule_metadata=metadata or {}, urgency_rule_text=text
        ),
        workspace_id=workspace_id,
    )


@pytest.fixture
async def rules(
    rollback_asession: AsyncSession, workspace_ids: tuple[int, int]
) -> list[UrgencyRuleDB]:
    """Save three rules in the first workspace and one in the second.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_ids
        The two throwaway workspace IDs.

    Returns
    -------
    list[UrgencyRuleDB]
        The rules saved in the first workspace, in insertion (ID) order.
    """

    ws_1, ws_2 = workspace_ids
    saved = [await _save(rollback_asession, ws_1, text) for text in AXES]
    await _save(rollback_asession, ws_2, "fever")
    return saved


async def test_save_urgency_rule_to_db(
    rollback_asession: AsyncSession, workspace_ids: tuple[int, int]
) -> None:
    """A saved rule gets an ID, timestamps and the embedded vector.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_ids
        The two throwaway workspace IDs.
    """

    rule_db = await _save(rollback_asession, workspace_ids[0], "fever", {"k": "v"})

    assert rule_db.urgency_rule_id is not None
    assert rule_db.urgency_rule_text == "fever"
    assert rule_db.urgency_rule_metadata == {"k": "v"}
    assert rule_db.workspace_id == workspace_ids[0]
    assert rule_db.created_datetime_utc is not None
    assert list(rule_db.urgency_rule_vector[:2]) == [1.0, 0.0]
    assert f"#{rule_db.urgency_rule_id}: fever" in repr(rule_db)


async def test_update_urgency_rule_in_db(
    rollback_asession: AsyncSession, rules: list[UrgencyRuleDB]
) -> None:
    """Updating replaces text, metadata and vector but keeps the creation time.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.
    rules
        Rules saved in the first workspace.
    """

    original = rules[0]
    created = original.created_datetime_utc

    updated = await update_urgency_rule_in_db(
        asession=rollback_asession,
        urgency_rule=UrgencyRuleCreate(
            urgency_rule_metadata={"new": "meta"}, urgency_rule_text="headache"
        ),
        urgency_rule_id=original.urgency_rule_id,
        workspace_id=original.workspace_id,
    )

    assert updated.urgency_rule_id == original.urgency_rule_id
    assert updated.urgency_rule_text == "headache"
    assert updated.urgency_rule_metadata == {"new": "meta"}
    assert updated.urgency_rule_vector[AXES["headache"]] == 1.0
    assert updated.created_datetime_utc == created
    assert updated.updated_datetime_utc >= created


@pytest.mark.parametrize("same_workspace", [True, False])
async def test_get_urgency_rule_by_id_from_db(
    rollback_asession: AsyncSession,
    rules: list[UrgencyRuleDB],
    same_workspace: bool,
    workspace_ids: tuple[int, int],
) -> None:
    """A rule is only found from the workspace it belongs to.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.
    rules
        Rules saved in the first workspace.
    same_workspace
        Whether to look the rule up from its own workspace.
    workspace_ids
        The two throwaway workspace IDs.
    """

    found = await get_urgency_rule_by_id_from_db(
        asession=rollback_asession,
        urgency_rule_id=rules[0].urgency_rule_id,
        workspace_id=workspace_ids[0 if same_workspace else 1],
    )

    assert (found is rules[0]) if same_workspace else (found is None)


@pytest.mark.parametrize(
    "workspace_index, deleted",
    [(1, False), (0, True)],
    ids=["other_workspace", "own_workspace"],
)
async def test_delete_urgency_rule_from_db(
    deleted: bool,
    rollback_asession: AsyncSession,
    rules: list[UrgencyRuleDB],
    workspace_ids: tuple[int, int],
    workspace_index: int,
) -> None:
    """Deleting only removes the rule from the workspace it belongs to.

    Parameters
    ----------
    deleted
        Whether the rule is expected to be gone afterwards.
    rollback_asession
        Async session that is rolled back on teardown.
    rules
        Rules saved in the first workspace.
    workspace_ids
        The two throwaway workspace IDs.
    workspace_index
        Which workspace to delete from.
    """

    rule_id = rules[0].urgency_rule_id

    await delete_urgency_rule_from_db(
        asession=rollback_asession,
        urgency_rule_id=rule_id,
        workspace_id=workspace_ids[workspace_index],
    )

    remaining = await get_urgency_rules_from_db(
        asession=rollback_asession, workspace_id=workspace_ids[0]
    )
    assert (rule_id not in [r.urgency_rule_id for r in remaining]) is deleted


@pytest.mark.parametrize(
    "offset, limit, expected_indices",
    [
        (0, None, [0, 1, 2]),
        (1, None, [1, 2]),
        (0, 2, [0, 1]),
        (1, 1, [1]),
        # Non-positive limits are ignored rather than returning nothing.
        (0, 0, [0, 1, 2]),
    ],
)
async def test_get_urgency_rules_from_db(
    expected_indices: list[int],
    limit: int | None,
    offset: int,
    rollback_asession: AsyncSession,
    rules: list[UrgencyRuleDB],
    workspace_ids: tuple[int, int],
) -> None:
    """Rules are listed in ID order and honour offset and limit.

    Parameters
    ----------
    expected_indices
        Indices into `rules` expected in the result.
    limit
        The maximum number of rules to return.
    offset
        The number of rules to skip.
    rollback_asession
        Async session that is rolled back on teardown.
    rules
        Rules saved in the first workspace.
    workspace_ids
        The two throwaway workspace IDs.
    """

    result = await get_urgency_rules_from_db(
        asession=rollback_asession,
        limit=limit,
        offset=offset,
        workspace_id=workspace_ids[0],
    )

    assert [r.urgency_rule_id for r in result] == [
        rules[i].urgency_rule_id for i in expected_indices
    ]


async def test_get_cosine_distances_from_rules(
    rollback_asession: AsyncSession,
    rules: list[UrgencyRuleDB],
    workspace_ids: tuple[int, int],
) -> None:
    """Distances cover only the workspace's rules, closest first.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.
    rules
        Rules saved in the first workspace.
    workspace_ids
        The two throwaway workspace IDs.
    """

    distances = await get_cosine_distances_from_rules(
        asession=rollback_asession,
        message_text="bleeding",
        workspace_id=workspace_ids[0],
    )

    assert list(distances) == [0, 1, 2]
    assert distances[0].urgency_rule == "bleeding"
    assert distances[0].distance == pytest.approx(0.0)
    # The other two rules are orthogonal to the message.
    assert {distances[1].urgency_rule, distances[2].urgency_rule} == {
        "fever",
        "headache",
    }
    assert all(distances[i].distance == pytest.approx(1.0) for i in (1, 2))


async def test_get_cosine_distances_from_rules_no_rules(
    rollback_asession: AsyncSession, workspace_ids: tuple[int, int]
) -> None:
    """A workspace without rules yields no distances.

    Parameters
    ----------
    rollback_asession
        Async session that is rolled back on teardown.
    workspace_ids
        The two throwaway workspace IDs.
    """

    assert (
        await get_cosine_distances_from_rules(
            asession=rollback_asession,
            message_text="fever",
            workspace_id=workspace_ids[0],
        )
        == {}
    )
