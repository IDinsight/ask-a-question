"""This module contains fixtures for the API tests."""

# pylint: disable=W0613, W0621
import json
from datetime import datetime, timezone, tzinfo
from typing import Any, AsyncGenerator, Generator, Optional

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pytest_alembic.config import Config
from redis import asyncio as aioredis
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from core_backend.app import create_app
from core_backend.app.auth.dependencies import create_access_token
from core_backend.app.config import (
    LITELLM_API_KEY,
    LITELLM_ENDPOINT,
    LITELLM_MODEL_EMBEDDING,
    PGVECTOR_VECTOR_SIZE,
    REDIS_HOST,
)
from core_backend.app.contents.models import ContentDB
from core_backend.app.database import (
    SYNC_DB_API,
    get_connection_url,
    get_session_context_manager,
)
from core_backend.app.llm_call import process_input, process_output
from core_backend.app.llm_call.llm_prompts import (
    RAG,
    AlignmentScore,
    IdentifiedLanguage,
)
from core_backend.app.question_answer.models import (
    ContentFeedbackDB,
    QueryResponseContentDB,
)
from core_backend.app.question_answer.schemas import QueryRefined, QueryResponse
from core_backend.app.urgency_detection.models import UrgencyQueryDB, UrgencyResponseDB
from core_backend.app.urgency_rules.models import UrgencyRuleDB
from core_backend.app.users.models import (
    UserDB,
    UserWorkspaceDB,
    WorkspaceDB,
)
from core_backend.app.users.schemas import UserRoles
from core_backend.app.utils import get_key_hash, get_password_salted_hash
from core_backend.app.workspaces.utils import get_workspace_by_workspace_name

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

    app = create_app()
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

    return Config({"file": "alembic.ini"})


@pytest.fixture(scope="function")
def alembic_engine() -> Engine:
    """`alembic_engine` is where you specify the engine with which the alembic_runner
    should execute your tests.

    NB: The engine should point to a database that must be empty. It is out of scope
    for `pytest-alembic` to manage the database state.

    Returns
    -------
    Engine
        A SQLAlchemy engine object.
    """

    return create_engine(get_connection_url(db_api=SYNC_DB_API))


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

    with open("tests/api/data/content.json", "r", encoding="utf-8") as f:
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

    with open("tests/api/data/content.json", "r", encoding="utf-8") as f:
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

    with open("tests/api/data/content.json", "r", encoding="utf-8") as f:
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

    with open("tests/api/data/content.json", "r", encoding="utf-8") as f:
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

    monkeysession.setattr(
        "core_backend.app.contents.models.embedding", async_fake_embedding
    )
    monkeysession.setattr(
        "core_backend.app.urgency_rules.models.embedding", async_fake_embedding
    )
    monkeysession.setattr(process_input, "_classify_safety", mock_return_args)
    monkeysession.setattr(process_input, "_identify_language", mock_identify_language)
    monkeysession.setattr(process_input, "_paraphrase_question", mock_return_args)
    monkeysession.setattr(process_input, "_translate_question", mock_translate_question)
    monkeysession.setattr(process_output, "_get_llm_align_score", mock_get_align_score)
    monkeysession.setattr(
        "core_backend.app.urgency_detection.routers.detect_urgency", mock_detect_urgency
    )
    monkeysession.setattr(
        "core_backend.app.llm_call.process_output.get_llm_rag_answer",
        patched_llm_rag_answer,
    )


@pytest.fixture(scope="session", autouse=True)
def patch_voice_gcs_functions(monkeysession: pytest.MonkeyPatch) -> None:
    """Monkeypatch GCS functions to replace their real implementations with dummy ones.

    Parameters
    ----------
    monkeysession
        Pytest monkeypatch object.
    """

    monkeysession.setattr(
        "core_backend.app.question_answer.routers.upload_file_to_gcs",
        async_fake_upload_file_to_gcs,
    )
    monkeysession.setattr(
        "core_backend.app.llm_call.process_output.upload_file_to_gcs",
        async_fake_upload_file_to_gcs,
    )
    monkeysession.setattr(
        "core_backend.app.llm_call.process_output.generate_public_url",
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
        hashed_password=get_password_salted_hash(key="temp_password"),
        updated_datetime_utc=datetime.now(timezone.utc),
        username=username,
    )
    db_session.add(temp_user_db)
    db_session.flush()

    temp_workspace_db = WorkspaceDB(
        api_daily_quota=api_daily_quota,
        created_datetime_utc=datetime.now(timezone.utc),
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
        hashed_password=get_password_salted_hash(key="temp_password"),
        updated_datetime_utc=datetime.now(timezone.utc),
        username=username,
    )
    db_session.add(temp_user_db)
    db_session.flush()

    temp_workspace_db = WorkspaceDB(
        content_quota=content_quota,
        created_datetime_utc=datetime.now(timezone.utc),
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

    with open("tests/api/data/urgency_rules.json", "r", encoding="utf-8") as f:
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

    with open("tests/api/data/urgency_rules.json", "r", encoding="utf-8") as f:
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

    with open("tests/api/data/urgency_rules.json", "r", encoding="utf-8") as f:
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


async def mock_detect_urgency(
    urgency_rules: list[str], message: str, metadata: Optional[dict]
) -> dict[str, Any]:
    """Mock function arguments for the `detect_urgency` function.

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
    dict[str, Any]
        The urgency detection result.
    """

    return {
        "best_matching_rule": "made up rule",
        "probability": 0.7,
        "reason": "this is a mocked response",
    }


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
