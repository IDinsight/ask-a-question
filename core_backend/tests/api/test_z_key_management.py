from fastapi.testclient import TestClient

from core_backend.tests.api.conftest import TEST_USER_API_KEY_2


class TestKeyManagement:
    async def test_get_new_api_key(
        self, client: TestClient, fullaccess_token_user2: str
    ) -> None:
        response = client.put(
            "/key",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["new_api_key"] != TEST_USER_API_KEY_2
