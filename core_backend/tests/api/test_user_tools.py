from fastapi.testclient import TestClient

from core_backend.tests.api.conftest import TEST_USER_API_KEY_2


class TestUserCreation:
    def test_admin_create_user(self, client: TestClient, fullaccess_token: str) -> None:
        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "username": "test_username_5",
                "password": "password",
                "content_quota": 50,
            },
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["username"] == "test_username_5"

    def test_admin_create_user_existing_user(
        self, client: TestClient, fullaccess_token: str
    ) -> None:
        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "username": "test_username_5",
                "password": "password",
                "content_quota": 50,
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
