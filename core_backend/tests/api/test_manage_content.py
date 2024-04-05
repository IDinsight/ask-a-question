from datetime import datetime
from datetime import timezone as tz
from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient

from core_backend.app.contents.models import ContentTextDB
from core_backend.app.contents.routers import (
    _convert_record_to_schema,
    _convert_summary_to_schema,
)

from .conftest import fake_embedding


DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


@pytest.fixture(
    scope="function",
    params=[
        ("test title 1", "test content - no metadata", {}),
        ("test title 2", "test content - with metadata", {"meta_key": "meta_value"}),
    ],
)
def existing_content_ids(
    request: pytest.FixtureRequest,
    client: TestClient,
    existing_languages: tuple,
    fullaccess_token: str,
) -> Generator[tuple, None, None]:
    response = client.post(
        "/content/",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
        json={
            "content_title": request.param[0],
            "content_text": request.param[1],
            "content_id": None,
            "language_id": existing_languages[0]["language_id"],
            "content_metadata": request.param[2],
        },
    )
    content_text_id, content_id = (
        response.json()["content_text_id"],
        response.json()["content_id"],
    )
    yield (content_id, content_text_id)
    client.delete(
        f"/content/{content_id}/",
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
        existing_languages: tuple,
        content_title: str,
        content_text: str,
        fullaccess_token: str,
        content_metadata: Dict[Any, Any],
    ) -> None:
        response = client.post(
            "/content/",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": content_title,
                "content_text": content_text,
                "language_id": existing_languages[0]["language_id"],
                "content_metadata": content_metadata,
            },
        )
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["content_metadata"] == content_metadata
        assert "content_id" in json_response

        response = client.delete(
            f"/content/{json_response['content_id']}/",
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
        existing_content_ids: tuple[int, int],
        existing_languages: tuple,
        content_title: str,
        content_text: str,
        fullaccess_token: str,
        readonly_token: str,
        content_metadata: Dict[Any, Any],
    ) -> None:
        content_id, _ = existing_content_ids
        response = client.put(
            f"/content/{content_id}?language_id={existing_languages[0]['language_id']}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": content_title,
                "content_text": content_text,
                "content_id": content_id,
                "language_id": existing_languages[0]["language_id"],
                "content_metadata": content_metadata,
            },
        )

        assert response.status_code == 200

        response = client.get(
            f"/content/{content_id}?language={existing_languages[0]['language_name']}",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 200
        assert response.json()["content_title"] == content_title
        assert response.json()["content_text"] == content_text
        edited_metadata = response.json()["content_metadata"]

        assert all(edited_metadata[k] == v for k, v in content_metadata.items())

    def test_edit_content_not_found(
        self,
        client: TestClient,
        existing_languages: tuple,
        fullaccess_token: str,
    ) -> None:
        response = client.put(
            f"/content/12345?language_id={existing_languages[0]['language_id']}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "title",
                "content_text": "sample text",
                "content_id": 12345,
                "language_id": existing_languages[0]["language_id"],
                "content_metadata": {"key": "value"},
            },
        )
        assert response.status_code == 404

    def test_list_content(
        self,
        client: TestClient,
        existing_content_ids: tuple[int, int],
        readonly_token: str,
    ) -> None:
        response = client.get(
            "/content/", headers={"Authorization": f"Bearer {readonly_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_delete_content(
        self,
        client: TestClient,
        existing_content_ids: tuple[int, int],
        fullaccess_token: str,
    ) -> None:
        response = client.delete(
            f"/content/{existing_content_ids[0]}/",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == 200

    def test_add_content_text_to_content(
        self,
        client: TestClient,
        existing_content_ids: tuple[int, int],
        existing_languages: tuple,
        fullaccess_token: str,
    ) -> None:
        response = client.put(
            f"/content/{existing_content_ids[0]}?language_id={existing_languages[1]['language_id']}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "content_id": existing_content_ids[0],
                "language_id": existing_languages[1]["language_id"],
                "content_metadata": {},
            },
        )

        assert response.status_code == 200

    def test_adding_text_with_non_existing_language(
        self, client: TestClient, fullaccess_token: str
    ) -> None:
        response = client.post(
            "/content/",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "language_id": 4000,
                "content_metadata": {},
            },
        )
        assert response.status_code == 400

    def test_retrieve_all_language_versions_of_content(
        self,
        client: TestClient,
        existing_content_ids: tuple[int, int],
        existing_languages: tuple[dict, dict],
        fullaccess_token: str,
        readonly_token: str,
    ) -> None:
        response = client.put(
            f"/content/{existing_content_ids[0]}?language_id={existing_languages[1]['language_id']}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "content_id": existing_content_ids[0],
                "language_id": existing_languages[1]["language_id"],
                "content_metadata": {},
            },
        )
        assert response.status_code == 200
        response = client.get(
            f"/content/{existing_content_ids[0]}",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert response.json()[0]["content_id"] == response.json()[1]["content_id"]
        assert response.json()[0]["content_id"] == existing_content_ids[0]

    def test_retrieve_one_language_version_of_content(
        self,
        client: TestClient,
        existing_content_ids: tuple[int, int],
        existing_languages: tuple[dict, dict],
        fullaccess_token: str,
        readonly_token: str,
    ) -> None:
        response = client.get(
            f"/content/{existing_content_ids[0]}?language={existing_languages[0]['language_name']}",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 200
        assert response.json()["content_id"] == existing_content_ids[0]
        assert response.json()["language_id"] == existing_languages[0]["language_id"]

    def test_delete_language_version_of_content(
        self,
        client: TestClient,
        existing_content_ids: tuple[int, int],
        existing_languages: tuple[dict, dict],
        fullaccess_token: str,
        readonly_token: str,
    ) -> None:
        response = client.put(
            f"/content/{existing_content_ids[0]}?language_id={existing_languages[1]['language_id']}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "content_id": existing_content_ids[0],
                "language_id": existing_languages[1]["language_id"],
                "content_metadata": {},
            },
        )
        assert response.status_code == 200
        response = client.delete(
            f"/content/{existing_content_ids[0]}?language_id={existing_languages[1]['language_id']}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == 200

        response = client.get(
            f"/content/{existing_content_ids[0]}?language={existing_languages[1]['language_name']}",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 404

        response = client.get(
            f"/content/{existing_content_ids[0]}",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_delete_all_language_versions_of_content(
        self,
        client: TestClient,
        existing_content_ids: tuple[int, int],
        existing_languages: tuple[dict, dict],
        fullaccess_token: str,
        readonly_token: str,
    ) -> None:
        response = client.post(
            "/content/",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "language_id": existing_languages[0]["language_id"],
                "content_metadata": {},
            },
        )
        assert response.status_code == 200
        content_id = response.json()["content_id"]

        response = client.put(
            f"/content/{content_id}?language_id={existing_languages[1]['language_id']}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "content_id": content_id,
                "language_id": existing_languages[1]["language_id"],
                "content_metadata": {},
            },
        )
        assert response.status_code == 200
        response = client.delete(
            f"/content/{content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == 200

        response = client.get(
            f"/content/{content_id}",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 404

    def test_retrieve_summary(
        self,
        client: TestClient,
        existing_content_ids: tuple[int, int],
        existing_languages: tuple[int, int],
        readonly_token: str,
        fullaccess_token: str,
    ) -> None:
        response = client.put(
            f"/content/{existing_content_ids[0]}?language_id={existing_languages[1]['language_id']}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "content_id": existing_content_ids[0],
                "language_id": existing_languages[1]["language_id"],
                "content_metadata": {},
            },
        )
        assert response.status_code == 200

        response = client.get(
            f"/content/landing?language={existing_languages[0]['language_name']}",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        assert response.status_code == 200

        response_json = response.json()
        assert len(response_json) > 0
        assert len(response_json[0]["languages"]) == 2


class TestAuthManageContent:
    @pytest.mark.parametrize(
        "access_token, expected_status",
        [("readonly_token", 400), ("fullaccess_token", 200)],
    )
    def test_auth_delete(
        self,
        client: TestClient,
        existing_content_ids: tuple[int, int],
        access_token: str,
        expected_status: int,
        request: pytest.FixtureRequest,
    ) -> None:
        access_token = request.getfixturevalue(access_token)
        response = client.delete(
            f"/content/{existing_content_ids[0]}/",
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
        existing_languages: tuple,
        access_token: str,
        expected_status: int,
        request: pytest.FixtureRequest,
    ) -> None:
        access_token = request.getfixturevalue(access_token)
        response = client.post(
            "/content/",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "language_id": existing_languages[0]["language_id"],
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
        existing_content_ids: tuple[int, int],
        existing_languages: tuple,
        access_token: str,
        expected_status: int,
        request: pytest.FixtureRequest,
    ) -> None:
        access_token = request.getfixturevalue(access_token)
        content_id, _ = existing_content_ids
        response = client.put(
            f"/content/{content_id}?language_id={existing_languages[0]['language_id']}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "content_title": "sample title",
                "content_text": "sample text",
                "content_id": content_id,
                "language_id": existing_languages[0]["language_id"],
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
            "/content/",
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
        existing_content_ids: tuple[int, int],
        existing_languages,
        access_token: str,
        expected_status: int,
        request: pytest.FixtureRequest,
    ) -> None:
        access_token = request.getfixturevalue(access_token)
        response = client.get(
            f"/content/{existing_content_ids[0]}?language_id={existing_languages[0]['language_id']}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == expected_status


def test_convert_record_to_schema() -> None:
    content_text_id = 1
    record = ContentTextDB(
        content_text_id=content_text_id,
        content_title="sample title for content",
        content_text="sample text",
        content_embedding=fake_embedding(),
        content_id=0,
        language_id=1,
        content_metadata={"extra_field": "extra value"},
        created_datetime_utc=datetime.now(tz.utc).replace(tzinfo=None),
        updated_datetime_utc=datetime.now(tz.utc).replace(tzinfo=None),
    )
    result = _convert_record_to_schema(record)
    assert result.content_text_id == content_text_id
    assert result.content_text == "sample text"
    assert result.content_metadata["extra_field"] == "extra value"


def test_convert_summary_to_schema() -> None:
    content_text_id = 1
    record = (
        content_text_id,
        1,
        "Sample title",
        "Sample text",
        datetime.now(tz.utc).replace(tzinfo=None),
        datetime.now(tz.utc).replace(tzinfo=None),
        ["ENGLISH", "HINDI"],
    )
    result = _convert_summary_to_schema(record)
    assert result.content_text_id == content_text_id
    assert result.content_title == "Sample title"
    assert len(result.languages) == 2
