from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


@pytest.fixture(
    scope="function",
    params=[
        ("test title 1", "test content - no metadata", {}),
        ("test title 2", "test content - with metadata", {"meta_key": "meta_value"}),
    ],
)
def existing_content_id(
    request: pytest.FixtureRequest, client: TestClient, fullaccess_token: str
) -> Generator[str, None, None]:
    response = client.post(
        "/content/create",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
        json={
            "content_title": request.param[0],
            "content_text": request.param[1],
            "content_language": "ENGLISH",
            "content_metadata": request.param[2],
        },
    )
    content_id = response.json()["content_id"]
    yield content_id
    client.delete(
        f"/content/{content_id}/delete",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
    )


class TestManageContent:
    @pytest.mark.parametrize(
        "content_title, content_text, content_metadata",
        [
            ("title 3", "test content 3", {}),
            ("title 2", "test content 2", {"meta_key": "meta_value"}),
        ],
    )
    def test_create_and_delete_content(
        self,
        client: TestClient,
        content_title: str,
        content_text: str,
        fullaccess_token: str,
        content_metadata: Dict[Any, Any],
    ) -> None:
        response = client.post(
            "/content/create",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": content_title,
                "content_text": content_text,
                "content_language": "ENGLISH",
                "content_metadata": content_metadata,
            },
        )
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["content_metadata"] == content_metadata
        assert "content_id" in json_response

        response = client.delete(
            f"/content/{json_response['content_id']}/delete",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "content_title, content_text, content_metadata",
        [
            ("test content 3 title - edited", "test content 3 - edited", {}),
            (
                "test content 4 title - edited",
                "test content 4 - edited",
                {"new_meta_key": "new meta_value", "meta_key": "meta_value_edited #2"},
            ),
        ],
    )
    def test_edit_and_retrieve_content(
        self,
        client: TestClient,
        existing_content_id: int,
        content_title: str,
        content_text: str,
        fullaccess_token: str,
        readonly_token: str,
        content_metadata: Dict[Any, Any],
    ) -> None:
        response = client.put(
            f"/content/{existing_content_id}/edit",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": content_title,
                "content_text": content_text,
                "content_language": "ENGLISH",
                "content_metadata": content_metadata,
            },
        )

        assert response.status_code == 200

        response = client.get(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 200
        assert response.json()["content_title"] == content_title
        assert response.json()["content_text"] == content_text
        edited_metadata = response.json()["content_metadata"]

        assert all(edited_metadata[k] == v for k, v in content_metadata.items())

    def test_edit_content_not_found(
        self, client: TestClient, fullaccess_token: str
    ) -> None:
        response = client.put(
            "/content/12345/edit",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "title",
                "content_text": "sample text",
                "content_language": "ENGLISH",
                "content_metadata": {"key": "value"},
            },
        )

        assert response.status_code == 404

    def test_list_content(
        self, client: TestClient, existing_content_id: int, readonly_token: str
    ) -> None:
        response = client.get(
            "/content/list", headers={"Authorization": f"Bearer {readonly_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_delete_content(
        self, client: TestClient, existing_content_id: int, fullaccess_token: str
    ) -> None:
        response = client.delete(
            f"/content/{existing_content_id}/delete",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == 200


class TestAuthManageContent:
    @pytest.mark.parametrize(
        "access_token, expected_status",
        [("readonly_token", 400), ("fullaccess_token", 200)],
    )
    def test_auth_delete(
        self,
        client: TestClient,
        existing_content_id: int,
        access_token: str,
        expected_status: int,
        request: pytest.FixtureRequest,
    ) -> None:
        access_token = request.getfixturevalue(access_token)
        response = client.delete(
            f"/content/{existing_content_id}/delete",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "access_token, expected_status",
        [("readonly_token", 400), ("fullaccess_token", 200)],
    )
    def test_auth_create(
        self,
        client: TestClient,
        access_token: str,
        expected_status: int,
        request: pytest.FixtureRequest,
    ) -> None:
        access_token = request.getfixturevalue(access_token)
        response = client.post(
            "/content/create",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "content_language": "ENGLISH",
                "content_metadata": {},
            },
        )
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "access_token, expected_status",
        [("readonly_token", 400), ("fullaccess_token", 200)],
    )
    def test_auth_edit(
        self,
        client: TestClient,
        existing_content_id: int,
        access_token: str,
        expected_status: int,
        request: pytest.FixtureRequest,
    ) -> None:
        access_token = request.getfixturevalue(access_token)
        response = client.put(
            f"/content/{existing_content_id}/edit",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "content_language": "ENGLISH",
                "content_metadata": {},
            },
        )
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "access_token, expected_status",
        [("readonly_token", 200), ("fullaccess_token", 200)],
    )
    def test_auth_list(
        self,
        client: TestClient,
        access_token: str,
        expected_status: int,
        request: pytest.FixtureRequest,
    ) -> None:
        access_token = request.getfixturevalue(access_token)
        response = client.get(
            "/content/list",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "access_token, expected_status",
        [("readonly_token", 200), ("fullaccess_token", 200)],
    )
    def test_auth_retrieve(
        self,
        client: TestClient,
        existing_content_id: int,
        access_token: str,
        expected_status: int,
        request: pytest.FixtureRequest,
    ) -> None:
        access_token = request.getfixturevalue(access_token)
        response = client.get(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == expected_status
