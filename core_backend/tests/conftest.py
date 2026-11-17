"""This module contains fixtures for the API tests."""

# pylint: disable=W0613, W0621
import builtins
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Generator, Optional
from urllib.parse import urlparse

import numpy as np
import pytest
import redis as sync_redis
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from pytest_alembic.config import Config
from redis import asyncio as aioredis
from sqlalchemy import delete, select, text
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.contents.models import ContentDB
from app.core import security as core_security
from app.core.config import (
    LITELLM_API_KEY,
    LITELLM_ENDPOINT,
    LITELLM_MODEL_EMBEDDING,
    PGVECTOR_VECTOR_SIZE,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
    REDIS_HOST,
)
from app.core.database import (
    SYNC_DB_API,
    get_connection_url,
    get_session_context_manager,
)
from app.core.security import (
    create_access_token,
    get_key_hash,
    hash_password,
)
from app.main import app

# process_input / process_output were merged into the question_answer service module.
from app.question_answer import service as process_input
from app.question_answer import service as process_output
from app.question_answer.models import (
    ContentFeedbackDB,
    QueryResponseContentDB,
)
from app.question_answer.schemas import IdentifiedLanguage, QueryRefined, QueryResponse
from app.question_answer.service import RAG, AlignmentScore
from app.urgency_detection.models import UrgencyQueryDB, UrgencyResponseDB
from app.urgency_detection.schemas import UrgencyDetectionEntailmentResult
from app.urgency_rules.models import UrgencyRuleDB
from app.users.models import UserDB, UserWorkspaceDB
from app.users.schemas import UserRoles
from app.workspaces.models import WorkspaceDB
from app.workspaces.repository import get_workspace_by_workspace_name

# Production Argon2 parameters (64 MiB, 3 passes) make every hash/verify cost tens of
# milliseconds, which more than doubles the suite's run time. Tests swap in the
# cheapest valid Argon2 parameters. Hashes keep the same `$argon2id$` format and the
# same verify/upgrade code paths; only the work factor changes. This is a test-only
# monkeypatch: there is deliberately no setting that lowers the cost in production.
core_security.password_hash = core_security.PasswordHash(
    (
        core_security.Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),
        core_security.LegacySha256Hasher(),
    )
)
core_security._DUMMY_PASSWORD_HASH = core_security.password_hash.hash("dummy")

# Fixture data files live next to this conftest, so paths do not depend on the
# directory pytest is launched from.
DATA_DIR = Path(__file__).parent / "data"

# Admin users.
TEST_ADMIN_PASSWORD_1 = "admin_password_1"  # pragma: allowlist secret
TEST_ADMIN_PASSWORD_2 = "admin_password_2"  # pragma: allowlist secret
TEST_ADMIN_PASSWORD_3 = "admin_password_3"  # pragma: allowlist secret
TEST_ADMIN_PASSWORD_4 = "admin_password_4"  # pragma: allowlist secret
TEST_ADMIN_PASSWORD_DATA_API_1 = "admin_password_data_api_1"  # pragma: allowlist secret
TEST_ADMIN_PASSWORD_DATA_API_2 = "admin_password_data_api_2"  # pragma: allowlist secret
TEST_ADMIN_USERNAME_1 = "admin_1"
TEST_ADMIN_USERNAME_2 = "admin_2"
TEST_ADMIN_USERNAME_3 = "admin_3"
TEST_ADMIN_USERNAME_4 = "admin_4"
TEST_ADMIN_USERNAME_DATA_API_1 = "admin_data_api_1"
TEST_ADMIN_USERNAME_DATA_API_2 = "admin_data_api_2"

# Read-only users.
TEST_READ_ONLY_PASSWORD_1 = "test_password_1"  # pragma: allowlist secret
TEST_READ_ONLY_USERNAME_1 = "test_username_1"
TEST_READ_ONLY_USERNAME_2 = "test_username_2"

# Workspaces.
TEST_WORKSPACE_API_KEY_1 = "test_api_key_1"  # pragma: allowlist secret
TEST_WORKSPACE_API_QUOTA_2 = 2000
TEST_WORKSPACE_API_QUOTA_3 = 2000
TEST_WORKSPACE_API_QUOTA_4 = 2000
TEST_WORKSPACE_API_QUOTA_DATA_API_1 = 2000
TEST_WORKSPACE_API_QUOTA_DATA_API_2 = 2000
TEST_WORKSPACE_CONTENT_QUOTA_2 = 50
TEST_WORKSPACE_CONTENT_QUOTA_3 = 50
TEST_WORKSPACE_CONTENT_QUOTA_4 = 50
TEST_WORKSPACE_CONTENT_QUOTA_DATA_API_1 = 50
TEST_WORKSPACE_CONTENT_QUOTA_DATA_API_2 = 50

TEST_WORKSPACE_NAME_1 = "test_workspace_1"
TEST_WORKSPACE_NAME_2 = "test_workspace_2"
TEST_WORKSPACE_NAME_3 = "test_workspace_3"
TEST_WORKSPACE_NAME_4 = "test_workspace_4"
TEST_WORKSPACE_NAME_DATA_API_1 = "test_workspace_data_api_1"
TEST_WORKSPACE_NAME_DATA_API_2 = "test_workspace_data_api_2"


# Fresh test database per run.
#
# Every pytest run gets a brand-new Postgres database and an empty Redis DB:
#
#   1. If Postgres/Redis are not reachable on localhost, start the `testdb` /
#      `redis-test` docker containers (same images and ports as the Makefile).
#   2. Keep a migrated template database, "<POSTGRES_DB>-template". It is rebuilt
#      with `alembic upgrade head` only when its revision differs from the
#      migration head, so normally no migrations run at all.
#   3. DROP + CREATE "<POSTGRES_DB>" from that template. Postgres copies the
#      template's files, which takes a fraction of a second.
#   4. FLUSHDB on the Redis DB in REDIS_HOST.
#
# The alembic migration tests get a separate, empty "<POSTGRES_DB>-alembic"
# database (see `alembic_engine`), so they can run in the same session.
BACKEND_DIR = Path(__file__).resolve().parent.parent
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
SERVICE_START_TIMEOUT_SECONDS = 30


def _refuse_non_test_database(db_name: str) -> None:
    """Stop the run unless `db_name` is clearly a throwaway test database.

    Each run DROPs the database, so this guards against a misconfigured environment
    pointing pytest at a development or production database.

    Parameters
    ----------
    db_name
        The database the run is about to drop and recreate.
    """

    if "test" not in db_name.lower():
        pytest.exit(
            f"Refusing to drop database {db_name!r}: the test database name must "
            "contain 'test'. Set POSTGRES_DB in tests/test.env (or your shell).",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )


def _sync_engine(db_name: str, **kwargs: Any) -> Engine:
    """Return a short-lived sync engine for `db_name` on the test Postgres server.

    Parameters
    ----------
    db_name
        Database to connect to.
    **kwargs
        Extra arguments for `create_engine` (e.g. `isolation_level`).

    Returns
    -------
    Engine
        Engine that does not pool connections, so nothing is left open afterwards.
    """

    return create_engine(
        get_connection_url(db=db_name, db_api=SYNC_DB_API),
        connect_args={"connect_timeout": 3},
        poolclass=NullPool,
        **kwargs,
    )


def _postgres_is_up() -> bool:
    """Return True if the Postgres server accepts connections."""

    try:
        with _sync_engine("postgres").connect():
            return True
    except OperationalError:
        return False


def _redis_is_up() -> bool:
    """Return True if the Redis server answers PING."""

    try:
        return bool(sync_redis.from_url(REDIS_HOST, socket_connect_timeout=3).ping())
    except sync_redis.exceptions.ConnectionError:
        return False


def _start_container(name: str, run_args: list[str]) -> None:
    """Start docker container `name`, creating it with `run_args` if it is missing.

    Parameters
    ----------
    name
        Container name.
    run_args
        Arguments for `docker run -d --name <name> ...` when the container does not
        exist yet.
    """

    if shutil.which("docker") is None:
        pytest.exit(
            f"Cannot reach the test {name} service and docker is not installed. "
            "Start Postgres/Redis yourself (see tests/test.env for host/ports).",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )
    started = subprocess.run(["docker", "start", name], capture_output=True)
    if started.returncode != 0:
        subprocess.run(
            ["docker", "run", "-d", "--name", name, *run_args],
            capture_output=True,
            check=True,
        )


def _wait_until(is_up: Callable[[], bool], what: str) -> None:
    """Poll `is_up` until it returns True or the start-up timeout passes.

    Parameters
    ----------
    is_up
        Health check to poll.
    what
        Service name for the error message.
    """

    deadline = time.monotonic() + SERVICE_START_TIMEOUT_SECONDS
    while not is_up():
        if time.monotonic() > deadline:
            pytest.exit(f"{what} did not become ready in time.", returncode=1)
        time.sleep(0.5)


def _ensure_local_services() -> None:
    """Start the Postgres/Redis test containers if they are local and not running.

    Remote hosts (e.g. the CI service containers) are never touched.
    """

    if POSTGRES_HOST in LOCAL_HOSTS and not _postgres_is_up():
        _start_container(
            "testdb",
            [
                "-p",
                f"{POSTGRES_PORT}:5432",
                "-e",
                f"POSTGRES_USER={POSTGRES_USER}",
                "-e",
                f"POSTGRES_PASSWORD={POSTGRES_PASSWORD}",
                "-e",
                f"POSTGRES_DB={POSTGRES_DB}",
                "pgvector/pgvector:pg16",
            ],
        )
        _wait_until(_postgres_is_up, "Postgres")

    redis_url = urlparse(REDIS_HOST)
    if redis_url.hostname in LOCAL_HOSTS and not _redis_is_up():
        _start_container(
            "redis-test", ["-p", f"{redis_url.port or 6379}:6379", "redis:6.0-alpine"]
        )
        _wait_until(_redis_is_up, "Redis")


def _template_revision(db_name: str) -> str | None:
    """Return the alembic revision of database `db_name`, or None if it has none.

    Parameters
    ----------
    db_name
        Database to inspect.

    Returns
    -------
    str | None
        The stored `alembic_version`, or None if the DB or table does not exist.
    """

    try:
        with _sync_engine(db_name).connect() as conn:
            return conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
    except (OperationalError, ProgrammingError):
        return None


def _recreate_database(db_name: str, *, template: str | None = None) -> None:
    """DROP database `db_name` (if present) and CREATE it, optionally from a template.

    Parameters
    ----------
    db_name
        Database to recreate.
    template
        Template database to copy; None creates an empty database.
    """

    _refuse_non_test_database(db_name)
    # CREATE/DROP DATABASE cannot run inside a transaction block.
    admin = _sync_engine("postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))
        template_sql = f' TEMPLATE "{template}"' if template else ""
        conn.execute(text(f'CREATE DATABASE "{db_name}"{template_sql}'))
    admin.dispose()


def _build_fresh_test_database() -> None:
    """Recreate POSTGRES_DB from an up-to-date migrated template (see above)."""

    template = f"{POSTGRES_DB}-template"
    alembic_cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    head = ScriptDirectory.from_config(alembic_cfg).get_current_head()

    if _template_revision(template) != head:
        # Template missing or behind the migrations: rebuild it once. Alembic runs
        # in a subprocess because `migrations/env.py` reads POSTGRES_DB at import.
        _recreate_database(template)
        migrated = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env={**os.environ, "POSTGRES_DB": template},
            capture_output=True,
            text=True,
        )
        if migrated.returncode != 0:
            pytest.exit(f"alembic upgrade failed:\n{migrated.stderr}", returncode=1)

    _recreate_database(POSTGRES_DB, template=template)


# Hooks.
def pytest_sessionstart(session: pytest.Session) -> None:
    """Give every test run a brand-new database and an empty Redis DB.

    Parameters
    ----------
    session
        The pytest session object (unused).
    """

    _ensure_local_services()
    _build_fresh_test_database()
    # A sync client is enough here; the app opens its own async client later.
    sync_redis.from_url(REDIS_HOST).flushdb()


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Run the BDD scenarios last.

    The BDD suite deletes every user and workspace, which would break the
    session-scoped users/workspaces the other tests share. `trylast` makes this run
    after pytest-randomly's shuffle; the sort is stable, so the shuffled order is
    kept within each group.

    Parameters
    ----------
    config
        The pytest config object (unused).
    items
        Collected test items, reordered in place.
    """

    bdd_dir = Path(__file__).parent / "bdd"
    items.sort(key=lambda item: item.path.is_relative_to(bdd_dir))


# Fixtures.
@pytest.fixture(scope="function")
async def asession(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async session for testing.

    Parameters
    ----------
    async_engine
        Async engine for testing.

    Yields
    ------
    AsyncGenerator[AsyncSession, None]
        Async session for testing.
    """

    async with AsyncSession(async_engine, expire_on_commit=False) as async_session:
        yield async_session


@pytest.fixture(scope="function")
async def rollback_asession(
    async_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Async session whose writes are rolled back when the test ends.

    Use this for repository tests. The session runs inside one outer transaction;
    `join_transaction_mode="create_savepoint"` turns every `commit()` made by the
    code under test into a SAVEPOINT release, so nothing reaches the database and no
    clean-up code is needed. Rows written here are invisible to the `client`
    fixture (different connection), so do not mix the two in one test.

    Also do not combine it with fixtures that commit and later DELETE rows (e.g.
    `faq_contents_in_workspace_*`): their teardown DELETE waits on the locks this
    open transaction holds, and the test hangs. Create the rows inside this
    session instead.

    Parameters
    ----------
    async_engine
        Async engine for testing.

    Yields
    ------
    AsyncGenerator[AsyncSession, None]
        Async session bound to a transaction that is rolled back on teardown.
    """

    async with async_engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session
        await transaction.rollback()


@pytest.fixture(scope="function")
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an async engine for testing.

    NB: We recreate engine and session to ensure it is in the same event loop as the
    test. Without this we get "Future attached to different loop" error. See:
    https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html#using-multiple-asyncio-event-loops

    Yields
    ------
    Generator[AsyncEngine, None, None]
        Async engine for testing.
    """  # noqa: E501

    connection_string = get_connection_url()
    engine = create_async_engine(connection_string, pool_size=20)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def client(patch_llm_call: pytest.FixtureRequest) -> Generator[TestClient, None, None]:
    """Create a test client.

    Parameters
    ----------
    patch_llm_call
        Pytest fixture request object.

    Yields
    ------
    Generator[TestClient, None, None]
        Test client.
    """

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def db_session() -> Generator[Session, None, None]:
    """Create a test database session.

    Yields
    ------
    Generator[Session, None, None]
        Test database session.
    """

    with get_session_context_manager() as session:
        yield session


@pytest.fixture(scope="session")
def access_token_admin_1() -> str:
    """Return an access token for admin user 1 in workspace 1.

    Returns
    -------
    str
        Access token for admin user 1 in workspace 1.
    """

    return create_access_token(
        user_role=UserRoles.ADMIN,
        username=TEST_ADMIN_USERNAME_1,
        workspace_name=TEST_WORKSPACE_NAME_1,
    )


@pytest.fixture(scope="session")
def access_token_admin_2() -> str:
    """Return an access token for admin user 2 in workspace 2.

    Returns
    -------
    str
        Access token for admin user 2 in workspace 2.
    """

    return create_access_token(
        user_role=UserRoles.ADMIN,
        username=TEST_ADMIN_USERNAME_2,
        workspace_name=TEST_WORKSPACE_NAME_2,
    )


@pytest.fixture(scope="session")
def access_token_admin_4() -> str:
    """Return an access token for admin user 4 in workspace 4.

    Returns
    -------
    str
        Access token for admin user 4 in workspace 4.
    """

    return create_access_token(
        user_role=UserRoles.ADMIN,
        username=TEST_ADMIN_USERNAME_4,
        workspace_name=TEST_WORKSPACE_NAME_4,
    )


@pytest.fixture(scope="session")
def access_token_admin_data_api_1() -> str:
    """Return an access token for data API admin user 1 in data API workspace 1.

    Returns
    -------
    str
        Access token for data API admin user 1 in data API workspace 1.
    """

    return create_access_token(
        user_role=UserRoles.ADMIN,
        username=TEST_ADMIN_USERNAME_DATA_API_1,
        workspace_name=TEST_WORKSPACE_NAME_DATA_API_1,
    )


@pytest.fixture(scope="session")
def access_token_admin_data_api_2() -> str:
    """Return an access token for data API admin user 2 in data API workspace 2.

    Returns
    -------
    str
        Access token for data API admin user 2 in data API workspace 2.
    """

    return create_access_token(
        user_role=UserRoles.ADMIN,
        username=TEST_ADMIN_USERNAME_DATA_API_2,
        workspace_name=TEST_WORKSPACE_NAME_DATA_API_2,
    )


@pytest.fixture(scope="session")
def access_token_read_only_1() -> str:
    """Return an access token for read-only user 1 in workspace 1.

    NB: Read-only user 1 is created in the same workspace as the admin user 1.

    Returns
    -------
    str
        Access token for read-only user 1 in workspace 1.
    """

    return create_access_token(
        user_role=UserRoles.READ_ONLY,
        username=TEST_READ_ONLY_USERNAME_1,
        workspace_name=TEST_WORKSPACE_NAME_1,
    )


@pytest.fixture(scope="session")
def access_token_read_only_2() -> str:
    """Return an access token for read-only user 2 in workspace 2.

    NB: Read-only user 2 is created in the same workspace as the admin user 2.

    Returns
    -------
    str
        Access token for read-only user 2 in workspace 2.
    """

    return create_access_token(
        user_role=UserRoles.READ_ONLY,
        username=TEST_READ_ONLY_USERNAME_2,
        workspace_name=TEST_WORKSPACE_NAME_2,
    )


@pytest.fixture(scope="session", autouse=True)
async def admin_user_1_in_workspace_1(
    access_token_admin_1: pytest.FixtureRequest, client: TestClient
) -> dict[str, Any]:
    """Create admin user 1 in workspace 1 by invoking the `/user/register-first-user`
    endpoint.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1 in workspace 1.
    client
        Test client.

    Returns
    -------
    dict[str, Any]
        The response from creating admin user 1 in workspace 1.
    """

    response = client.post(
        "/user/register-first-user",
        json={
            "is_default_workspace": True,
            "password": TEST_ADMIN_PASSWORD_1,
            "role": UserRoles.ADMIN,
            "username": TEST_ADMIN_USERNAME_1,
            "workspace_name": TEST_WORKSPACE_NAME_1,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    return response.json()


@pytest.fixture(scope="session", autouse=True)
async def admin_user_2_in_workspace_2(
    access_token_admin_1: pytest.FixtureRequest, client: TestClient
) -> dict[str, Any]:
    """Create admin user 2 in workspace 2 by invoking the `/user` endpoint.

    NB: Only admins can create workspaces. Since admin user 1 is the first admin user
    ever, we need admin user 1 to create workspace 2 and then add admin user 2 to
    workspace 2.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1 in workspace 1.
    client
        Test client.

    Returns
    -------
    dict[str, Any]
        The response from creating admin user 2 in workspace 2.
    """

    client.post(
        "/workspace",
        json={
            "api_daily_quota": TEST_WORKSPACE_API_QUOTA_2,
            "content_quota": TEST_WORKSPACE_CONTENT_QUOTA_2,
            "workspace_name": TEST_WORKSPACE_NAME_2,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    response = client.post(
        "/user",
        json={
            "is_default_workspace": True,
            "password": TEST_ADMIN_PASSWORD_2,
            "role": UserRoles.ADMIN,
            "username": TEST_ADMIN_USERNAME_2,
            "workspace_name": TEST_WORKSPACE_NAME_2,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    return response.json()


@pytest.fixture(scope="session", autouse=True)
async def admin_user_3_in_workspace_3(
    access_token_admin_1: pytest.FixtureRequest, client: TestClient
) -> dict[str, Any]:
    """Create admin user 3 in workspace 3 by invoking the `/user` endpoint.

    NB: Only admins can create workspaces. Since admin user 1 is the first admin user
    ever, we need admin user 1 to create workspace 3 and then add admin user 3 to
    workspace 3.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1 in workspace 1.
    client
        Test client.

    Returns
    -------
    dict[str, Any]
        The response from creating admin user 3 in workspace 3.
    """

    client.post(
        "/workspace",
        json={
            "api_daily_quota": TEST_WORKSPACE_API_QUOTA_3,
            "content_quota": TEST_WORKSPACE_CONTENT_QUOTA_3,
            "workspace_name": TEST_WORKSPACE_NAME_3,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    response = client.post(
        "/user",
        json={
            "is_default_workspace": True,
            "password": TEST_ADMIN_PASSWORD_3,
            "role": UserRoles.ADMIN,
            "username": TEST_ADMIN_USERNAME_3,
            "workspace_name": TEST_WORKSPACE_NAME_3,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    return response.json()


@pytest.fixture(scope="session", autouse=True)
async def admin_user_4_in_workspace_4(
    access_token_admin_1: pytest.FixtureRequest, client: TestClient
) -> dict[str, Any]:
    """Create admin user 4 in workspace 4 by invoking the `/user` endpoint.

    NB: Only admins can create workspaces. Since admin user 1 is the first admin user
    ever, we need admin user 1 to create workspace 4 and then add admin user 4 to
    workspace 4.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1 in workspace 1.
    client
        Test client.

    Returns
    -------
    dict[str, Any]
        The response from creating admin user 4 in workspace 4.
    """

    client.post(
        "/workspace",
        json={
            "api_daily_quota": TEST_WORKSPACE_API_QUOTA_4,
            "content_quota": TEST_WORKSPACE_CONTENT_QUOTA_4,
            "workspace_name": TEST_WORKSPACE_NAME_4,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    response = client.post(
        "/user",
        json={
            "is_default_workspace": True,
            "password": TEST_ADMIN_PASSWORD_4,
            "role": UserRoles.ADMIN,
            "username": TEST_ADMIN_USERNAME_4,
            "workspace_name": TEST_WORKSPACE_NAME_4,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    return response.json()


@pytest.fixture(scope="session", autouse=True)
async def admin_user_data_api_1_in_workspace_data_api_1(
    access_token_admin_1: pytest.FixtureRequest, client: TestClient
) -> dict[str, Any]:
    """Create data API admin user 1 in data API workspace 1 by invoking the `/user`
    endpoint.

    NB: Only admins can create workspaces. Since admin user 1 is the first admin user
    ever, we need admin user 1 to create the data API workspace 1 and then add the data
    API admin user 1 to the data API workspace 1.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1 in workspace 1.
    client
        Test client.

    Returns
    -------
    dict[str, Any]
        The response from creating the data API admin user 1 in the data API workspace
        1.
    """

    client.post(
        "/workspace",
        json={
            "api_daily_quota": TEST_WORKSPACE_API_QUOTA_DATA_API_1,
            "content_quota": TEST_WORKSPACE_CONTENT_QUOTA_DATA_API_1,
            "workspace_name": TEST_WORKSPACE_NAME_DATA_API_1,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    response = client.post(
        "/user",
        json={
            "is_default_workspace": True,
            "password": TEST_ADMIN_PASSWORD_DATA_API_1,
            "role": UserRoles.ADMIN,
            "username": TEST_ADMIN_USERNAME_DATA_API_1,
            "workspace_name": TEST_WORKSPACE_NAME_DATA_API_1,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    return response.json()


@pytest.fixture(scope="session", autouse=True)
async def admin_user_data_api_2_in_workspace_data_api_2(
    access_token_admin_1: pytest.FixtureRequest, client: TestClient
) -> dict[str, Any]:
    """Create data API admin user 2 in data API workspace 2 by invoking the `/user`
    endpoint.

    NB: Only admins can create workspaces. Since admin user 1 is the first admin user
    ever, we need admin user 1 to create the data API workspace 2 and then add the data
    API admin user 2 to the data API workspace 2.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1 in workspace 1.
    client
        Test client.

    Returns
    -------
    dict[str, Any]
        The response from creating the data API admin user 2 in the data API workspace
        2.
    """

    client.post(
        "/workspace",
        json={
            "api_daily_quota": TEST_WORKSPACE_API_QUOTA_DATA_API_2,
            "content_quota": TEST_WORKSPACE_CONTENT_QUOTA_DATA_API_2,
            "workspace_name": TEST_WORKSPACE_NAME_DATA_API_2,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    response = client.post(
        "/user",
        json={
            "is_default_workspace": True,
            "password": TEST_ADMIN_PASSWORD_DATA_API_2,
            "role": UserRoles.ADMIN,
            "username": TEST_ADMIN_USERNAME_DATA_API_2,
            "workspace_name": TEST_WORKSPACE_NAME_DATA_API_2,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    return response.json()


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    """`alembic_config` is the primary point of entry for configurable options for the
    alembic runner for `pytest-alembic`.

    Returns
    -------
    Config
        A configuration object used by `pytest-alembic`.
    """

    # Absolute paths, so the tests do not depend on the launch directory.
    return Config(
        {
            "file": str(BACKEND_DIR / "alembic.ini"),
            "script_location": str(BACKEND_DIR / "migrations"),
        }
    )


@pytest.fixture(scope="session")
def alembic_database() -> str:
    """Create an empty database for the alembic migration tests, once per run.

    `pytest-alembic` needs an empty database, while the rest of the suite needs a
    migrated one. Giving the migration tests their own "<POSTGRES_DB>-alembic"
    database lets both run in the same `pytest` invocation.

    Returns
    -------
    str
        Name of the freshly created, empty database.
    """

    db_name = f"{POSTGRES_DB}-alembic"
    _recreate_database(db_name)
    return db_name


@pytest.fixture(scope="function")
def alembic_engine(alembic_database: str) -> Engine:
    """`alembic_engine` is where you specify the engine with which the alembic_runner
    should execute your tests.

    NB: The engine should point to a database that must be empty. It is out of scope
    for `pytest-alembic` to manage the database state.

    Parameters
    ----------
    alembic_database
        Name of the empty database created for the migration tests.

    Returns
    -------
    Engine
        A SQLAlchemy engine object.
    """

    return create_engine(get_connection_url(db=alembic_database, db_api=SYNC_DB_API))


@pytest.fixture(scope="session")
def api_key_workspace_1(access_token_admin_1: str, client: TestClient) -> str:
    """Return an API key for admin user 1 in workspace 1 by invoking the
    `/workspace/rotate-key` endpoint.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1.
    client
        Test client.

    Returns
    -------
    str
        The new API key for workspace 1.
    """

    response = client.put(
        "/workspace/rotate-key",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    return response.json()["new_api_key"]


@pytest.fixture(scope="session")
def api_key_workspace_2(access_token_admin_2: str, client: TestClient) -> str:
    """Return an API key for admin user 2 in workspace 2 by invoking the
    `/workspace/rotate-key` endpoint.

    Parameters
    ----------
    access_token_admin_2
        Access token for admin user 2.
    client
        Test client.

    Returns
    -------
    str
        The new API key for workspace 2.
    """

    response = client.put(
        "/workspace/rotate-key",
        headers={"Authorization": f"Bearer {access_token_admin_2}"},
    )
    return response.json()["new_api_key"]


@pytest.fixture(scope="session")
def api_key_workspace_data_api_1(
    access_token_admin_data_api_1: str, client: TestClient
) -> str:
    """Return an API key for the data API admin user 1 in the data API workspace 1 by
    invoking the `/workspace/rotate-key` endpoint.

    Parameters
    ----------
    access_token_admin_data_api_1
        Access token for the data API admin user 1 in data API workspace 1.
    client
        Test client.

    Returns
    -------
    str
        The new API key for data API workspace 1.
    """

    response = client.put(
        "/workspace/rotate-key",
        headers={"Authorization": f"Bearer {access_token_admin_data_api_1}"},
    )
    return response.json()["new_api_key"]


@pytest.fixture(scope="session")
def api_key_workspace_data_api_2(
    access_token_admin_data_api_2: str, client: TestClient
) -> str:
    """Return an API key for the data API admin user 2 in the data API workspace 2 by
    invoking the `/workspace/rotate-key` endpoint.

    Parameters
    ----------
    access_token_admin_data_api_2
        Access token for the data API admin user 2 in data API workspace 2.
    client
        Test client.

    Returns
    -------
    str
        The new API key for the data API workspace 2.
    """

    response = client.put(
        "/workspace/rotate-key",
        headers={"Authorization": f"Bearer {access_token_admin_data_api_2}"},
    )
    return response.json()["new_api_key"]


@pytest.fixture(scope="module", params=["Tag1", "Tag2"])
def existing_tag_id_in_workspace_1(
    access_token_admin_1: str, client: TestClient, request: pytest.FixtureRequest
) -> Generator[str, None, None]:
    """Create a tag for workspace 1.

    NB: Using `request.param[0]` only uses the "T" in "Tag1" or "Tag2". This is
    essentially a hack fix in order to not get a tag already exists error when we
    create the tag (unless, of course, another test creates a tag named "T").

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1.
    client
        Test client.
    request
        Pytest request object.

    Yields
    ------
    Generator[str, None, None]
        Tag ID.
    """

    response = client.post(
        "/tag",
        json={"tag_name": request.param[0]},
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    tag_id = response.json()["tag_id"]

    yield tag_id

    client.delete(
        f"/tag/{tag_id}", headers={"Authorization": f"Bearer {access_token_admin_1}"}
    )


@pytest.fixture(scope="function")
async def faq_contents_in_workspace_1(
    asession: AsyncSession, admin_user_1_in_workspace_1: dict[str, Any]
) -> AsyncGenerator[list[int], None]:
    """Create FAQ contents in workspace 1.

    Parameters
    ----------
    asession
        Async database session.
    admin_user_1_in_workspace_1
        Admin user 1 in workspace 1.

    Yields
    ------
    AsyncGenerator[list[int], None]
        FAQ content IDs.
    """

    workspace_name = admin_user_1_in_workspace_1["workspace_name"]
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    workspace_id = workspace_db.workspace_id

    with open(DATA_DIR / "content.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    contents = []
    for content in json_data:
        text_to_embed = content["content_title"] + "\n" + content["content_text"]
        content_embedding = await async_fake_embedding(
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
            input=text_to_embed,
            model=LITELLM_MODEL_EMBEDDING,
        )
        content_db = ContentDB(
            content_embedding=content_embedding,
            content_metadata=content.get("content_metadata", {}),
            content_text=content["content_text"],
            content_title=content["content_title"],
            created_datetime_utc=datetime.now(timezone.utc),
            updated_datetime_utc=datetime.now(timezone.utc),
            workspace_id=workspace_id,
        )
        contents.append(content_db)

    asession.add_all(contents)
    await asession.commit()

    yield [content.content_id for content in contents]

    for content in contents:
        delete_feedback = delete(ContentFeedbackDB).where(
            ContentFeedbackDB.content_id == content.content_id
        )
        content_query = delete(QueryResponseContentDB).where(
            QueryResponseContentDB.content_id == content.content_id
        )
        await asession.execute(delete_feedback)
        await asession.execute(content_query)
        await asession.delete(content)

    await asession.commit()


@pytest.fixture(scope="function")
async def faq_contents_in_workspace_3(
    asession: AsyncSession, admin_user_3_in_workspace_3: dict[str, Any]
) -> AsyncGenerator[list[int], None]:
    """Create FAQ contents in workspace 3.

    Parameters
    ----------
    asession
        Async database session.
    admin_user_3_in_workspace_3
        Admin user 3 in workspace 3.

    Yields
    ------
    AsyncGenerator[list[int], None]
        FAQ content IDs.
    """

    workspace_name = admin_user_3_in_workspace_3["workspace_name"]
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    workspace_id = workspace_db.workspace_id

    with open(DATA_DIR / "content.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    contents = []
    for content in json_data:
        text_to_embed = content["content_title"] + "\n" + content["content_text"]
        content_embedding = await async_fake_embedding(
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
            input=text_to_embed,
            model=LITELLM_MODEL_EMBEDDING,
        )
        content_db = ContentDB(
            content_embedding=content_embedding,
            content_metadata=content.get("content_metadata", {}),
            content_text=content["content_text"],
            content_title=content["content_title"],
            created_datetime_utc=datetime.now(timezone.utc),
            updated_datetime_utc=datetime.now(timezone.utc),
            workspace_id=workspace_id,
        )
        contents.append(content_db)

    asession.add_all(contents)
    await asession.commit()

    yield [content.content_id for content in contents]

    for content in contents:
        delete_feedback = delete(ContentFeedbackDB).where(
            ContentFeedbackDB.content_id == content.content_id
        )
        content_query = delete(QueryResponseContentDB).where(
            QueryResponseContentDB.content_id == content.content_id
        )
        await asession.execute(delete_feedback)
        await asession.execute(content_query)
        await asession.delete(content)

    await asession.commit()


@pytest.fixture(scope="function")
async def faq_contents_in_workspace_data_api_1(
    asession: AsyncSession,
    admin_user_data_api_1_in_workspace_data_api_1: dict[str, Any],
) -> AsyncGenerator[list[int], None]:
    """Create FAQ contents in the data API workspace 1.

    Parameters
    ----------
    asession
        Async database session.
    admin_user_data_api_1_in_workspace_data_api_1
        Data API admin user 1 in the data API workspace 1.

    Yields
    ------
    AsyncGenerator[list[int], None]
        FAQ content IDs.
    """

    workspace_name = admin_user_data_api_1_in_workspace_data_api_1["workspace_name"]
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    workspace_id = workspace_db.workspace_id

    with open(DATA_DIR / "content.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    contents = []
    for content in json_data:
        text_to_embed = content["content_title"] + "\n" + content["content_text"]
        content_embedding = await async_fake_embedding(
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
            input=text_to_embed,
            model=LITELLM_MODEL_EMBEDDING,
        )
        content_db = ContentDB(
            content_embedding=content_embedding,
            content_metadata=content.get("content_metadata", {}),
            content_text=content["content_text"],
            content_title=content["content_title"],
            created_datetime_utc=datetime.now(timezone.utc),
            updated_datetime_utc=datetime.now(timezone.utc),
            workspace_id=workspace_id,
        )
        contents.append(content_db)

    asession.add_all(contents)
    await asession.commit()

    yield [content.content_id for content in contents]

    for content in contents:
        delete_feedback = delete(ContentFeedbackDB).where(
            ContentFeedbackDB.content_id == content.content_id
        )
        content_query = delete(QueryResponseContentDB).where(
            QueryResponseContentDB.content_id == content.content_id
        )
        await asession.execute(delete_feedback)
        await asession.execute(content_query)
        await asession.delete(content)

    await asession.commit()


@pytest.fixture(scope="function")
async def faq_contents_in_workspace_data_api_2(
    asession: AsyncSession,
    admin_user_data_api_2_in_workspace_data_api_2: dict[str, Any],
) -> AsyncGenerator[list[int], None]:
    """Create FAQ contents in the data API workspace 2.

    Parameters
    ----------
    asession
        Async database session.
    admin_user_data_api_2_in_workspace_data_api_2
        Data API admin user 2 in the data API workspace 2.

    Yields
    ------
    AsyncGenerator[list[int], None]
        FAQ content IDs.
    """

    workspace_name = admin_user_data_api_2_in_workspace_data_api_2["workspace_name"]
    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    workspace_id = workspace_db.workspace_id

    with open(DATA_DIR / "content.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    contents = []
    for content in json_data:
        text_to_embed = content["content_title"] + "\n" + content["content_text"]
        content_embedding = await async_fake_embedding(
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
            input=text_to_embed,
            model=LITELLM_MODEL_EMBEDDING,
        )
        content_db = ContentDB(
            content_embedding=content_embedding,
            content_metadata=content.get("content_metadata", {}),
            content_text=content["content_text"],
            content_title=content["content_title"],
            created_datetime_utc=datetime.now(timezone.utc),
            updated_datetime_utc=datetime.now(timezone.utc),
            workspace_id=workspace_id,
        )
        contents.append(content_db)

    asession.add_all(contents)
    await asession.commit()

    yield [content.content_id for content in contents]

    for content in contents:
        delete_feedback = delete(ContentFeedbackDB).where(
            ContentFeedbackDB.content_id == content.content_id
        )
        content_query = delete(QueryResponseContentDB).where(
            QueryResponseContentDB.content_id == content.content_id
        )
        await asession.execute(delete_feedback)
        await asession.execute(content_query)
        await asession.delete(content)

    await asession.commit()


@pytest.fixture(scope="session")
def monkeysession(
    request: pytest.FixtureRequest,
) -> Generator[pytest.MonkeyPatch, None, None]:
    """Create a monkeypatch for the session.

    Parameters
    ----------
    request
        Pytest fixture request object.

    Yields
    ------
    Generator[pytest.MonkeyPatch, None, None]
        Monkeypatch for the session.
    """

    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session", autouse=True)
def patch_llm_call(monkeysession: pytest.MonkeyPatch) -> None:
    """Monkeypatch call to LLM embeddings service.

    Parameters
    ----------
    monkeysession
        Pytest monkeypatch object.
    """

    monkeysession.setattr("app.contents.repository.embedding", async_fake_embedding)
    monkeysession.setattr(
        "app.urgency_rules.repository.embedding", async_fake_embedding
    )
    monkeysession.setattr(process_input, "_classify_safety", mock_return_args)
    monkeysession.setattr(process_input, "_identify_language", mock_identify_language)
    monkeysession.setattr(process_input, "_paraphrase_question", mock_return_args)
    monkeysession.setattr(process_input, "_translate_question", mock_translate_question)
    monkeysession.setattr(process_output, "_get_llm_align_score", mock_get_align_score)
    monkeysession.setattr(
        "app.urgency_detection.service.detect_urgency", mock_detect_urgency
    )
    monkeysession.setattr(
        "app.question_answer.service.get_llm_rag_answer",
        patched_llm_rag_answer,
    )
    # Loading the real model costs ~3s per run, and reranking random fake embeddings
    # proves nothing. `rerank_search_results` itself is unit-tested with fakes.
    monkeysession.setattr("app.main.load_crossencoder", FakeCrossEncoder)


@pytest.fixture(scope="session", autouse=True)
def patch_voice_gcs_functions(monkeysession: pytest.MonkeyPatch) -> None:
    """Monkeypatch GCS functions to replace their real implementations with dummy ones.

    Parameters
    ----------
    monkeysession
        Pytest monkeypatch object.
    """

    monkeysession.setattr(
        "app.question_answer.service.upload_file_to_gcs",
        async_fake_upload_file_to_gcs,
    )
    monkeysession.setattr(
        "app.question_answer.service.upload_file_to_gcs",
        async_fake_upload_file_to_gcs,
    )
    monkeysession.setattr(
        "app.question_answer.service.generate_public_url",
        async_fake_generate_public_url,
    )


@pytest.fixture(scope="session", autouse=True)
async def read_only_user_1_in_workspace_1(
    access_token_admin_1: pytest.FixtureRequest, client: TestClient
) -> dict[str, Any]:
    """Create read-only user 1 in workspace 1.

    NB: Only admin user 1 can create read-only user 1 in workspace 1.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1.
    client
        Test client.

    Returns
    -------
    dict[str, Any]
        The response from creating read-only user 1 in workspace 1.
    """

    response = client.post(
        "/user",
        json={
            "is_default_workspace": True,
            "password": TEST_READ_ONLY_PASSWORD_1,
            "role": UserRoles.READ_ONLY,
            "username": TEST_READ_ONLY_USERNAME_1,
            "workspace_name": TEST_WORKSPACE_NAME_1,
        },
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )
    return response.json()


@pytest.fixture(scope="function")
async def redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    """Create a redis client for testing.

    Yields
    ------
    Generator[aioredis.Redis, None, None]
        Redis client for testing.
    """

    rclient = await aioredis.from_url(REDIS_HOST, decode_responses=True)

    await rclient.flushdb()

    yield rclient

    await rclient.close()


@pytest.fixture(scope="class")
def temp_workspace_api_key_and_api_quota(
    client: TestClient, db_session: Session, request: pytest.FixtureRequest
) -> Generator[tuple[str, int], None, None]:
    """Create a temporary workspace API key and API quota.

    Parameters
    ----------
    client
        Test client.
    db_session
        Test database session.
    request
        Pytest request object.

    Yields
    ------
    Generator[tuple[str, int], None, None]
        Temporary workspace API key and API quota.
    """

    db_session.rollback()
    api_daily_quota = request.param["api_daily_quota"]
    username = request.param["username"]
    workspace_name = request.param["workspace_name"]
    temp_access_token = create_access_token(
        user_role=UserRoles.ADMIN, username=username, workspace_name=workspace_name
    )

    temp_user_db = UserDB(
        created_datetime_utc=datetime.now(timezone.utc),
        hashed_password=hash_password(password="temp_password"),
        updated_datetime_utc=datetime.now(timezone.utc),
        username=username,
    )
    db_session.add(temp_user_db)
    db_session.flush()

    temp_workspace_db = WorkspaceDB(
        api_daily_quota=api_daily_quota,
        created_datetime_utc=datetime.now(timezone.utc),
        doc_language="ENGLISH",
        hashed_api_key=get_key_hash(key="temp_api_key"),
        updated_datetime_utc=datetime.now(timezone.utc),
        workspace_name=workspace_name,
    )
    db_session.add(temp_workspace_db)
    db_session.flush()

    temp_user_workspace_db = UserWorkspaceDB(
        created_datetime_utc=datetime.now(timezone.utc),
        default_workspace=True,
        updated_datetime_utc=datetime.now(timezone.utc),
        user_id=temp_user_db.user_id,
        user_role=UserRoles.ADMIN,
        workspace_id=temp_workspace_db.workspace_id,
    )
    db_session.add(temp_user_workspace_db)
    db_session.commit()

    response_key = client.put(
        "/workspace/rotate-key",
        headers={"Authorization": f"Bearer {temp_access_token}"},
    )
    api_key = response_key.json()["new_api_key"]

    yield api_key, api_daily_quota

    db_session.delete(temp_user_db)
    db_session.delete(temp_workspace_db)
    db_session.delete(temp_user_workspace_db)
    db_session.commit()
    db_session.rollback()


@pytest.fixture(scope="class")
def temp_workspace_token_and_quota(
    db_session: Session, request: pytest.FixtureRequest
) -> Generator[tuple[str, int], None, None]:
    """Create a temporary workspace with a specific content quota and return the access
    token and content quota.

    Parameters
    ----------
    db_session
        The database session.
    request
        The pytest request object.

    Yields
    ------
    Generator[tuple[str, int], None, None]
        The access token and content quota for the temporary workspace.
    """

    content_quota = request.param["content_quota"]
    username = request.param["username"]
    workspace_name = request.param["workspace_name"]

    temp_user_db = UserDB(
        created_datetime_utc=datetime.now(timezone.utc),
        hashed_password=hash_password(password="temp_password"),
        updated_datetime_utc=datetime.now(timezone.utc),
        username=username,
    )
    db_session.add(temp_user_db)
    db_session.flush()

    temp_workspace_db = WorkspaceDB(
        content_quota=content_quota,
        created_datetime_utc=datetime.now(timezone.utc),
        doc_language="ENGLISH",
        hashed_api_key=get_key_hash(key="temp_api_key"),
        updated_datetime_utc=datetime.now(timezone.utc),
        workspace_name=workspace_name,
    )
    db_session.add(temp_workspace_db)
    db_session.flush()

    temp_user_workspace_db = UserWorkspaceDB(
        created_datetime_utc=datetime.now(timezone.utc),
        default_workspace=True,
        updated_datetime_utc=datetime.now(timezone.utc),
        user_id=temp_user_db.user_id,
        user_role=UserRoles.ADMIN,
        workspace_id=temp_workspace_db.workspace_id,
    )
    db_session.add(temp_user_workspace_db)
    db_session.commit()

    yield (
        create_access_token(
            user_role=UserRoles.ADMIN, username=username, workspace_name=workspace_name
        ),
        content_quota,
    )

    db_session.delete(temp_user_db)
    db_session.delete(temp_workspace_db)
    db_session.delete(temp_user_workspace_db)
    db_session.commit()


@pytest.fixture(scope="function")
async def urgency_rules_workspace_1(
    db_session: Session, workspace_1_id: int
) -> AsyncGenerator[int, None]:
    """Create urgency rules for workspace 1.

    NB: It is important to also delete the urgency queries and urgency query responses
    entries since the tests that use this fixture will create entries in those tables.

    Parameters
    ----------
    db_session
        Test database session.
    workspace_1_id
        The ID for workspace 1.

    Yields
    ------
    AsyncGenerator[int, None]
        Number of urgency rules in workspace 1.
    """

    with open(DATA_DIR / "urgency_rules.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    rules = []
    for i, rule in enumerate(json_data):
        rule_embedding = await async_fake_embedding(
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
            input=rule["urgency_rule_text"],
            model=LITELLM_MODEL_EMBEDDING,
        )
        rule_db = UrgencyRuleDB(
            created_datetime_utc=datetime.now(timezone.utc),
            updated_datetime_utc=datetime.now(timezone.utc),
            urgency_rule_id=i,
            urgency_rule_metadata=rule.get("urgency_rule_metadata", {}),
            urgency_rule_text=rule["urgency_rule_text"],
            urgency_rule_vector=rule_embedding,
            workspace_id=workspace_1_id,
        )
        rules.append(rule_db)
    db_session.add_all(rules)
    db_session.commit()

    yield len(rules)

    # Delete the urgency rules.
    for rule in rules:
        db_session.delete(rule)

    # Delete urgency queries.
    stmt = delete(UrgencyQueryDB).where(UrgencyQueryDB.workspace_id == workspace_1_id)
    db_session.execute(stmt)

    # Delete urgency query responses.
    stmt = delete(UrgencyResponseDB).where(
        UrgencyResponseDB.workspace_id == workspace_1_id
    )
    db_session.execute(stmt)

    db_session.commit()


@pytest.fixture(scope="function")
async def urgency_rules_workspace_data_api_1(
    db_session: Session, workspace_data_api_id_1: int
) -> AsyncGenerator[int, None]:
    """Create urgency rules for the data API workspace 1.

    Parameters
    ----------
    db_session
        Test database session.
    workspace_data_api_id_1
        The ID for the data API workspace 1.

    Yields
    ------
    AsyncGenerator[int, None]
        Number of urgency rules in the data API workspace 1.
    """

    with open(DATA_DIR / "urgency_rules.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    rules = []
    for i, rule in enumerate(json_data):
        rule_embedding = await async_fake_embedding(
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
            input=rule["urgency_rule_text"],
            model=LITELLM_MODEL_EMBEDDING,
        )
        rule_db = UrgencyRuleDB(
            created_datetime_utc=datetime.now(timezone.utc),
            updated_datetime_utc=datetime.now(timezone.utc),
            urgency_rule_id=i,
            urgency_rule_metadata=rule.get("urgency_rule_metadata", {}),
            urgency_rule_text=rule["urgency_rule_text"],
            urgency_rule_vector=rule_embedding,
            workspace_id=workspace_data_api_id_1,
        )
        rules.append(rule_db)
    db_session.add_all(rules)
    db_session.commit()

    yield len(rules)

    # Delete the urgency rules.
    for rule in rules:
        db_session.delete(rule)
    db_session.commit()


@pytest.fixture(scope="function")
async def urgency_rules_workspace_data_api_2(
    db_session: Session, workspace_data_api_id_2: int
) -> AsyncGenerator[int, None]:
    """Create urgency rules for the data API workspace 2.

    Parameters
    ----------
    db_session
        Test database session.
    workspace_data_api_id_2
        The ID for the data API workspace 2.

    Yields
    ------
    AsyncGenerator[int, None]
        Number of urgency rules in the data API workspace 2.
    """

    with open(DATA_DIR / "urgency_rules.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    rules = []
    for i, rule in enumerate(json_data):
        rule_embedding = await async_fake_embedding(
            api_base=LITELLM_ENDPOINT,
            api_key=LITELLM_API_KEY,
            input=rule["urgency_rule_text"],
            model=LITELLM_MODEL_EMBEDDING,
        )
        rule_db = UrgencyRuleDB(
            created_datetime_utc=datetime.now(timezone.utc),
            updated_datetime_utc=datetime.now(timezone.utc),
            urgency_rule_id=i,
            urgency_rule_metadata=rule.get("urgency_rule_metadata", {}),
            urgency_rule_text=rule["urgency_rule_text"],
            urgency_rule_vector=rule_embedding,
            workspace_id=workspace_data_api_id_2,
        )
        rules.append(rule_db)
    db_session.add_all(rules)
    db_session.commit()

    yield len(rules)

    # Delete the urgency rules.
    for rule in rules:
        db_session.delete(rule)
    db_session.commit()


@pytest.fixture(scope="session")
def workspace_1_id(db_session: Session) -> Generator[int, None, None]:
    """Return workspace 1 ID.

    Parameters
    ----------
    db_session
        Test database session.

    Yields
    ------
    Generator[int, None, None]
        Workspace 1 ID.
    """

    stmt = select(WorkspaceDB).where(
        WorkspaceDB.workspace_name == TEST_WORKSPACE_NAME_1
    )
    result = db_session.execute(stmt)
    workspace_db = result.scalar_one()
    yield workspace_db.workspace_id


@pytest.fixture(scope="session")
def workspace_2_id(db_session: Session) -> Generator[int, None, None]:
    """Return workspace 2 ID.

    Parameters
    ----------
    db_session
        Test database session.

    Yields
    ------
    Generator[int, None, None]
        Workspace 2 ID.
    """

    stmt = select(WorkspaceDB).where(
        WorkspaceDB.workspace_name == TEST_WORKSPACE_NAME_2
    )
    result = db_session.execute(stmt)
    workspace_db = result.scalar_one()
    yield workspace_db.workspace_id


@pytest.fixture(scope="session")
def workspace_3_id(db_session: Session) -> Generator[int, None, None]:
    """Return workspace 3 ID.

    Parameters
    ----------
    db_session
        Test database session.

    Yields
    ------
    Generator[int, None, None]
        Workspace 3 ID.
    """

    stmt = select(WorkspaceDB).where(
        WorkspaceDB.workspace_name == TEST_WORKSPACE_NAME_3
    )
    result = db_session.execute(stmt)
    workspace_db = result.scalar_one()
    yield workspace_db.workspace_id


@pytest.fixture(scope="session")
def workspace_data_api_id_1(db_session: Session) -> Generator[int, None, None]:
    """Return data API workspace 1 ID.

    Parameters
    ----------
    db_session
        Test database session.

    Yields
    ------
    Generator[int, None, None]
        Data API workspace 1 ID.
    """

    stmt = select(WorkspaceDB).where(
        WorkspaceDB.workspace_name == TEST_WORKSPACE_NAME_DATA_API_1
    )
    result = db_session.execute(stmt)
    workspace_db = result.scalar_one()
    yield workspace_db.workspace_id


@pytest.fixture(scope="session")
def workspace_data_api_id_2(db_session: Session) -> Generator[int, None, None]:
    """Return data API workspace 2 ID.

    Parameters
    ----------
    db_session
        Test database session.

    Yields
    ------
    Generator[int, None, None]
        Data API workspace 2 ID.
    """

    stmt = select(WorkspaceDB).where(
        WorkspaceDB.workspace_name == TEST_WORKSPACE_NAME_DATA_API_2
    )
    result = db_session.execute(stmt)
    workspace_db = result.scalar_one()
    yield workspace_db.workspace_id


# Mocks.
class MockDatetime:
    """Mock the datetime object."""

    def __init__(self, *, date: datetime) -> None:
        """Initialize the mock datetime object.

        Parameters
        ----------
        date
            The date.
        """

        self.date = date

    def now(self, tz: Optional[tzinfo] = None) -> datetime:
        """Mock the datetime.now() method.

        Parameters
        ----------
        tz
            The timezone.

        Returns
        -------
        datetime
            The datetime object.
        """

        return self.date.astimezone(tz) if tz is not None else self.date


async def async_fake_embedding(*arg: str, **kwargs: str) -> list[float]:
    """Replicate `embedding` function by generating a random list of floats.

    Parameters
    ----------
    arg:
        Additional positional arguments. Not used.
    kwargs
        Additional keyword arguments. Not used.

    Returns
    -------
    list[float]
        List of random floats.
    """

    embedding_list = (
        np.random.rand(int(PGVECTOR_VECTOR_SIZE)).astype(np.float32).tolist()
    )
    return embedding_list


async def async_fake_generate_public_url(*args: Any, **kwargs: Any) -> str:
    """A dummy function to replace the real `generate_public_url` function.

    Parameters
    ----------
    args
        Additional positional arguments.
    kwargs
        Additional keyword arguments.

    Returns
    -------
    str
        A dummy URL.
    """

    return "http://example.com/signed-url"


async def async_fake_upload_file_to_gcs(*args: Any, **kwargs: Any) -> None:
    """A dummy function to replace the real `upload_file_to_gcs` function.

    Parameters
    ----------
    args
        Additional positional arguments.
    kwargs
        Additional keyword arguments.
    """


class FakeCrossEncoder:
    """Stand-in for `sentence_transformers.CrossEncoder` in tests.

    Scores every (query, content) pair by content length, so reranking is
    deterministic and instant.
    """

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        """Return one score per (query, content) pair.

        Parameters
        ----------
        pairs
            (query text, content text) pairs to score.

        Returns
        -------
        list[float]
            One score per pair.
        """

        return [float(len(content)) for _, content in pairs]


async def mock_detect_urgency(
    urgency_rules: list[str], message: str, metadata: Optional[dict]
) -> UrgencyDetectionEntailmentResult:
    """Mock for the `detect_urgency` function.

    Returns the same type as the real function, because `llm_entailment_classifier`
    reads `result.probability` (a dict would raise AttributeError).

    Parameters
    ----------
    urgency_rules
        A list of urgency rules.
    message
        The message to check against the urgency rules.
    metadata
        Additional metadata.

    Returns
    -------
    UrgencyDetectionEntailmentResult
        The urgency detection result.
    """

    return UrgencyDetectionEntailmentResult(
        best_matching_rule="made up rule",
        probability=0.7,
        reason="this is a mocked response",
    )


async def mock_get_align_score(*args: Any, **kwargs: Any) -> AlignmentScore:
    """Mock return argument for the `_get_llm_align_score function`.

    Parameters
    ----------
    args
        Additional positional arguments.
    kwargs
        Additional keyword arguments.

    Returns
    -------
    AlignmentScore
        Alignment score object.
    """

    return AlignmentScore(reason="test - high score", score=0.9)


async def mock_identify_language(
    *,
    metadata: Optional[dict] = None,
    query_refined: QueryRefined,
    response: QueryResponse,
) -> tuple[QueryRefined, QueryResponse]:
    """Mock function arguments for the `_identify_language` function.

    Parameters
    ----------
    query_refined
        The refined query.
    response
        The query response.
    metadata
        Additional metadata.

    Returns
    -------
    tuple[QueryRefined, QueryResponse]
        Refined query and query response.
    """

    query_refined.original_language = IdentifiedLanguage.ENGLISH
    response.debug_info["original_language"] = "ENGLISH"

    return query_refined, response


async def mock_return_args(
    *,
    metadata: Optional[dict] = None,
    query_refined: QueryRefined,
    response: QueryResponse,
) -> tuple[QueryRefined, QueryResponse]:
    """Mock function arguments for functions in the `process_input` module.

    Parameters
    ----------
    metadata
        Additional metadata.
    query_refined
        The refined query.
    response
        The query response.

    Returns
    -------
    tuple[QueryRefined, QueryResponse]
        Refined query and query response.
    """

    return query_refined, response


async def mock_translate_question(
    *,
    metadata: Optional[dict] = None,
    query_refined: QueryRefined,
    response: QueryResponse,
) -> tuple[QueryRefined, QueryResponse]:
    """Mock function arguments for the `_translate_question` function.

    Parameters
    ----------
    query_refined
        The refined query.
    response
        The query response.
    metadata
        Additional metadata.

    Returns
    -------
    tuple[QueryRefined, QueryResponse]
        Refined query and query response.

    Raises
    ------
    ValueError
        If the language hasn't been identified.
    """

    if query_refined.original_language is None:
        raise ValueError(
            (
                "Language hasn't been identified. "
                "Identify language before running translation"
            )
        )
    response.debug_info["translated_question"] = query_refined.query_text

    return query_refined, response


async def patched_llm_rag_answer(*args: Any, **kwargs: Any) -> RAG:
    """Mock return argument for the `get_llm_rag_answer` function.

    Parameters
    ----------
    args
        Additional positional arguments.
    kwargs
        Additional keyword arguments.

    Returns
    -------
    RAG
        Patched LLM RAG response object.
    """

    return RAG(answer="patched llm response", extracted_info=[])


class FakeRedis:
    """In-memory stand-in for the async Redis client, for unit tests that must not
    touch the network.

    Implements only the commands the refresh-token code uses. Expiry is accepted and
    ignored; tests that need expiry use the real Redis via `redis_client`.
    """

    def __init__(self) -> None:
        """Start with an empty keyspace."""

        self.data: dict[str, Any] = {}

    async def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        """Store a string value."""

        self.data[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        """Delete keys and return how many existed."""

        return sum(self.data.pop(key, None) is not None for key in keys)

    async def exists(self, *keys: str) -> int:
        """Return how many of the keys exist."""

        return sum(key in self.data for key in keys)

    async def sadd(self, key: str, *members: str) -> int:
        """Add members to a set."""

        members_set = self.data.setdefault(key, set())
        before = len(members_set)
        members_set.update(m.encode() for m in members)
        return len(members_set) - before

    async def srem(self, key: str, *members: str) -> int:
        """Remove members from a set."""

        members_set = self.data.get(key, set())
        before = len(members_set)
        members_set.difference_update(m.encode() for m in members)
        return before - len(members_set)

    # `builtins.set`: inside this class body, `set` is the method above.
    async def smembers(self, key: str) -> "builtins.set[bytes]":
        """Return a set's members as bytes, like redis-py without decoding."""

        return set(self.data.get(key, set()))

    async def expire(self, key: str, seconds: int) -> bool:
        """Accept and ignore an expiry."""

        return key in self.data

    def pipeline(self, transaction: bool = True) -> "_FakePipeline":
        """Return a pipeline that runs the queued commands on `execute()`."""

        return _FakePipeline(self)


class _FakePipeline:
    """Queues `FakeRedis` commands and runs them in order on `execute()`."""

    def __init__(self, redis: FakeRedis) -> None:
        """Bind to the fake client."""

        self._redis = redis
        self._calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Callable[..., "_FakePipeline"]:
        """Queue any command the fake client implements."""

        getattr(self._redis, name)  # Fail fast on unsupported commands.

        def _queue(*args: Any, **kwargs: Any) -> "_FakePipeline":
            self._calls.append((name, args, kwargs))
            return self

        return _queue

    async def execute(self) -> list[Any]:
        """Run the queued commands."""

        return [
            await getattr(self._redis, name)(*args, **kwargs)
            for name, args, kwargs in self._calls
        ]

    async def __aenter__(self) -> "_FakePipeline":
        """Enter the `async with` block."""

        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        """Exit the `async with` block."""


@pytest.fixture
def fake_redis() -> FakeRedis:
    """In-memory Redis stand-in. See `FakeRedis`.

    Returns
    -------
    FakeRedis
        A fresh fake client.
    """

    return FakeRedis()
