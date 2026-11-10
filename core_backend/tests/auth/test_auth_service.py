"""Unit tests for `app.auth.service`.

No database, Redis or network. Several service functions open their own
`AsyncSession`; the `fake_session` fixture swaps `AsyncSession` (and the engine
factory) on the service module for a context manager yielding a mock session.
Repository functions, Google ID-token verification and Redis are replaced with
mocks on the `app.auth.service` module.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.schemas import AuthenticatedUser
from app.core.config import JWT_ALGORITHM, JWT_SECRET, REDIS_KEY_EXPIRED
from app.core.exceptions import (
    BadRequestError,
    TooManyRequestsError,
    UnauthorizedError,
)
from app.core.security import (
    create_access_token,
    get_key_hash,
    get_password_salted_hash,
)
from app.users.models import UserDB
from app.users.repository import UserNotFoundError
from app.users.schemas import UserRoles
from app.workspaces.models import WorkspaceDB

PASSWORD = "auth_service_password"  # pragma: allowlist secret
GMAIL = "someone@gmail.com"

PatchService = Callable[..., dict[str, AsyncMock]]


def make_user_db(username: str = "user") -> UserDB:
    """Build a transient `UserDB` whose password is `PASSWORD`.

    Parameters
    ----------
    username
        The username.

    Returns
    -------
    UserDB
        The user object.
    """

    return UserDB(
        hashed_password=get_password_salted_hash(key=PASSWORD),
        user_id=1,
        username=username,
    )


def make_workspace_db(
    name: str = "ws", api_daily_quota: int | None = 10
) -> WorkspaceDB:
    """Build a transient `WorkspaceDB`.

    Parameters
    ----------
    name
        The workspace name.
    api_daily_quota
        The workspace's daily API quota.

    Returns
    -------
    WorkspaceDB
        The workspace object.
    """

    return WorkspaceDB(
        api_daily_quota=api_daily_quota, workspace_id=1, workspace_name=name
    )


def result_with(value: Any) -> MagicMock:
    """Build a fake `session.execute()` result.

    Parameters
    ----------
    value
        Returned by `scalar_one()`; if it is an exception it is raised instead.

    Returns
    -------
    MagicMock
        The fake result.
    """

    result = MagicMock()
    if isinstance(value, Exception):
        result.scalar_one.side_effect = value
    else:
        result.scalar_one.return_value = value
    return result


@pytest.fixture
def patch_service(monkeypatch: pytest.MonkeyPatch) -> PatchService:
    """Replace functions on `app.auth.service` with `AsyncMock`s.

    Keyword values that are already mocks are used as-is (e.g. to set a
    `side_effect`); any other value becomes the mock's `return_value`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    PatchService
        Callable `(**name_to_value) -> dict[name, AsyncMock]`.
    """

    def _patch(**values: Any) -> dict[str, AsyncMock]:
        mocks: dict[str, AsyncMock] = {}
        for name, value in values.items():
            mock = (
                value if isinstance(value, AsyncMock) else AsyncMock(return_value=value)
            )
            monkeypatch.setattr(service, name, mock)
            mocks[name] = mock
        return mocks

    return _patch


@pytest.fixture
def fake_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Make `AsyncSession(...)` inside the service yield a mock session.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    MagicMock
        The mock session the service will use (`execute` is an `AsyncMock`).
    """

    session = MagicMock(spec=AsyncSession)

    class _SessionContext:
        """Stand-in for `AsyncSession` used as an async context manager."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Accept and ignore the engine / options."""

        async def __aenter__(self) -> MagicMock:
            """Return the mock session."""
            return session

        async def __aexit__(self, *exc_info: Any) -> None:
            """Do nothing on exit."""

    monkeypatch.setattr(service, "AsyncSession", _SessionContext)
    monkeypatch.setattr(service, "get_sqlalchemy_async_engine", lambda: None)
    return session


@pytest.fixture
def fake_google(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace Google ID-token verification on the service module.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    MagicMock
        The fake `verify_oauth2_token`; set its `return_value` / `side_effect`.
    """

    verify = MagicMock()
    monkeypatch.setattr(
        service, "id_token", SimpleNamespace(verify_oauth2_token=verify)
    )
    monkeypatch.setattr(service, "requests", SimpleNamespace(Request=lambda: None))
    return verify


class TestDecodeAccessToken:
    """Tests for `decode_access_token` and `build_authentication_details`."""

    def test_round_trip(self) -> None:
        """Test that a token issued by the service decodes to its claims."""

        details = service.build_authentication_details(
            access_level="fullaccess",
            user_role=UserRoles.ADMIN,
            username="user",
            workspace_name="ws",
        )
        assert details.token_type == "bearer"
        assert service.decode_access_token(token=details.access_token) == ("user", "ws")

    @pytest.mark.parametrize(
        "token",
        [
            "not-a-jwt",
            jwt.encode({"username": "user"}, JWT_SECRET, algorithm=JWT_ALGORITHM),
            jwt.encode(
                {
                    "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
                    "username": "user",
                    "workspace_name": "ws",
                },
                JWT_SECRET,
                algorithm=JWT_ALGORITHM,
            ),
        ],
        ids=["malformed", "missing-workspace", "expired"],
    )
    def test_invalid_tokens(self, token: str) -> None:
        """Test that bad tokens raise a 401 with the bearer challenge header.

        Parameters
        ----------
        token
            The token to decode.
        """

        with pytest.raises(UnauthorizedError) as exc_info:
            service.decode_access_token(token=token)
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


class TestCredentialsLogin:
    """Tests for `authenticate_credentials` and `login_with_credentials`."""

    @pytest.mark.parametrize(
        "user_lookup, password, expected_user",
        [
            (AsyncMock(side_effect=UserNotFoundError()), PASSWORD, False),
            (AsyncMock(return_value=make_user_db()), "wrong", False),
            (AsyncMock(return_value=make_user_db()), PASSWORD, True),
        ],
        ids=["unknown-user", "wrong-password", "valid"],
    )
    async def test_authenticate_credentials(
        self,
        expected_user: bool,
        fake_session: MagicMock,
        password: str,
        patch_service: PatchService,
        user_lookup: AsyncMock,
    ) -> None:
        """Test that only valid credentials authenticate, in the default workspace.

        Parameters
        ----------
        expected_user
            Whether an authenticated user is expected.
        fake_session
            Mock session used by the service.
        password
            The password supplied.
        patch_service
            Fixture that patches service dependencies.
        user_lookup
            Mock for `get_user_by_username`.
        """

        patch_service(
            get_user_by_username=user_lookup,
            get_user_default_workspace=make_workspace_db("default_ws"),
            get_user_role_in_workspace=UserRoles.READ_ONLY,
        )
        result = await service.authenticate_credentials(
            password=password, username="user"
        )
        if expected_user:
            assert result == AuthenticatedUser(
                access_level="fullaccess",
                user_role=UserRoles.READ_ONLY,
                username="user",
                workspace_name="default_ws",
            )
        else:
            assert result is None

    @pytest.mark.parametrize("authenticated", [False, True])
    async def test_login_with_credentials(
        self, authenticated: bool, patch_service: PatchService
    ) -> None:
        """Test that failed authentication is a 401 and success issues a token.

        Parameters
        ----------
        authenticated
            Whether `authenticate_credentials` succeeds.
        patch_service
            Fixture that patches service dependencies.
        """

        user = AuthenticatedUser(
            access_level="fullaccess",
            user_role=UserRoles.ADMIN,
            username="user",
            workspace_name="ws",
        )
        patch_service(authenticate_credentials=user if authenticated else None)
        call = service.login_with_credentials(password=PASSWORD, username="user")
        if authenticated:
            details = await call
            assert details.username == "user"
            assert service.decode_access_token(token=details.access_token) == (
                "user",
                "ws",
            )
        else:
            with pytest.raises(UnauthorizedError):
                await call


class TestGoogleLogin:
    """Tests for the Google sign-in functions."""

    @pytest.mark.parametrize(
        "verify_kwargs, valid",
        [
            ({"return_value": {"email": GMAIL, "iss": "accounts.google.com"}}, True),
            ({"return_value": {"email": GMAIL, "iss": "evil.example.com"}}, False),
            ({"side_effect": ValueError("bad signature")}, False),
        ],
        ids=["valid", "wrong-issuer", "bad-token"],
    )
    def test_verify_google_token(
        self, fake_google: MagicMock, valid: bool, verify_kwargs: dict[str, Any]
    ) -> None:
        """Test that only tokens from Google's issuers are accepted.

        Parameters
        ----------
        fake_google
            Fake Google token verifier.
        valid
            Whether the token should be accepted.
        verify_kwargs
            Behaviour of the fake verifier.
        """

        fake_google.configure_mock(**verify_kwargs)
        if valid:
            assert service.verify_google_token(credential="tok")["email"] == GMAIL
        else:
            with pytest.raises(UnauthorizedError):
                service.verify_google_token(credential="tok")

    async def test_login_with_google(
        self, monkeypatch: pytest.MonkeyPatch, patch_service: PatchService
    ) -> None:
        """Test that the verified email is used to authenticate and a token issued.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.
        patch_service
            Fixture that patches service dependencies.
        """

        mocks = patch_service(
            authenticate_or_create_google_user=AuthenticatedUser(
                access_level="fullaccess",
                user_role=UserRoles.ADMIN,
                username=GMAIL,
                workspace_name="ws",
            )
        )
        # `verify_google_token` is sync, so it is replaced with a plain function.
        monkeypatch.setattr(
            service, "verify_google_token", lambda **_: {"email": GMAIL}
        )

        details = await service.login_with_google(credential="tok", redis=AsyncMock())

        assert details.username == GMAIL
        assert mocks["authenticate_or_create_google_user"].await_args is not None
        create_kwargs = mocks["authenticate_or_create_google_user"].await_args.kwargs
        assert create_kwargs["gmail"] == GMAIL

    async def test_existing_google_user(
        self, fake_session: MagicMock, patch_service: PatchService
    ) -> None:
        """Test that an existing Google user signs into their default workspace.

        Parameters
        ----------
        fake_session
            Mock session used by the service.
        patch_service
            Fixture that patches service dependencies.
        """

        mocks = patch_service(
            create_workspace=None,
            get_user_by_username=make_user_db(GMAIL),
            get_user_default_workspace=make_workspace_db("their_ws"),
            get_user_role_in_workspace=UserRoles.READ_ONLY,
        )
        user = await service.authenticate_or_create_google_user(
            gmail=GMAIL, redis=AsyncMock()
        )
        assert user.workspace_name == "their_ws"
        assert user.user_role == UserRoles.READ_ONLY
        mocks["create_workspace"].assert_not_awaited()

    @pytest.mark.parametrize("workspace_is_new", [True, False])
    async def test_new_google_user(
        self,
        fake_session: MagicMock,
        patch_service: PatchService,
        workspace_is_new: bool,
    ) -> None:
        """Test that a new Google user gets their own workspace as ADMIN, unless a
        workspace with that name already exists.

        Parameters
        ----------
        fake_session
            Mock session used by the service.
        patch_service
            Fixture that patches service dependencies.
        workspace_is_new
            Whether `create_workspace` reports a newly created workspace.
        """

        workspace_name = f"{GMAIL}'s Workspace"
        mocks = patch_service(
            create_user_workspace_role=None,
            create_workspace=(make_workspace_db(workspace_name), workspace_is_new),
            get_user_by_username=AsyncMock(side_effect=UserNotFoundError()),
            save_user_to_db=make_user_db(GMAIL),
            update_api_limits=None,
        )

        call = service.authenticate_or_create_google_user(
            gmail=GMAIL, redis=AsyncMock()
        )
        if not workspace_is_new:
            with pytest.raises(BadRequestError):
                await call
            mocks["save_user_to_db"].assert_not_awaited()
            return

        user = await call
        assert user.user_role == UserRoles.ADMIN
        assert user.workspace_name == workspace_name
        mocks["update_api_limits"].assert_awaited_once()
        assert mocks["create_user_workspace_role"].await_args is not None
        role_kwargs = mocks["create_user_workspace_role"].await_args.kwargs
        assert role_kwargs["is_default_workspace"] is True
        assert role_kwargs["user_role"] == UserRoles.ADMIN


class TestWorkspaceLookup:
    """Tests for the API-key / JWT workspace lookups."""

    @pytest.mark.parametrize("found", [True, False])
    async def test_get_workspace_by_api_key(self, found: bool) -> None:
        """Test looking a workspace up by the hash of its API key.

        Parameters
        ----------
        found
            Whether a workspace matches the key.
        """

        workspace_db = make_workspace_db()
        asession = MagicMock(spec=AsyncSession)
        asession.execute.return_value = result_with(
            workspace_db if found else NoResultFound()
        )

        call = service.get_workspace_by_api_key(asession=asession, token="api-key")
        if found:
            assert await call is workspace_db
        else:
            with pytest.raises(service.WorkspaceTokenNotFoundError):
                await call

        # The query filters on the SHA-256 of the key, never the key itself.
        (stmt,) = asession.execute.await_args.args
        assert stmt.compile().params == {
            "hashed_api_key_1": get_key_hash(key="api-key")
        }

    async def test_api_key_match(
        self, fake_session: MagicMock, patch_service: PatchService
    ) -> None:
        """Test that a valid API key resolves to its workspace without a JWT.

        Parameters
        ----------
        fake_session
            Mock session used by the service.
        patch_service
            Fixture that patches service dependencies.
        """

        workspace_db = make_workspace_db()
        patch_service(get_workspace_by_api_key=workspace_db)
        result = await service.get_workspace_by_api_key_or_jwt(token="api-key")
        assert result is workspace_db
        fake_session.execute.assert_not_awaited()

    @pytest.mark.parametrize(
        "token, workspace_found, valid",
        [
            (
                create_access_token(
                    user_role=UserRoles.ADMIN, username="u", workspace_name="ws"
                ),
                True,
                True,
            ),
            (
                create_access_token(
                    user_role=UserRoles.ADMIN, username="u", workspace_name="gone"
                ),
                False,
                False,
            ),
            ("neither-key-nor-jwt", True, False),
        ],
        ids=["jwt-valid", "jwt-unknown-workspace", "garbage"],
    )
    async def test_jwt_fallback(
        self,
        fake_session: MagicMock,
        patch_service: PatchService,
        token: str,
        valid: bool,
        workspace_found: bool,
    ) -> None:
        """Test the JWT fallback used when the bearer token is not an API key.

        Parameters
        ----------
        fake_session
            Mock session used by the service.
        patch_service
            Fixture that patches service dependencies.
        token
            The bearer token.
        valid
            Whether the token should resolve to a workspace.
        workspace_found
            Whether the workspace named in the JWT exists.
        """

        workspace_db = make_workspace_db()
        patch_service(
            get_workspace_by_api_key=AsyncMock(
                side_effect=service.WorkspaceTokenNotFoundError()
            )
        )
        fake_session.execute.return_value = result_with(
            workspace_db if workspace_found else NoResultFound()
        )

        call = service.get_workspace_by_api_key_or_jwt(token=token)
        if valid:
            assert await call is workspace_db
        else:
            with pytest.raises(UnauthorizedError):
                await call

    @pytest.mark.parametrize("found", [True, False])
    async def test_get_user_by_access_token(
        self, fake_session: MagicMock, found: bool, patch_service: PatchService
    ) -> None:
        """Test resolving the user named in a JWT.

        Parameters
        ----------
        fake_session
            Mock session used by the service.
        found
            Whether the user exists.
        patch_service
            Fixture that patches service dependencies.
        """

        user_db = make_user_db("u")
        patch_service(
            get_user_by_username=AsyncMock(
                return_value=user_db, side_effect=None if found else UserNotFoundError()
            )
        )
        token = create_access_token(
            user_role=UserRoles.ADMIN, username="u", workspace_name="ws"
        )
        call = service.get_user_by_access_token(token=token)
        if found:
            assert await call is user_db
        else:
            with pytest.raises(UnauthorizedError):
                await call


class TestConsumeApiQuota:
    """Tests for `consume_api_quota`."""

    @pytest.fixture
    def redis(self) -> AsyncMock:
        """Return a fake Redis client with a live key holding 5 remaining calls.

        Returns
        -------
        AsyncMock
            The fake client.
        """

        redis = AsyncMock()
        redis.ttl.return_value = 100
        redis.get.return_value = b"5"
        return redis

    async def test_limit_check_disabled(
        self, monkeypatch: pytest.MonkeyPatch, redis: AsyncMock
    ) -> None:
        """Test that nothing is read or written when limits are disabled.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.
        redis
            Fake Redis client.
        """

        monkeypatch.setattr(service, "CHECK_API_LIMIT", False)
        await service.consume_api_quota(redis=redis, workspace_db=make_workspace_db())
        redis.ttl.assert_not_awaited()

    @pytest.mark.parametrize(
        "ttl, stored, expected_updates",
        [
            (100, b"5", [4]),  # Decrement.
            (REDIS_KEY_EXPIRED, b"5", [10, 4]),  # Re-initialise from quota first.
            (100, b"None", []),  # Unlimited workspace.
        ],
        ids=["decrement", "expired-key", "unlimited"],
    )
    async def test_quota_consumed(
        self,
        expected_updates: list[int],
        patch_service: PatchService,
        redis: AsyncMock,
        stored: bytes,
        ttl: int,
    ) -> None:
        """Test how the remaining-calls counter is updated.

        Parameters
        ----------
        expected_updates
            `api_daily_quota` values passed to each `update_api_limits` call.
        patch_service
            Fixture that patches service dependencies.
        redis
            Fake Redis client.
        stored
            The counter value stored in Redis.
        ttl
            The key's TTL reported by Redis.
        """

        redis.ttl.return_value = ttl
        redis.get.return_value = stored
        mocks = patch_service(update_api_limits=None)

        await service.consume_api_quota(redis=redis, workspace_db=make_workspace_db())

        updates = [
            c.kwargs["api_daily_quota"]
            for c in mocks["update_api_limits"].await_args_list
        ]
        assert updates == expected_updates
        redis.get.assert_awaited_once_with("remaining-calls:ws")

    async def test_quota_exhausted(
        self, patch_service: PatchService, redis: AsyncMock
    ) -> None:
        """Test that an exhausted quota raises 429.

        Parameters
        ----------
        patch_service
            Fixture that patches service dependencies.
        redis
            Fake Redis client.
        """

        redis.get.return_value = b"0"
        patch_service(update_api_limits=None)
        with pytest.raises(TooManyRequestsError):
            await service.consume_api_quota(
                redis=redis, workspace_db=make_workspace_db()
            )
