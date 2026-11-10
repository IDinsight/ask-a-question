"""Unit tests for `app.contents.service`.

These tests never touch the database or the network: every repository function is
replaced (as imported in `app.contents.service`) with an `AsyncMock`, and a bare
`AsyncMock()` stands in for the SQLAlchemy session.
"""

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Callable, Coroutine
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest
import sqlalchemy.exc

from app.contents import service
from app.contents.models import ContentDB
from app.contents.schemas import ContentCreate, ContentRetrieve, CustomError
from app.contents.service import (
    ExceedsContentQuotaError,
    _check_content_quota_availability,
    _convert_record_to_schema,
    _extract_unique_tags,
    _get_tags_not_in_db,
    _load_csv,
    _validate_tags_and_related_contents,
    check_content_quota,
    check_db_duplicates,
    check_duplicates,
    check_empty_values,
    check_length_constraints,
    check_required_columns,
    clean_dataframe,
)
from app.core.exceptions import (
    AppError,
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
)
from app.core.utils import EmbeddingCallException
from app.tags.models import TagDB
from app.users.models import UserDB
from app.workspaces.models import WorkspaceDB
from tests.conftest import async_fake_embedding

WORKSPACE_ID = 7
WORKSPACE_NAME = "unit_test_workspace"
USER = UserDB(user_id=1, username="unit_test_user")


def _content_record(**overrides: Any) -> ContentDB:
    """Build a transient `ContentDB` row with sensible defaults.

    Parameters
    ----------
    overrides
        Column values that replace the defaults.

    Returns
    -------
    ContentDB
        The (unsaved) content record.
    """

    now = datetime.now(timezone.utc)
    values: dict[str, Any] = {
        "content_id": 1,
        "content_metadata": {},
        "content_text": "text",
        "content_title": "title",
        "created_datetime_utc": now,
        "display_number": 1,
        "is_archived": False,
        "is_validated": True,
        "negative_votes": 0,
        "positive_votes": 0,
        "related_contents_id": [],
        "updated_datetime_utc": now,
        "workspace_id": WORKSPACE_ID,
    }
    values.update(overrides)
    return ContentDB(**values)


def _tag_record(*, tag_id: int, tag_name: str) -> TagDB:
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


def _content_create(**overrides: Any) -> ContentCreate:
    """Build a `ContentCreate` request body.

    Parameters
    ----------
    overrides
        Field values that replace the defaults.

    Returns
    -------
    ContentCreate
        The content creation request.
    """

    values: dict[str, Any] = {"content_text": "text", "content_title": "title"}
    values.update(overrides)
    return ContentCreate(**values)


@pytest.fixture
def patch_service(monkeypatch: pytest.MonkeyPatch) -> Callable[..., AsyncMock]:
    """Return a helper that replaces a name in `app.contents.service` with an
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


@pytest.fixture
def valid_tags(patch_service: Callable[..., AsyncMock]) -> AsyncMock:
    """Make every tag ID valid (and resolve to no `TagDB` objects).

    Parameters
    ----------
    patch_service
        Helper to patch service-level names.

    Returns
    -------
    AsyncMock
        The mocked `validate_tags`.
    """

    return patch_service("validate_tags", return_value=(True, []))


async def test_convert_record_to_schema() -> None:
    """Test the conversion of a record to a schema."""

    content_id = 1
    workspace_id = 123
    record = ContentDB(
        content_embedding=await async_fake_embedding(),
        content_id=content_id,
        content_metadata={"extra_field": "extra value"},
        content_text="sample text",
        content_title="sample title for content",
        created_datetime_utc=datetime.now(timezone.utc),
        display_number=2,
        is_archived=False,
        positive_votes=0,
        negative_votes=0,
        updated_datetime_utc=datetime.now(timezone.utc),
        workspace_id=workspace_id,
    )
    result = _convert_record_to_schema(record=record)
    assert result.content_id == content_id
    assert result.workspace_id == workspace_id
    assert result.content_text == "sample text"
    assert result.content_metadata["extra_field"] == "extra value"


def test_convert_record_to_schema_maps_tags_to_ids() -> None:
    """Tag objects on the record become a list of tag IDs on the schema."""

    record = _content_record(
        content_tags=[
            _tag_record(tag_id=3, tag_name="A"),
            _tag_record(tag_id=5, tag_name="B"),
        ]
    )
    assert _convert_record_to_schema(record=record).content_tags == [3, 5]


@pytest.mark.xfail(
    strict=True,
    reason="App bug: _convert_record_to_schema does not copy is_validated, so "
    "responses always report the ContentCreate default (True).",
)
def test_convert_record_to_schema_keeps_is_validated() -> None:
    """Unvalidated records should be reported as unvalidated."""

    record = _content_record(is_validated=False)
    assert _convert_record_to_schema(record=record).is_validated is False


# Every admin-only service function, with the arguments it needs.
_ADMIN_ONLY_CALLS: list[tuple[str, Callable[[], Coroutine[Any, Any, Any]]]] = [
    (
        "create_content",
        lambda: service.create_content(
            asession=AsyncMock(),
            calling_user_db=USER,
            content=_content_create(),
            workspace_name=WORKSPACE_NAME,
        ),
    ),
    (
        "edit_content",
        lambda: service.edit_content(
            asession=AsyncMock(),
            calling_user_db=USER,
            content=_content_create(),
            content_id=1,
            exclude_archived=True,
            exclude_unvalidated=False,
            workspace_name=WORKSPACE_NAME,
        ),
    ),
    (
        "get_next_unvalidated_content",
        lambda: service.get_next_unvalidated_content(
            asession=AsyncMock(), calling_user_db=USER, workspace_name=WORKSPACE_NAME
        ),
    ),
    (
        "validate_content_card",
        lambda: service.validate_content_card(
            asession=AsyncMock(),
            calling_user_db=USER,
            content_id=1,
            workspace_name=WORKSPACE_NAME,
        ),
    ),
    (
        "get_unvalidated_card_count",
        lambda: service.get_unvalidated_card_count(
            asession=AsyncMock(), calling_user_db=USER, workspace_name=WORKSPACE_NAME
        ),
    ),
    (
        "archive_content",
        lambda: service.archive_content(
            asession=AsyncMock(),
            calling_user_db=USER,
            content_id=1,
            exclude_unvalidated=False,
            workspace_name=WORKSPACE_NAME,
        ),
    ),
    (
        "delete_content",
        lambda: service.delete_content(
            asession=AsyncMock(),
            calling_user_db=USER,
            content_id=1,
            exclude_archived=True,
            exclude_unvalidated=False,
            workspace_name=WORKSPACE_NAME,
        ),
    ),
    (
        "bulk_upload_contents",
        lambda: service.bulk_upload_contents(
            asession=AsyncMock(),
            calling_user_db=USER,
            exclude_archived=True,
            file=BytesIO(b"title,text\na,b\n"),
            filename="test.csv",
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
    """Every write/review operation raises `ForbiddenError` for non-admins.

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


class TestValidateTagsAndRelatedContents:
    """Tests for `_validate_tags_and_related_contents`."""

    async def test_invalid_tags_raise(
        self, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """Unknown tag IDs are reported in the error.

        Parameters
        ----------
        patch_service
            Helper to patch service-level names.
        """

        patch_service("validate_tags", return_value=(False, [99]))
        with pytest.raises(BadRequestError, match=r"Invalid tag IDs: \[99\]"):
            await _validate_tags_and_related_contents(
                asession=AsyncMock(),
                content=_content_create(content_tags=[99]),
                workspace_id=WORKSPACE_ID,
            )

    async def test_no_related_contents_skips_lookup(
        self, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """Valid tags are swapped in and related contents are not looked up when
        none are given.

        Parameters
        ----------
        patch_service
            Helper to patch service-level names.
        """

        tag = _tag_record(tag_id=1, tag_name="A")
        patch_service("validate_tags", return_value=(True, [tag]))
        related = patch_service("validate_related_contents")
        content = _content_create(content_tags=[1])

        await _validate_tags_and_related_contents(
            asession=AsyncMock(), content=content, workspace_id=WORKSPACE_ID
        )

        assert content.content_tags == [tag]
        related.assert_not_awaited()

    @pytest.mark.parametrize(
        "lookup_result, expected_ids",
        [((True, [1, 2]), [1, 2]), ((False, [2]), [2])],
        ids=["all_valid", "partially_valid"],
    )
    async def test_valid_related_contents_are_kept(
        self,
        expected_ids: list[int],
        lookup_result: tuple[bool, list[int]],
        patch_service: Callable[..., AsyncMock],
        valid_tags: AsyncMock,
    ) -> None:
        """Only related contents that exist are kept; partial matches are allowed.

        Parameters
        ----------
        expected_ids
            The related content IDs expected on the content afterwards.
        lookup_result
            The mocked return value of `validate_related_contents`.
        patch_service
            Helper to patch service-level names.
        valid_tags
            Mocked `validate_tags` that accepts every tag.
        """

        patch_service("validate_related_contents", return_value=lookup_result)
        content = _content_create(related_contents_id=[1, 2])

        await _validate_tags_and_related_contents(
            asession=AsyncMock(), content=content, workspace_id=WORKSPACE_ID
        )

        assert content.related_contents_id == expected_ids

    async def test_all_invalid_related_contents_raise(
        self, patch_service: Callable[..., AsyncMock], valid_tags: AsyncMock
    ) -> None:
        """A request whose related contents are all unknown is rejected.

        Parameters
        ----------
        patch_service
            Helper to patch service-level names.
        valid_tags
            Mocked `validate_tags` that accepts every tag.
        """

        patch_service("validate_related_contents", return_value=(False, []))
        with pytest.raises(BadRequestError, match="Invalid related content IDs"):
            await _validate_tags_and_related_contents(
                asession=AsyncMock(),
                content=_content_create(related_contents_id=[123]),
                workspace_id=WORKSPACE_ID,
            )


class TestCreateContent:
    """Tests for `create_content`."""

    @pytest.mark.parametrize("check_limit", [True, False])
    async def test_success(
        self,
        admin: WorkspaceDB,
        check_limit: bool,
        monkeypatch: pytest.MonkeyPatch,
        patch_service: Callable[..., AsyncMock],
        valid_tags: AsyncMock,
    ) -> None:
        """Content is saved and returned; the quota is checked only when enabled.

        Parameters
        ----------
        admin
            The mocked workspace.
        check_limit
            Value of the `CHECK_CONTENT_LIMIT` setting.
        monkeypatch
            Pytest monkeypatch fixture.
        patch_service
            Helper to patch service-level names.
        valid_tags
            Mocked `validate_tags` that accepts every tag.
        """

        monkeypatch.setattr(service, "CHECK_CONTENT_LIMIT", check_limit)
        quota = patch_service("_check_content_quota_availability")
        save = patch_service("save_content_to_db", return_value=_content_record())

        result = await service.create_content(
            asession=AsyncMock(),
            calling_user_db=USER,
            content=_content_create(),
            workspace_name=WORKSPACE_NAME,
        )

        assert isinstance(result, ContentRetrieve)
        assert quota.await_count == int(check_limit)
        # Newly saved content must be returned even if it is archived.
        assert save.await_args is not None
        assert save.await_args.kwargs["exclude_archived"] is False
        assert save.await_args.kwargs["workspace_id"] == WORKSPACE_ID

    async def test_quota_exceeded(
        self,
        admin: WorkspaceDB,
        monkeypatch: pytest.MonkeyPatch,
        patch_service: Callable[..., AsyncMock],
        valid_tags: AsyncMock,
    ) -> None:
        """Exceeding the content quota is reported as `ForbiddenError`.

        Parameters
        ----------
        admin
            The mocked workspace.
        monkeypatch
            Pytest monkeypatch fixture.
        patch_service
            Helper to patch service-level names.
        valid_tags
            Mocked `validate_tags` that accepts every tag.
        """

        monkeypatch.setattr(service, "CHECK_CONTENT_LIMIT", True)
        patch_service(
            "_check_content_quota_availability",
            side_effect=ExceedsContentQuotaError("over"),
        )
        save = patch_service("save_content_to_db")

        with pytest.raises(ForbiddenError, match="Exceeds content quota"):
            await service.create_content(
                asession=AsyncMock(),
                calling_user_db=USER,
                content=_content_create(),
                workspace_name=WORKSPACE_NAME,
            )
        save.assert_not_awaited()

    async def test_embedding_failure_returns_bad_gateway(
        self,
        admin: WorkspaceDB,
        monkeypatch: pytest.MonkeyPatch,
        patch_service: Callable[..., AsyncMock],
        valid_tags: AsyncMock,
    ) -> None:
        """An embedding-service failure becomes a 502 `AppError`.

        Parameters
        ----------
        admin
            The mocked workspace.
        monkeypatch
            Pytest monkeypatch fixture.
        patch_service
            Helper to patch service-level names.
        valid_tags
            Mocked `validate_tags` that accepts every tag.
        """

        monkeypatch.setattr(service, "CHECK_CONTENT_LIMIT", False)
        patch_service("save_content_to_db", side_effect=EmbeddingCallException())

        with pytest.raises(AppError) as exc_info:
            await service.create_content(
                asession=AsyncMock(),
                calling_user_db=USER,
                content=_content_create(),
                workspace_name=WORKSPACE_NAME,
            )
        assert exc_info.value.status_code == 502


class TestEditContent:
    """Tests for `edit_content`."""

    @staticmethod
    async def _edit(content: ContentCreate) -> ContentRetrieve:
        """Call `edit_content` with fixed arguments.

        Parameters
        ----------
        content
            The new content.

        Returns
        -------
        ContentRetrieve
            The edited content.
        """

        return await service.edit_content(
            asession=AsyncMock(),
            calling_user_db=USER,
            content=content,
            content_id=1,
            exclude_archived=False,
            exclude_unvalidated=False,
            workspace_name=WORKSPACE_NAME,
        )

    async def test_not_found(
        self, admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """Editing unknown content raises `NotFoundError`.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        """

        patch_service("get_content_from_db", return_value=None)
        with pytest.raises(NotFoundError):
            await self._edit(_content_create())

    async def test_keeps_archive_status(
        self,
        admin: WorkspaceDB,
        patch_service: Callable[..., AsyncMock],
        valid_tags: AsyncMock,
    ) -> None:
        """Editing never changes `is_archived`, whatever the request says.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        valid_tags
            Mocked `validate_tags` that accepts every tag.
        """

        patch_service(
            "get_content_from_db", return_value=_content_record(is_archived=True)
        )
        update = patch_service(
            "update_content_in_db", return_value=_content_record(is_archived=True)
        )

        result = await self._edit(_content_create(is_archived=False))

        assert update.await_args is not None
        assert update.await_args.kwargs["content"].is_archived is True
        assert result.is_archived is True

    async def test_embedding_failure_returns_bad_gateway(
        self,
        admin: WorkspaceDB,
        patch_service: Callable[..., AsyncMock],
        valid_tags: AsyncMock,
    ) -> None:
        """An embedding-service failure becomes a 502 `AppError`.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        valid_tags
            Mocked `validate_tags` that accepts every tag.
        """

        patch_service("get_content_from_db", return_value=_content_record())
        patch_service("update_content_in_db", side_effect=EmbeddingCallException())

        with pytest.raises(AppError) as exc_info:
            await self._edit(_content_create())
        assert exc_info.value.status_code == 502


async def test_retrieve_content_passes_paging(
    admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
) -> None:
    """`skip` is passed to the repository as `offset` and records are converted.

    Parameters
    ----------
    admin
        The mocked workspace.
    patch_service
        Helper to patch service-level names.
    """

    get_list = patch_service(
        "get_list_of_content_from_db",
        return_value=[_content_record(content_id=1), _content_record(content_id=2)],
    )

    result = await service.retrieve_content(
        asession=AsyncMock(),
        exclude_archived=True,
        exclude_unvalidated=False,
        limit=10,
        skip=5,
        workspace_name=WORKSPACE_NAME,
    )

    assert [c.content_id for c in result] == [1, 2]
    assert get_list.await_args is not None
    assert get_list.await_args.kwargs["offset"] == 5
    assert get_list.await_args.kwargs["limit"] == 10


class TestUnvalidatedQueue:
    """Tests for the unvalidated-content functions."""

    async def test_next_unvalidated_none(
        self, admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """An empty queue raises `NotFoundError`.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        """

        patch_service("get_next_unvalidated_content_card", return_value=None)
        with pytest.raises(NotFoundError):
            await service.get_next_unvalidated_content(
                asession=AsyncMock(), calling_user_db=USER, workspace_name="w"
            )

    async def test_next_unvalidated_found(
        self, admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """The next card is converted to a schema.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        """

        patch_service(
            "get_next_unvalidated_content_card",
            return_value=_content_record(content_id=4, is_validated=False),
        )
        result = await service.get_next_unvalidated_content(
            asession=AsyncMock(), calling_user_db=USER, workspace_name="w"
        )
        assert result.content_id == 4

    async def test_validate_not_found(
        self, admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """Validating unknown content raises `NotFoundError` and changes nothing.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        """

        patch_service("get_content_from_db", return_value=None)
        mark = patch_service("mark_content_as_validated")
        with pytest.raises(NotFoundError):
            await service.validate_content_card(
                asession=AsyncMock(),
                calling_user_db=USER,
                content_id=1,
                workspace_name="w",
            )
        mark.assert_not_awaited()

    async def test_validate_success(
        self, admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """Validation looks up unvalidated content too, then marks it validated.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        """

        get_content = patch_service(
            "get_content_from_db", return_value=_content_record()
        )
        mark = patch_service("mark_content_as_validated")

        await service.validate_content_card(
            asession=AsyncMock(), calling_user_db=USER, content_id=3, workspace_name="w"
        )

        assert get_content.await_args is not None
        assert get_content.await_args.kwargs["exclude_unvalidated"] is False
        assert mark.await_args is not None
        assert mark.await_args.kwargs["content_id"] == 3
        assert mark.await_args.kwargs["workspace_id"] == WORKSPACE_ID

    @pytest.mark.parametrize("count, expected", [(None, -1), (0, 0), (5, 5)])
    async def test_unvalidated_count(
        self,
        admin: WorkspaceDB,
        count: int | None,
        expected: int,
        patch_service: Callable[..., AsyncMock],
    ) -> None:
        """A missing count is reported as -1.

        Parameters
        ----------
        admin
            The mocked workspace.
        count
            The count returned by the repository.
        expected
            The expected service result.
        patch_service
            Helper to patch service-level names.
        """

        patch_service("get_unvalidated_count", return_value=count)
        result = await service.get_unvalidated_card_count(
            asession=AsyncMock(), calling_user_db=USER, workspace_name="w"
        )
        assert result == expected


class TestArchiveAndDelete:
    """Tests for `archive_content` and `delete_content`."""

    @staticmethod
    async def _archive() -> None:
        """Call `archive_content` with fixed arguments."""

        await service.archive_content(
            asession=AsyncMock(),
            calling_user_db=USER,
            content_id=1,
            exclude_unvalidated=False,
            workspace_name=WORKSPACE_NAME,
        )

    @staticmethod
    async def _delete() -> None:
        """Call `delete_content` with fixed arguments."""

        await service.delete_content(
            asession=AsyncMock(),
            calling_user_db=USER,
            content_id=1,
            exclude_archived=True,
            exclude_unvalidated=False,
            workspace_name=WORKSPACE_NAME,
        )

    @pytest.mark.parametrize(
        "operation, repo_function",
        [
            ("_archive", "archive_content_from_db"),
            ("_delete", "delete_content_from_db"),
        ],
    )
    async def test_not_found(
        self,
        admin: WorkspaceDB,
        operation: str,
        patch_service: Callable[..., AsyncMock],
        repo_function: str,
    ) -> None:
        """Unknown content raises `NotFoundError` before any write.

        Parameters
        ----------
        admin
            The mocked workspace.
        operation
            Name of the helper that calls the service function.
        patch_service
            Helper to patch service-level names.
        repo_function
            The repository write function that must not be called.
        """

        patch_service("get_content_from_db", return_value=None)
        write = patch_service(repo_function)
        with pytest.raises(NotFoundError):
            await getattr(self, operation)()
        write.assert_not_awaited()

    @pytest.mark.parametrize(
        "operation, repo_function",
        [
            ("_archive", "archive_content_from_db"),
            ("_delete", "delete_content_from_db"),
        ],
    )
    async def test_success(
        self,
        admin: WorkspaceDB,
        operation: str,
        patch_service: Callable[..., AsyncMock],
        repo_function: str,
    ) -> None:
        """Existing content is archived/deleted in the caller's workspace.

        Parameters
        ----------
        admin
            The mocked workspace.
        operation
            Name of the helper that calls the service function.
        patch_service
            Helper to patch service-level names.
        repo_function
            The repository write function that must be called.
        """

        patch_service("get_content_from_db", return_value=_content_record())
        write = patch_service(repo_function)
        await getattr(self, operation)()
        assert write.await_args is not None
        assert write.await_args.kwargs["workspace_id"] == WORKSPACE_ID

    async def test_delete_with_feedback_is_rejected(
        self, admin: WorkspaceDB, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """A foreign-key violation (content has feedback) becomes a 500.

        Parameters
        ----------
        admin
            The mocked workspace.
        patch_service
            Helper to patch service-level names.
        """

        patch_service("get_content_from_db", return_value=_content_record())
        patch_service(
            "delete_content_from_db",
            side_effect=sqlalchemy.exc.IntegrityError("DELETE", {}, Exception("fk")),
        )
        with pytest.raises(InternalServerError, match="feedback"):
            await self._delete()


@pytest.mark.parametrize("record_found", [True, False])
async def test_retrieve_content_by_id(
    admin: WorkspaceDB, patch_service: Callable[..., AsyncMock], record_found: bool
) -> None:
    """Content is returned when found, otherwise `NotFoundError` is raised.

    Parameters
    ----------
    admin
        The mocked workspace.
    patch_service
        Helper to patch service-level names.
    record_found
        Whether the repository finds the content.
    """

    record = _content_record(content_id=9) if record_found else None
    patch_service("get_content_from_db", return_value=record)

    async def _call() -> ContentRetrieve:
        return await service.retrieve_content_by_id(
            asession=AsyncMock(),
            content_id=9,
            exclude_archived=True,
            exclude_unvalidated=True,
            workspace_name=WORKSPACE_NAME,
        )

    if record_found:
        assert (await _call()).content_id == 9
    else:
        with pytest.raises(NotFoundError):
            await _call()


class TestBulkUpload:
    """Tests for `bulk_upload_contents`."""

    @pytest.fixture
    def no_quota_and_empty_db(
        self, patch_service: Callable[..., AsyncMock]
    ) -> AsyncMock:
        """Mock the CSV checks' DB lookups: no quota and no existing contents.

        Parameters
        ----------
        patch_service
            Helper to patch service-level names.

        Returns
        -------
        AsyncMock
            The mocked `save_content_to_db`, which echoes the title/text it is given.
        """

        patch_service("get_content_quota_by_workspace_id", return_value=None)
        patch_service("get_list_of_content_from_db", return_value=[])

        async def _save(*, content: ContentCreate, **kwargs: Any) -> ContentDB:
            return _content_record(
                content_text=content.content_text, content_title=content.content_title
            )

        return patch_service("save_content_to_db", side_effect=_save)

    @staticmethod
    async def _upload(csv: bytes, filename: str | None = "test.csv") -> Any:
        """Call `bulk_upload_contents` with the given CSV bytes.

        Parameters
        ----------
        csv
            The raw CSV file content.
        filename
            The uploaded file's name.

        Returns
        -------
        Any
            The service result.
        """

        return await service.bulk_upload_contents(
            asession=AsyncMock(),
            calling_user_db=USER,
            exclude_archived=True,
            file=BytesIO(csv),
            filename=filename,
            workspace_name=WORKSPACE_NAME,
        )

    @pytest.mark.parametrize("filename", [None, "test.txt"])
    async def test_rejects_non_csv(
        self, admin: WorkspaceDB, filename: str | None
    ) -> None:
        """Files without a `.csv` name are rejected before parsing.

        Parameters
        ----------
        admin
            The mocked workspace.
        filename
            The uploaded file's name.
        """

        with pytest.raises(BadRequestError) as exc_info:
            await self._upload(b"title,text\na,b\n", filename=filename)
        assert exc_info.value.detail["errors"][0]["type"] == "invalid_format"

    async def test_without_tags(
        self,
        admin: WorkspaceDB,
        no_quota_and_empty_db: AsyncMock,
        patch_service: Callable[..., AsyncMock],
    ) -> None:
        """A CSV without a tags column creates contents and no tags.

        Parameters
        ----------
        admin
            The mocked workspace.
        no_quota_and_empty_db
            Mocked DB lookups and content saving.
        patch_service
            Helper to patch service-level names.
        """

        list_tags = patch_service("get_list_of_tag_from_db")

        result = await self._upload(b"title,text\n t1 ,x1\nt2,x2\n")

        assert result.tags == []
        # Titles are stripped by the CSV clean-up step.
        assert [c.content_title for c in result.contents] == ["t1", "t2"]
        list_tags.assert_not_awaited()

    async def test_with_tags(
        self,
        admin: WorkspaceDB,
        no_quota_and_empty_db: AsyncMock,
        patch_service: Callable[..., AsyncMock],
    ) -> None:
        """New tags are created once; each row is linked to its (upper-cased) tags.

        Parameters
        ----------
        admin
            The mocked workspace.
        no_quota_and_empty_db
            Mocked DB lookups and content saving.
        patch_service
            Helper to patch service-level names.
        """

        existing = _tag_record(tag_id=1, tag_name="OLD")
        created = _tag_record(tag_id=2, tag_name="NEW")
        patch_service("get_list_of_tag_from_db", return_value=[existing])
        save_tag = patch_service("save_tag_to_db", return_value=created)
        validate = patch_service("validate_tags", return_value=(True, []))

        # The second row has no tags, so it must not be validated.
        result = await self._upload(b'tags,title,text\n"old, new",t1,x1\n,t2,x2\n')

        assert [t.tag_name for t in result.tags] == ["NEW"]
        assert save_tag.await_args is not None
        assert save_tag.await_args.kwargs["tag"].tag_name == "NEW"
        validate.assert_awaited_once()
        assert validate.await_args is not None
        assert sorted(validate.await_args.kwargs["tags"]) == [1, 2]
        assert len(result.contents) == 2

    async def test_failed_checks_raise(
        self, admin: WorkspaceDB, no_quota_and_empty_db: AsyncMock
    ) -> None:
        """All CSV problems are collected into a single `BadRequestError`.

        Parameters
        ----------
        admin
            The mocked workspace.
        no_quota_and_empty_db
            Mocked DB lookups and content saving.
        """

        with pytest.raises(BadRequestError) as exc_info:
            await self._upload(b"title,text\nsame,x1\nsame,x1\n")

        error_types = {e["type"] for e in exc_info.value.detail["errors"]}
        assert error_types == {"duplicate_titles", "duplicate_texts"}
        no_quota_and_empty_db.assert_not_awaited()


@pytest.mark.parametrize(
    "csv, expected_type",
    [
        (b"", "empty_data"),
        (b"title,text\n", "no_rows_csv"),
        (b"a,b\n1,2\n1,2,3,4\n", "parse_error"),
        (b"title,text\n\xff\xfe,\xfa\n", "encoding_error"),
    ],
)
def test_load_csv_errors(csv: bytes, expected_type: str) -> None:
    """Unreadable or empty CSVs raise `BadRequestError` with a specific type.

    Parameters
    ----------
    csv
        The raw CSV bytes.
    expected_type
        The expected error type.
    """

    with pytest.raises(BadRequestError) as exc_info:
        _load_csv(file=BytesIO(csv))
    assert exc_info.value.detail["errors"][0]["type"] == expected_type


def test_load_csv_reads_strings() -> None:
    """Every column is loaded as a string so numeric-looking text is preserved."""

    df = _load_csv(file=BytesIO(b"title,text\n001,2\n"))
    assert df.loc[0, "title"] == "001"


class TestContentQuota:
    """Tests for `_check_content_quota_availability` and `check_content_quota`."""

    @staticmethod
    def _session_with_contents(n_contents: int) -> AsyncMock:
        """Build a mock session whose `execute(...).all()` returns `n_contents` rows.

        Parameters
        ----------
        n_contents
            Number of active contents already in the workspace.

        Returns
        -------
        AsyncMock
            The mocked async session.
        """

        asession = AsyncMock()
        asession.execute.return_value = MagicMock(
            all=MagicMock(return_value=[object()] * n_contents)
        )
        return asession

    async def test_no_quota_skips_count(
        self, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """A `None` quota means unlimited, so contents are not counted.

        Parameters
        ----------
        patch_service
            Helper to patch service-level names.
        """

        patch_service("get_content_quota_by_workspace_id", return_value=None)
        asession = self._session_with_contents(1000)
        await _check_content_quota_availability(
            asession=asession, n_contents_to_add=1000, workspace_id=WORKSPACE_ID
        )
        asession.execute.assert_not_awaited()

    @pytest.mark.parametrize(
        "existing, to_add, message",
        [
            (0, 5, None),
            (3, 2, None),
            (0, 6, "Adding 6 new contents to the database would exceed"),
            (4, 2, "to the already existing 4 in the database would exceed"),
        ],
        ids=["empty_within", "at_limit", "empty_over", "existing_over"],
    )
    async def test_quota_limit(
        self,
        existing: int,
        message: str | None,
        patch_service: Callable[..., AsyncMock],
        to_add: int,
    ) -> None:
        """Adding contents up to the quota is allowed; beyond it raises.

        Parameters
        ----------
        existing
            Active contents already in the workspace.
        message
            Expected error message fragment, or `None` if no error is expected.
        patch_service
            Helper to patch service-level names.
        to_add
            Number of contents to add.
        """

        patch_service("get_content_quota_by_workspace_id", return_value=5)
        asession = self._session_with_contents(existing)

        async def _check() -> None:
            await _check_content_quota_availability(
                asession=asession, n_contents_to_add=to_add, workspace_id=WORKSPACE_ID
            )

        if message is None:
            await _check()
        else:
            with pytest.raises(ExceedsContentQuotaError, match=message):
                await _check()

    async def test_check_content_quota_collects_error(
        self, patch_service: Callable[..., AsyncMock]
    ) -> None:
        """`check_content_quota` appends an error instead of raising.

        Parameters
        ----------
        patch_service
            Helper to patch service-level names.
        """

        patch_service(
            "_check_content_quota_availability",
            side_effect=ExceedsContentQuotaError("too many"),
        )
        errors: list[CustomError] = []
        await check_content_quota(
            asession=AsyncMock(),
            error_list=errors,
            n_contents_to_add=1,
            workspace_id=WORKSPACE_ID,
        )
        assert errors == [CustomError(type="exceeds_quota", description="too many")]


@pytest.mark.parametrize(
    "data, expected_types",
    [
        ({"title": ["a", "b"], "text": ["x", "y"]}, []),
        ({"title": ["a", None], "text": [None, "y"]}, ["empty_title", "empty_text"]),
        (
            {"title": ["a" * 151], "text": ["x" * 2001]},
            ["title_too_long", "texts_too_long"],
        ),
        (
            {"title": ["a", "a"], "text": ["x", "x"]},
            ["duplicate_titles", "duplicate_texts"],
        ),
    ],
    ids=["valid", "empty", "too_long", "duplicates"],
)
def test_dataframe_checks(data: dict[str, list], expected_types: list[str]) -> None:
    """The pure CSV checks append one error per failed rule.

    Parameters
    ----------
    data
        The CSV contents as columns.
    expected_types
        The expected error types, in order.
    """

    df = pd.DataFrame(data)
    errors: list[CustomError] = []
    check_empty_values(df=df, error_list=errors)
    check_length_constraints(df=df, error_list=errors)
    check_duplicates(df=df, error_list=errors)
    assert [e.type for e in errors] == expected_types


def test_check_required_columns_fails_fast() -> None:
    """A CSV missing `title`/`text` raises immediately with `missing_columns`."""

    errors: list[CustomError] = []
    with pytest.raises(BadRequestError) as exc_info:
        check_required_columns(df=pd.DataFrame({"title": ["a"]}), error_list=errors)
    assert exc_info.value.detail["errors"][0]["type"] == "missing_columns"


def test_clean_dataframe_blanks_become_none() -> None:
    """Whitespace is stripped and empty strings become missing values."""

    df = pd.DataFrame({"title": ["  a  ", "   "], "text": ["x", ""]})
    clean_dataframe(df=df)
    assert df.loc[0, "title"] == "a"
    assert df["title"].isnull().tolist() == [False, True]
    assert df["text"].isnull().tolist() == [False, True]


@pytest.mark.parametrize(
    "existing, expected_types",
    [
        ([], []),
        ([("Title", "other")], ["title_in_db"]),
        ([("other", "Text")], ["text_in_db"]),
        ([(" Title ", " Text ")], ["title_in_db", "text_in_db"]),
    ],
    ids=["none", "title", "text", "both_stripped"],
)
async def test_check_db_duplicates(
    existing: list[tuple[str, str]],
    expected_types: list[str],
    patch_service: Callable[..., AsyncMock],
) -> None:
    """Titles/texts already in the workspace are flagged (ignoring whitespace).

    Parameters
    ----------
    existing
        `(title, text)` pairs already stored in the workspace.
    expected_types
        The expected error types, in order.
    patch_service
        Helper to patch service-level names.
    """

    patch_service(
        "get_list_of_content_from_db",
        return_value=[
            _content_record(content_title=title, content_text=text)
            for title, text in existing
        ],
    )
    errors: list[CustomError] = []
    await check_db_duplicates(
        asession=AsyncMock(),
        df=pd.DataFrame({"title": ["Title"], "text": ["Text"]}),
        error_list=errors,
        workspace_id=WORKSPACE_ID,
    )
    assert [e.type for e in errors] == expected_types


def test_extract_unique_tags() -> None:
    """Comma-separated tags are split, stripped, upper-cased and de-duplicated."""

    tags = _extract_unique_tags(tags_col=pd.Series(["a, b", None, "B,c "]))
    assert sorted(tags) == ["A", "B", "C"]


def test_get_tags_not_in_db() -> None:
    """Only incoming tags missing from the DB are returned."""

    tags_in_db = [_tag_record(tag_id=1, tag_name="A")]
    result = _get_tags_not_in_db(incoming_tags=["A", "B"], tags_in_db=tags_in_db)
    assert result == ["B"]
