import random
import string
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from .conftest import (
    TEST_ADMIN_RECOVERY_CODES,
    TEST_ADMIN_USERNAME,
    TEST_USER_API_KEY_2,
    TEST_USERNAME,
)


@pytest.fixture(scope="function")
def temp_user_reset_password(
    client: TestClient,
    fullaccess_token_admin: str,
    request: pytest.FixtureRequest,
) -> Generator[tuple[str, list[str]], None, None]:
    json = {
        "username": request.param["username"],
        "password": request.param["password"],
        "is_admin": False,
    }
    response = client.post(
        "/user",
        json=json,
        headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
    )
    username = response.json()["username"]
    recovery_codes = response.json()["recovery_codes"]
    yield (username, recovery_codes)


class TestUserCreation:

    def test_admin_create_user(
        self, client: TestClient, fullaccess_token_admin: str
    ) -> None:
        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
            json={
                "username": "test_username_5",
                "password": "password",
                "content_quota": 50,
                "is_admin": False,
            },
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["username"] == "test_username_5"

    def test_admin_create_user_existing_user(
        self, client: TestClient, fullaccess_token_admin: str
    ) -> None:
        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
            json={
                "username": "test_username_5",
                "password": "password",
                "content_quota": 50,
                "is_admin": False,
            },
        )

        assert response.status_code == 400

    def test_non_admin_create_user(
        self, client: TestClient, fullaccess_token_user2: str
    ) -> None:
        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
            json={
                "username": "test_username_6",
                "password": "password",
                "content_quota": 50,
            },
        )

        assert response.status_code == 403

    def test_admin_create_admin_user(
        self, client: TestClient, fullaccess_token_admin: str
    ) -> None:
        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
            json={
                "username": "test_username_7",
                "password": "password",
                "content_quota": 50,
                "is_admin": True,
            },
        )
        assert response.status_code == 200
        json_response = response.json()
        assert "is_admin" in json_response
        assert json_response["is_admin"] is True


class TestUserUpdate:

    def test_admin_update_user(
        self, client: TestClient, admin_user: int, fullaccess_token_admin: str
    ) -> None:
        content_quota = 1500
        response = client.put(
            f"/user/{admin_user}",
            headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
            json={
                "username": TEST_ADMIN_USERNAME,
                "content_quota": content_quota,
                "is_admin": True,
            },
        )

        assert response.status_code == 200

        response = client.get(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
        )
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["content_quota"] == content_quota

    def test_admin_update_other_user(
        self,
        client: TestClient,
        user1: int,
        fullaccess_token_admin: str,
        fullaccess_token: str,
    ) -> None:
        content_quota = 1500
        response = client.put(
            f"/user/{user1}",
            headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
            json={
                "username": TEST_USERNAME,
                "content_quota": content_quota,
                "is_admin": False,
            },
        )
        assert response.status_code == 200

        response = client.get(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["content_quota"] == content_quota

    @pytest.mark.parametrize(
        "is_same_user",
        [
            (True),
            (False),
        ],
    )
    def test_non_admin_update_user(
        self,
        client: TestClient,
        is_same_user: bool,
        user1: int,
        user2: int,
        fullaccess_token_user2: str,
    ) -> None:
        user_id = user1 if is_same_user else user2
        response = client.put(
            f"/user/{user_id}",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
            json={
                "username": TEST_USERNAME,
                "content_quota": 1500,
                "is_admin": False,
            },
        )
        assert response.status_code == 403


class TestUserPasswordReset:

    @pytest.mark.parametrize(
        "temp_user_reset_password",
        [
            {
                "username": "temp_user_reset",
                "password": "test_password",  # pragma: allowlist secret
            },
        ],
        indirect=True,
    )
    def test_reset_password(
        self,
        client: TestClient,
        fullaccess_token_admin: str,
        temp_user_reset_password: tuple[str, list[str]],
    ) -> None:
        username, recovery_codes = temp_user_reset_password
        for code in recovery_codes:
            letters = string.ascii_letters
            random_string = "".join(random.choice(letters) for i in range(8))
            response = client.put(
                "/user/reset-password",
                headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
                json={
                    "username": username,
                    "password": random_string,
                    "recovery_code": code,
                },
            )

            assert response.status_code == 200

        response = client.put(
            "/user/reset-password",
            headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
            json={
                "username": "temp_user_reset",
                "password": "password",
                "recovery_code": code,
            },
        )

        assert response.status_code == 400

    @pytest.mark.parametrize(
        "temp_user_reset_password",
        [
            {
                "username": "temp_user_reset_non_admin",
                "password": "test_password",  # pragma: allowlist secret,
            }
        ],
        indirect=True,
    )
    def test_non_admin_user_reset_password(
        self,
        client: TestClient,
        fullaccess_token: str,
        temp_user_reset_password: tuple[str, list[str]],
    ) -> None:
        username, recovery_codes = temp_user_reset_password

        response = client.put(
            "/user/reset-password",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "username": username,
                "password": "password",
                "recovery_code": recovery_codes[1],
            },
        )

        assert response.status_code == 403

    def test_admin_user_reset_own_password(
        self, client: TestClient, fullaccess_token_admin: str
    ) -> None:
        response = client.put(
            "/user/reset-password",
            headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
            json={
                "username": TEST_ADMIN_USERNAME,
                "password": "password",
                "recovery_code": TEST_ADMIN_RECOVERY_CODES[0],
            },
        )

        assert response.status_code == 200

    def test_reset_password_invalid_recovery_code(
        self, client: TestClient, fullaccess_token_admin: str
    ) -> None:
        response = client.put(
            "/user/reset-password",
            headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
            json={
                "username": TEST_USERNAME,
                "password": "password",
                "recovery_code": "12345",
            },
        )

        assert response.status_code == 400

    def test_reset_password_invalid_user(
        self, client: TestClient, fullaccess_token_admin: str
    ) -> None:
        response = client.put(
            "/user/reset-password",
            headers={"Authorization": f"Bearer {fullaccess_token_admin}"},
            json={
                "username": "invalid_username",
                "password": "password",
                "recovery_code": "1234",
            },
        )

        assert response.status_code == 404


class TestUserFetching:
    def test_get_user(self, client: TestClient, fullaccess_token: str) -> None:
        response = client.get(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )

        assert response.status_code == 200
        json_response = response.json()
        expected_keys = [
            "user_id",
            "username",
            "content_quota",
            "is_admin",
            "api_daily_quota",
            "api_key_first_characters",
            "api_key_updated_datetime_utc",
            "created_datetime_utc",
            "updated_datetime_utc",
        ]
        for key in expected_keys:
            assert key in json_response


class TestKeyManagement:
    def test_get_new_api_key(
        self, client: TestClient, fullaccess_token_user2: str
    ) -> None:
        response = client.put(
            "/user/rotate-key",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["new_api_key"] != TEST_USER_API_KEY_2

    def test_get_new_api_key_query_with_old_key(
        self, client: TestClient, fullaccess_token_user2: str
    ) -> None:
        # get new api key (first time)
        rotate_key_response = client.put(
            "/user/rotate-key",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
        )
        assert rotate_key_response.status_code == 200
        json_response = rotate_key_response.json()
        first_api_key = json_response["new_api_key"]

        # make a QA call with this first key
        search_response = client.post(
            "/search",
            json={"query_text": "Tell me about a good sport to play"},
            headers={"Authorization": f"Bearer {first_api_key}"},
        )
        assert search_response.status_code == 200

        # get new api key (second time)
        rotate_key_response = client.put(
            "/user/rotate-key",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
        )
        assert rotate_key_response.status_code == 200
        json_response = rotate_key_response.json()
        second_api_key = json_response["new_api_key"]

        # make a QA call with the second key
        search_response = client.post(
            "/search",
            json={"query_text": "Tell me about a good sport to play"},
            headers={"Authorization": f"Bearer {second_api_key}"},
        )
        assert search_response.status_code == 200

        # make a QA call with the first key again
        search_response = client.post(
            "/search",
            json={"query_text": "Tell me about a good sport to play"},
            headers={"Authorization": f"Bearer {first_api_key}"},
        )
        assert search_response.status_code == 401
