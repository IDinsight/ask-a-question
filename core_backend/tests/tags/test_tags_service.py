"""Unit tests for `app.tags.service`.

No database or network access: repository functions are replaced (as imported in
`app.tags.service`) with `AsyncMock`s and `AsyncMock()` stands in for the session.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.tags import service
from app.tags.models import TagDB
from app.tags.schemas import TagCreate
from app.tags.service import _convert_record_to_schema
from app.users.models import UserDB
from app.workspaces.models import WorkspaceDB

WORKSPACE_ID = 7
WORKSPACE_NAME = "unit_test_workspace"
USER = UserDB(user_id=1, username="unit_test_user")


def _tag_record(*, tag_id: int = 1, tag_name: str = "TAG") -> TagDB:
    """Build a transient `TagDB` row.

    Parameters
    ----------
    tag_id
        The tag ID.
    tag_name
        The tag name.

    Returns
    -------
    TagDB
        The (unsaved) tag record.
    """

    now = datetime.now(timezone.utc)
    return TagDB(
        created_datetime_utc=now,
        tag_id=tag_id,
        tag_name=tag_name,
        updated_datetime_utc=now,
        workspace_id=WORKSPACE_ID,
    )


@pytest.fixture
def patch_service(monkeypatch: pytest.MonkeyPatch) -> Callable[..., AsyncMock]:
    """Return a helper that replaces a name in `app.tags.service` with an
    `AsyncMock`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    Callable[..., AsyncMock]
        `patch(name, **mock_kwargs)` -> the installed mock.
    """

    def _patch(name: str, **mock_kwargs: Any) -> AsyncMock:
        mock = AsyncMock(**mock_kwargs)
        monkeypatch.setattr(service, name, mock)
        return mock

    return _patch


@pytest.fixture
def admin(patch_service: Callable[..., AsyncMock]) -> WorkspaceDB:
    """Make the calling user an admin of the test workspace.

    Parameters
    ----------
    patch_service
        Helper to patch service-level names.

    Returns
    -------
    WorkspaceDB
        The workspace returned by the mocked workspace lookup.
    """

    workspace_db = WorkspaceDB(workspace_id=WORKSPACE_ID, workspace_name=WORKSPACE_NAME)
    patch_service("get_workspace_by_workspace_name", return_value=workspace_db)
    patch_service("user_has_required_role_in_workspace", return_value=True)
    return workspace_db


def test_convert_record_to_schema() -> None:
    """Test converting a record to a schema."""

    tag_id = 1
    workspace_id = 123
    record = TagDB(
        created_datetime_utc=datetime.now(timezone.utc),
        tag_id=tag_id,
        tag_name="tag",
        updated_datetime_utc=datetime.now(timezone.utc),
        workspace_id=workspace_id,
    )
    result = _convert_record_to_schema(record=record)
    assert result.tag_id == tag_id
    assert result.workspace_id == workspace_id
    assert result.tag_name == "tag"


# Every admin-only service function, with the arguments it needs.
_ADMIN_ONLY_CALLS: list[tuple[str, Callable[[], Coroutine[Any, Any, Any]]]] = [
    (
        "create_tag",
        lambda: service.create_tag(
            asession=AsyncMock(),
            calling_user_db=USER,
            tag=TagCreate(tag_name="t"),
            workspace_name=WORKSPACE_NAME,
        ),
    ),
    (
        "edit_tag",
        lambda: service.edit_tag(
            asession=AsyncMock(),
            calling_user_db=USER,
            tag=TagCreate(tag_name="t"),
            tag_id=1,
            workspace_name=WORKSPACE_NAME,
        ),
    ),
    (
        "delete_tag",
        lambda: service.delete_tag(
            asession=AsyncMock(),
            calling_user_db=USER,
            tag_id=1,
            workspace_name=WORKSPACE_NAME,
        ),
    ),
]


@pytest.mark.parametrize(
    "call", [c[1] for c in _ADMIN_ONLY_CALLS], ids=[c[0] for c in _ADMIN_ONLY_CALLS]
)
async def test_admin_only_functions_reject_non_admins(
    admin: WorkspaceDB,
    call: Callable[[], Coroutine[Any, Any, Any]],
    patch_service: Callable[..., AsyncMock],
) -> None:
    """Creating, editing and deleting tags raise `ForbiddenError` for non-admins.

    Parameters
    ----------
    admin
        The mocked workspace (role check overridden below).
    call
        Zero-argument factory for the service coroutine under test.
    patch_service
        Helper to patch service-level names.
    """

    patch_service("user_has_required_role_in_workspace", return_value=False)
    with pytest.raises(ForbiddenError):
        await call()


class TestCreateTag:
    """Tests for `create_tag`."""

    async def test_success_uppercases_name(
        self, admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """Tag names are upper-cased before the uniqueness check and save.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        """

        unique = patch_service("is_tag_name_unique", return_value=True)
        save = patch_service(
            "save_tag_to_db", return_value=_tag_record(tag_id=4, tag_name="NEW")
        )

        result = await service.create_tag(
            asession=AsyncMock(),
            calling_user_db=USER,
            tag=TagCreate(tag_name="new"),
            workspace_name=WORKSPACE_NAME,
        )

        assert result.tag_id == 4
        assert unique.await_args is not None
        assert unique.await_args.kwargs["tag_name"] == "NEW"
        assert save.await_args is not None
        assert save.await_args.kwargs["tag"].tag_name == "NEW"
        assert save.await_args.kwargs["workspace_id"] == WORKSPACE_ID

    async def test_duplicate_name(
        self, admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """A name that already exists raises `BadRequestError` and is not saved.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        """

        patch_service("is_tag_name_unique", return_value=False)
        save = patch_service("save_tag_to_db")

        with pytest.raises(BadRequestError, match="`DUP` already exists"):
            await service.create_tag(
                asession=AsyncMock(),
                calling_user_db=USER,
                tag=TagCreate(tag_name="dup"),
                workspace_name=WORKSPACE_NAME,
            )
        save.assert_not_awaited()


class TestEditTag:
    """Tests for `edit_tag`."""

    @staticmethod
    async def _edit(tag_name: str) -> Any:
        """Call `edit_tag` with fixed arguments.

        Parameters
        ----------
        tag_name
            The new tag name.

        Returns
        -------
        Any
            The service result.
        """

        return await service.edit_tag(
            asession=AsyncMock(),
            calling_user_db=USER,
            tag=TagCreate(tag_name=tag_name),
            tag_id=1,
            workspace_name=WORKSPACE_NAME,
        )

    async def test_not_found(
        self, admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """Editing an unknown tag raises `NotFoundError`.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        """

        patch_service("get_tag_from_db", return_value=None)
        with pytest.raises(NotFoundError):
            await self._edit("x")

    @pytest.mark.parametrize(
        "new_name, is_unique, expect_check, expect_error",
        [
            ("old", False, False, False),
            ("other", True, True, False),
            ("other", False, True, True),
        ],
        ids=["same_name_skips_check", "renamed_unique", "renamed_duplicate"],
    )
    async def test_uniqueness_checked_only_on_rename(
        self,
        admin: WorkspaceDB,
        expect_check: bool,
        expect_error: bool,
        is_unique: bool,
        new_name: str,
        patch_service: Callable[..., AsyncMock],
    ) -> None:
        """Uniqueness is only checked when the (upper-cased) name changes.

        Parameters
        ----------
        admin
            The mocked workspace.
        expect_check
            Whether `is_tag_name_unique` should be awaited.
        expect_error
            Whether `BadRequestError` should be raised.
        is_unique
            The mocked uniqueness result.
        new_name
            The requested tag name.
        patch_service
            Helper to patch service-level names.
        """

        patch_service("get_tag_from_db", return_value=_tag_record(tag_name="OLD"))
        unique = patch_service("is_tag_name_unique", return_value=is_unique)
        update = patch_service(
            "update_tag_in_db",
            return_value=_tag_record(tag_name=new_name.upper()),
        )

        if expect_error:
            with pytest.raises(BadRequestError):
                await self._edit(new_name)
            update.assert_not_awaited()
        else:
            result = await self._edit(new_name)
            assert result.tag_name == new_name.upper()
        assert unique.await_count == int(expect_check)


async def test_retrieve_tag_passes_paging(
    admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
) -> None:
    """`skip` becomes the repository `offset` and records are converted.

    Parameters
    ----------
    admin
        The mocked workspace.
    patch_service
        Helper to patch service-level names.
    """

    get_list = patch_service(
        "get_list_of_tag_from_db",
        return_value=[_tag_record(tag_id=1), _tag_record(tag_id=2)],
    )

    result = await service.retrieve_tag(
        asession=AsyncMock(), limit=5, skip=3, workspace_name=WORKSPACE_NAME
    )

    assert [t.tag_id for t in result] == [1, 2]
    assert get_list.await_args is not None
    assert get_list.await_args.kwargs["offset"] == 3
    assert get_list.await_args.kwargs["limit"] == 5


@pytest.mark.parametrize("found", [True, False])
async def test_delete_tag(
    admin: WorkspaceDB, found: bool, patch_service: Callable[..., AsyncMock]
) -> None:
    """Existing tags are deleted; unknown tags raise `NotFoundError`.

    Parameters
    ----------
    admin
        The mocked workspace.
    found
        Whether the tag exists.
    patch_service
        Helper to patch service-level names.
    """

    patch_service("get_tag_from_db", return_value=_tag_record() if found else None)
    delete = patch_service("delete_tag_from_db")

    async def _call() -> None:
        await service.delete_tag(
            asession=AsyncMock(),
            calling_user_db=USER,
            tag_id=1,
            workspace_name=WORKSPACE_NAME,
        )

    if found:
        await _call()
        assert delete.await_args is not None
        assert delete.await_args.kwargs == {
            "asession": delete.await_args.kwargs["asession"],
            "tag_id": 1,
            "workspace_id": WORKSPACE_ID,
        }
    else:
        with pytest.raises(NotFoundError):
            await _call()
        delete.assert_not_awaited()


@pytest.mark.parametrize("found", [True, False])
async def test_retrieve_tag_by_id(
    admin: WorkspaceDB, found: bool, patch_service: Callable[..., AsyncMock]
) -> None:
    """A known tag is returned; an unknown one raises `NotFoundError`.

    Parameters
    ----------
    admin
        The mocked workspace.
    found
        Whether the tag exists.
    patch_service
        Helper to patch service-level names.
    """

    patch_service(
        "get_tag_from_db", return_value=_tag_record(tag_id=9) if found else None
    )

    async def _call() -> Any:
        return await service.retrieve_tag_by_id(
            asession=AsyncMock(), tag_id=9, workspace_name=WORKSPACE_NAME
        )

    if found:
        assert (await _call()).tag_id == 9
    else:
        with pytest.raises(NotFoundError):
            await _call()
