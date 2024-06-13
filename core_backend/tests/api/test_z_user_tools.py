from fastapi.testclient import TestClient

from core_backend.tests.api.conftest import TEST_USER_API_KEY_2


class TestUserCreation:
    async def test_admin_create_user(
        self, client: TestClient, fullaccess_token: str
    ) -> None:
        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={"username": "test_username_4", "password": "password"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["username"] == "test_username_4"
        assert json_response["user_id"] is not None

    async def test_admin_create_user_existing_user(
        self, client: TestClient, fullaccess_token: str
    ) -> None:
        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={"username": "test_username_4", "password": "password"},
        )

        assert response.status_code == 400

    async def test_non_admin_create_user(
        self, client: TestClient, fullaccess_token_user2: str
    ) -> None:
        response = client.post(
            "/user/",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
            json={"username": "test_username_5", "password": "password"},
        )

        assert response.status_code == 403


class TestKeyManagement:
    async def test_get_new_api_key(
        self, client: TestClient, fullaccess_token_user2: str
    ) -> None:
        response = client.put(
            "/user/rotate-key",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["new_api_key"] != TEST_USER_API_KEY_2
