from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient


class TestManageContent:
    @pytest.fixture(
        scope="function",
        params=[
            ("test content - no metadata", {}),
            ("test content - with metadata", {"meta_key": "meta_value"}),
        ],
    )
    def existing_content_id(
        self, request: pytest.FixtureRequest, client: TestClient
    ) -> Generator[str, None, None]:
        response = client.post(
            "/content/create",
            json={
                "content_text": request.param[0],
                "content_metadata": request.param[1],
            },
        )
        content_id = response.json()["content_id"]
        yield content_id
        client.delete(f"/content/{content_id}/delete")

    @pytest.mark.parametrize(
        "content_text, content_metadata",
        [("test content 3", {}), ("test content 2", {"meta_key": "meta_value"})],
    )
    def test_create_and_delete_content(
        self,
        client: TestClient,
        content_text: str,
        content_metadata: Dict[Any, Any],
    ) -> None:
        response = client.post(
            "/content/create",
            json={"content_text": content_text, "content_metadata": content_metadata},
        )
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["content_metadata"] == content_metadata
        assert "content_id" in json_response

        response = client.delete(f"/content/{json_response['content_id']}/delete")
        assert response.status_code == 200

        pass

    @pytest.mark.parametrize(
        "content_text, content_metadata",
        [
            ("test content 3 - edited", {}),
            (
                "test content 4 - edited",
                {"new_meta_key": "new meta_value", "meta_key": "meta_value_edited #2"},
            ),
        ],
    )
    def test_edit_and_retrieve_content(
        self,
        client: TestClient,
        existing_content_id: str,
        content_text: str,
        content_metadata: Dict[Any, Any],
    ) -> None:
        response = client.put(
            f"/content/{existing_content_id}/edit",
            json={
                "content_text": content_text,
                "content_metadata": content_metadata,
            },
        )
        assert response.status_code == 200

        response = client.get(f"/content/{existing_content_id}")
        assert response.status_code == 200
        assert response.json()["content_text"] == content_text
        edited_metadata = response.json()["content_metadata"]

        assert all(edited_metadata[k] == v for k, v in content_metadata.items())

    def test_list_content(self, client: TestClient, existing_content_id: str) -> None:
        response = client.get("/content/list")
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_delete_content(self, client: TestClient, existing_content_id: str) -> None:
        response = client.delete(f"/content/{existing_content_id}/delete")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "content_metadata",
        [{}, {"meta_key": "meta_value"}],
    )
    def test_creating_missing_content_text_returns_422(
        self, client: TestClient, content_metadata: Dict[Any, Any]
    ) -> None:
        response = client.post(
            "/content/create",
            json=content_metadata,
        )
        assert response.status_code == 422
