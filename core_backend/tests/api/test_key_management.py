from fastapi.testclient import TestClient

from core_backend.tests.api.conftest import TEST_USER_RETRIEVAL_KEY


class TestKeyManagement:
    async def test_get_new_retrieval_key(
        self, client: TestClient, fullaccess_token: str
    ) -> None:
        response = client.put(
            "/key",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["new_retrieval_key"] != TEST_USER_RETRIEVAL_KEY
