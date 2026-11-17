"""Unit tests for the urgency rules service layer.

No database is touched: the repository and workspace/user lookups are replaced
with mocks as imported in `app.urgency_rules.service`.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.core.utils import EmbeddingCallException
from app.urgency_rules import service
from app.urgency_rules.models import UrgencyRuleDB
from app.urgency_rules.schemas import UrgencyRuleCreate
from app.urgency_rules.service import _convert_record_to_schema
from app.users.models import UserDB
from app.workspaces.models import WorkspaceDB
from tests.conftest import async_fake_embedding

SERVICE = "app.urgency_rules.service"
WORKSPACE = WorkspaceDB(workspace_id=5, workspace_name="ws")
USER = UserDB(user_id=1, username="admin")
RULE_IN = UrgencyRuleCreate(urgency_rule_metadata={"k": "v"}, urgency_rule_text="t")


def _rule_db(urgency_rule_id: int = 7) -> UrgencyRuleDB:
    """Build an unsaved urgency rule row in `WORKSPACE`.

    Parameters
    ----------
    urgency_rule_id
        The rule ID.

    Returns
    -------
    UrgencyRuleDB
        The urgency rule row.
    """

    now = datetime.now(timezone.utc)
    return UrgencyRuleDB(
        created_datetime_utc=now,
        updated_datetime_utc=now,
        urgency_rule_id=urgency_rule_id,
        urgency_rule_metadata={"k": "v"},
        urgency_rule_text="t",
        workspace_id=WORKSPACE.workspace_id,
    )


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Mock every repository / lookup function the service calls.

    Defaults describe the happy path: the workspace exists, the caller is an
    admin and rule 7 exists. Tests override `return_value`/`side_effect` as needed.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    SimpleNamespace
        The mocks, keyed by the name of the function they replace.
    """

    mocks = SimpleNamespace(
        delete_urgency_rule_from_db=AsyncMock(),
        get_urgency_rule_by_id_from_db=AsyncMock(return_value=_rule_db()),
        get_urgency_rules_from_db=AsyncMock(return_value=[]),
        get_workspace_by_workspace_name=AsyncMock(return_value=WORKSPACE),
        save_urgency_rule_to_db=AsyncMock(return_value=_rule_db()),
        update_urgency_rule_in_db=AsyncMock(return_value=_rule_db()),
        user_has_required_role_in_workspace=AsyncMock(return_value=True),
    )
    for name, mock in vars(mocks).items():
        monkeypatch.setattr(f"{SERVICE}.{name}", mock)
    # The service tags the current Langfuse trace; there is none in unit tests.
    mocks.langfuse_context = MagicMock()
    monkeypatch.setattr(f"{SERVICE}.langfuse_context", mocks.langfuse_context)
    return mocks


async def test_convert_record_to_schema() -> None:
    """Test converting a record to a schema."""

    _id = 1
    workspace_id = 123
    record = UrgencyRuleDB(
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
        urgency_rule_id=_id,
        urgency_rule_metadata={"extra_field": "extra value"},
        urgency_rule_text="sample text",
        urgency_rule_vector=await async_fake_embedding(),
        workspace_id=workspace_id,
    )
    result = _convert_record_to_schema(urgency_rule_db=record)
    assert result.urgency_rule_id == _id
    assert result.workspace_id == workspace_id
    assert result.urgency_rule_text == "sample text"
    assert result.urgency_rule_metadata["extra_field"] == "extra value"


@pytest.mark.parametrize(
    "call, action",
    [
        (
            lambda: service.create_urgency_rule(
                asession=AsyncMock(),
                calling_user_db=USER,
                urgency_rule=RULE_IN,
                workspace_name="ws",
            ),
            "create",
        ),
        (
            lambda: service.update_urgency_rule(
                asession=AsyncMock(),
                calling_user_db=USER,
                urgency_rule=RULE_IN,
                urgency_rule_id=7,
                workspace_name="ws",
            ),
            "update",
        ),
        (
            lambda: service.delete_urgency_rule(
                asession=AsyncMock(),
                calling_user_db=USER,
                urgency_rule_id=7,
                workspace_name="ws",
            ),
            "delete",
        ),
    ],
    ids=["create", "update", "delete"],
)
async def test_non_admin_is_forbidden(
    action: str, call: Callable[[], Awaitable[object]], repo: SimpleNamespace
) -> None:
    """Non-admins cannot create, update or delete rules, and nothing is written.

    Parameters
    ----------
    action
        The verb expected in the error message.
    call
        Zero-argument callable returning the service coroutine.
    repo
        The repository mocks.
    """

    repo.user_has_required_role_in_workspace.return_value = False

    with pytest.raises(ForbiddenError, match=f"to {action} urgency rules"):
        await call()

    repo.save_urgency_rule_to_db.assert_not_awaited()
    repo.update_urgency_rule_in_db.assert_not_awaited()
    repo.delete_urgency_rule_from_db.assert_not_awaited()


class TestCreateUrgencyRule:
    """Tests for `create_urgency_rule`."""

    async def test_creates_rule(self, repo: SimpleNamespace) -> None:
        """The rule is saved in the caller's workspace and returned as a schema.

        Parameters
        ----------
        repo
            The repository mocks.
        """

        asession = AsyncMock()

        result = await service.create_urgency_rule(
            asession=asession,
            calling_user_db=USER,
            urgency_rule=RULE_IN,
            workspace_name="ws",
        )

        assert result == _convert_record_to_schema(
            urgency_rule_db=repo.save_urgency_rule_to_db.return_value
        )
        repo.save_urgency_rule_to_db.assert_awaited_once_with(
            asession=asession, urgency_rule=RULE_IN, workspace_id=5
        )
        repo.langfuse_context.update_current_trace.assert_called_once_with(
            name="create_urgency_rule",
            metadata={"urgency_rule_id": 7, "workspace_id": 5},
        )

    async def test_embedding_error_is_502(self, repo: SimpleNamespace) -> None:
        """An embedding failure becomes a 502 `AppError`.

        Parameters
        ----------
        repo
            The repository mocks.
        """

        repo.save_urgency_rule_to_db.side_effect = EmbeddingCallException("down")

        with pytest.raises(AppError) as exc_info:
            await service.create_urgency_rule(
                asession=AsyncMock(),
                calling_user_db=USER,
                urgency_rule=RULE_IN,
                workspace_name="ws",
            )

        assert exc_info.value.status_code == 502
        assert isinstance(exc_info.value.__cause__, EmbeddingCallException)


class TestUpdateUrgencyRule:
    """Tests for `update_urgency_rule`."""

    async def test_updates_rule(self, repo: SimpleNamespace) -> None:
        """An existing rule is updated and returned as a schema.

        Parameters
        ----------
        repo
            The repository mocks.
        """

        asession = AsyncMock()

        result = await service.update_urgency_rule(
            asession=asession,
            calling_user_db=USER,
            urgency_rule=RULE_IN,
            urgency_rule_id=7,
            workspace_name="ws",
        )

        assert result.urgency_rule_id == 7
        repo.update_urgency_rule_in_db.assert_awaited_once_with(
            asession=asession, urgency_rule=RULE_IN, urgency_rule_id=7, workspace_id=5
        )
        repo.langfuse_context.update_current_trace.assert_called_once_with(
            name="update_urgency_rule",
            metadata={"urgency_rule_id": 7, "workspace_id": 5},
        )

    async def test_missing_rule_is_not_found(self, repo: SimpleNamespace) -> None:
        """Updating a rule that is not in the workspace raises `NotFoundError`.

        Parameters
        ----------
        repo
            The repository mocks.
        """

        repo.get_urgency_rule_by_id_from_db.return_value = None

        with pytest.raises(NotFoundError, match="`7` not found"):
            await service.update_urgency_rule(
                asession=AsyncMock(),
                calling_user_db=USER,
                urgency_rule=RULE_IN,
                urgency_rule_id=7,
                workspace_name="ws",
            )

        repo.update_urgency_rule_in_db.assert_not_awaited()

    async def test_embedding_error_is_502(self, repo: SimpleNamespace) -> None:
        """An embedding failure becomes a 502 `AppError`.

        Parameters
        ----------
        repo
            The repository mocks.
        """

        repo.update_urgency_rule_in_db.side_effect = EmbeddingCallException("down")

        with pytest.raises(AppError) as exc_info:
            await service.update_urgency_rule(
                asession=AsyncMock(),
                calling_user_db=USER,
                urgency_rule=RULE_IN,
                urgency_rule_id=7,
                workspace_name="ws",
            )

        assert exc_info.value.status_code == 502


class TestDeleteUrgencyRule:
    """Tests for `delete_urgency_rule`."""

    async def test_deletes_rule(self, repo: SimpleNamespace) -> None:
        """An existing rule is deleted from the caller's workspace.

        Parameters
        ----------
        repo
            The repository mocks.
        """

        asession = AsyncMock()

        await service.delete_urgency_rule(
            asession=asession,
            calling_user_db=USER,
            urgency_rule_id=7,
            workspace_name="ws",
        )

        repo.delete_urgency_rule_from_db.assert_awaited_once_with(
            asession=asession, urgency_rule_id=7, workspace_id=5
        )

    async def test_missing_rule_is_not_found(self, repo: SimpleNamespace) -> None:
        """Deleting a rule that is not in the workspace raises `NotFoundError`.

        Parameters
        ----------
        repo
            The repository mocks.
        """

        repo.get_urgency_rule_by_id_from_db.return_value = None

        with pytest.raises(NotFoundError):
            await service.delete_urgency_rule(
                asession=AsyncMock(),
                calling_user_db=USER,
                urgency_rule_id=7,
                workspace_name="ws",
            )

        repo.delete_urgency_rule_from_db.assert_not_awaited()


class TestGetUrgencyRules:
    """Tests for the read-only service functions."""

    async def test_get_urgency_rule(self, repo: SimpleNamespace) -> None:
        """A single rule is returned without any role check.

        Parameters
        ----------
        repo
            The repository mocks.
        """

        result = await service.get_urgency_rule(
            asession=AsyncMock(), urgency_rule_id=7, workspace_name="ws"
        )

        assert result.urgency_rule_id == 7
        repo.user_has_required_role_in_workspace.assert_not_awaited()

    async def test_get_urgency_rule_not_found(self, repo: SimpleNamespace) -> None:
        """A missing rule raises `NotFoundError`.

        Parameters
        ----------
        repo
            The repository mocks.
        """

        repo.get_urgency_rule_by_id_from_db.return_value = None

        with pytest.raises(NotFoundError):
            await service.get_urgency_rule(
                asession=AsyncMock(), urgency_rule_id=7, workspace_name="ws"
            )

    async def test_get_urgency_rules(self, repo: SimpleNamespace) -> None:
        """All rules in the workspace are returned in repository order.

        Parameters
        ----------
        repo
            The repository mocks.
        """

        repo.get_urgency_rules_from_db.return_value = [_rule_db(2), _rule_db(1)]
        asession = AsyncMock()

        result = await service.get_urgency_rules(asession=asession, workspace_name="ws")

        assert [rule.urgency_rule_id for rule in result] == [2, 1]
        repo.get_urgency_rules_from_db.assert_awaited_once_with(
            asession=asession, workspace_id=5
        )
