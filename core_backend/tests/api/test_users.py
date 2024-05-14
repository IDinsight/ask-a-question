from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.database import get_async_session
from core_backend.app.users.models import (
    UserAlreadyExistsError,
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


class TestUsers:
    @pytest.fixture(scope="function")
    async def asession(self) -> AsyncGenerator[AsyncSession, None]:
        async for session in get_async_session():
            yield session

        await session.close()

    async def test_save_user_to_db(self, asession: AsyncSession) -> None:
        user = UserCreate(
            user_id="test_user_id_3",
            username="test_username_3",
            password="test_password_3",
            retrieval_key="test_retrieval_key_3",
        )
        saved_user = await save_user_to_db(user, asession)
        assert saved_user.username == "test_username_3"

    async def test_save_user_to_db_existing_user(self, asession: AsyncSession) -> None:
        user = UserCreate(
            user_id=TEST_USER_ID,
            username=TEST_USERNAME,
            password=TEST_PASSWORD,
            retrieval_key=TEST_USER_RETRIEVAL_KEY,
        )
        with pytest.raises(UserAlreadyExistsError):
            await save_user_to_db(user, asession)

    async def test_get_user_by_username(self, asession: AsyncSession) -> None:
        retrieved_user = await get_user_by_username(TEST_USERNAME, asession)
        assert retrieved_user.username == TEST_USERNAME

    async def test_get_user_by_username_no_user(self, asession: AsyncSession) -> None:
        with pytest.raises(UserNotFoundError):
            await get_user_by_username("nonexistent", asession)

    async def test_get_user_by_token(self, asession: AsyncSession) -> None:
        retrieved_user = await get_user_by_token(TEST_USER_RETRIEVAL_KEY, asession)
        assert retrieved_user.username == TEST_USERNAME

    async def test_get_user_by_token_no_user(self, asession: AsyncSession) -> None:
        with pytest.raises(UserNotFoundError):
            await get_user_by_token("nonexistent", asession)

    async def test_update_user_retrieval_key(self, asession: AsyncSession) -> None:
        user = UserCreate(
            user_id="test_user_id_4",
            username="test_username_4",
            password="test_password_4",
            retrieval_key="test_retrieval_key_4",
        )
        saved_user = await save_user_to_db(user, asession)
        assert saved_user.hashed_retrieval_key == get_key_hash("test_retrieval_key_4")

        updated_user = await update_user_retrieval_key(saved_user, "new_key", asession)
        assert updated_user.hashed_retrieval_key != get_key_hash("test_retrieval_key_4")
        assert updated_user.hashed_retrieval_key == get_key_hash("new_key")
