import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.users.models import (
    UserAlreadyExistsError,
    UserNotFoundError,
    get_user_by_token,
    get_user_by_username,
    save_user_to_db,
    update_user_api_key,
)
from core_backend.app.users.schemas import UserCreate
from core_backend.app.utils import get_key_hash
from core_backend.tests.api.conftest import (
    TEST_USER_API_KEY,
    TEST_USERNAME,
)


class TestUsers:
    async def test_save_user_to_db(self, asession: AsyncSession) -> None:
        user = UserCreate(username="test_username_3", content_quota=50)
        saved_user = await save_user_to_db(user, asession)
        assert saved_user.username == "test_username_3"

    async def test_save_user_to_db_existing_user(self, asession: AsyncSession) -> None:
        user = UserCreate(username=TEST_USERNAME, content_quota=50)
        with pytest.raises(UserAlreadyExistsError):
            await save_user_to_db(user, asession)

    async def test_get_user_by_username(self, asession: AsyncSession) -> None:
        retrieved_user = await get_user_by_username(TEST_USERNAME, asession)
        assert retrieved_user.username == TEST_USERNAME

    async def test_get_user_by_username_no_user(self, asession: AsyncSession) -> None:
        with pytest.raises(UserNotFoundError):
            await get_user_by_username("nonexistent", asession)

    async def test_get_user_by_token(self, asession: AsyncSession) -> None:
        retrieved_user = await get_user_by_token(TEST_USER_API_KEY, asession)
        assert retrieved_user.username == TEST_USERNAME

    async def test_get_user_by_token_no_user(self, asession: AsyncSession) -> None:
        with pytest.raises(UserNotFoundError):
            await get_user_by_token("nonexistent", asession)

    async def test_update_user_api_key(self, asession: AsyncSession) -> None:
        user = UserCreate(username="test_username_4", content_quota=50)
        saved_user = await save_user_to_db(user, asession)
        assert saved_user.hashed_api_key is None

        updated_user = await update_user_api_key(saved_user, "new_key", asession)
        assert updated_user.hashed_api_key is not None
        assert updated_user.hashed_api_key == get_key_hash("new_key")
