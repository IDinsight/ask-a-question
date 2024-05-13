from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.users.models import (
    UserAlreadyExistsError,
    UserDB,
    UserNotFoundError,
    get_user_by_token,
    get_user_by_username,
    save_user_to_db,
    update_user_retrieval_key,
)
from core_backend.app.users.schemas import UserCreate
from core_backend.app.utils import get_key_hash
from core_backend.tests.api.conftest import (
    TEST_PASSWORD,
    TEST_USER_ID,
    TEST_USER_RETRIEVAL_KEY,
    TEST_USERNAME,
)


@pytest.mark.asyncio(scope="module")
async def test_save_user_to_db(db_session: AsyncSession) -> None:
    user = UserCreate(
        user_id="2", username="test2", password="password2", retrieval_key="key2"
    )
    saved_user = await save_user_to_db(user, db_session)
    assert saved_user.username == "test2"


@pytest.mark.asyncio(scope="module")
async def test_save_user_to_db_existing_user(db_session: AsyncSession) -> None:
    user = UserCreate(
        user_id=TEST_USER_ID,
        username=TEST_USERNAME,
        password=TEST_PASSWORD,
        retrieval_key=TEST_USER_RETRIEVAL_KEY,
    )
    with pytest.raises(UserAlreadyExistsError):
        await save_user_to_db(user, db_session)


@pytest.mark.asyncio(scope="module")
async def test_get_user_by_username(db_session: AsyncSession) -> None:
    retrieved_user = await get_user_by_username(TEST_USERNAME, db_session)
    assert retrieved_user.username == TEST_USERNAME


@pytest.mark.asyncio(scope="module")
async def test_get_user_by_username_no_user(db_session: AsyncSession) -> None:
    with pytest.raises(UserNotFoundError):
        await get_user_by_username("nonexistent", db_session)


@pytest.mark.asyncio(scope="module")
async def test_get_user_by_token(db_session: AsyncSession) -> None:
    retrieved_user = await get_user_by_token(TEST_USER_RETRIEVAL_KEY, db_session)
    assert retrieved_user.username == TEST_USERNAME


@pytest.mark.asyncio(scope="module")
async def test_get_user_by_token_no_user(db_session: AsyncSession) -> None:
    with pytest.raises(UserNotFoundError):
        await get_user_by_token("nonexistent", db_session)


@pytest.mark.asyncio(scope="module")
async def test_update_user_retrieval_key(db_session: AsyncSession) -> None:
    user_db = UserDB(
        user_id=TEST_USER_ID,
        username=TEST_USERNAME,
        hashed_password=get_key_hash(TEST_PASSWORD),
        hashed_retrieval_key=get_key_hash("new_key"),
        created_datetime_utc=datetime.utcnow(),
        updated_datetime_utc=datetime.utcnow(),
    )
    updated_user = await update_user_retrieval_key(user_db, "new_key", db_session)
    assert updated_user.hashed_retrieval_key != get_key_hash(TEST_USER_RETRIEVAL_KEY)
