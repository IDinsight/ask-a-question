from fastapi.testclient import TestClient

from core_backend.tests.api.conftest import TEST_USER_API_KEY_2


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
