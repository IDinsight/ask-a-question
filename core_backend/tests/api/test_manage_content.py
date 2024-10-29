from datetime import datetime, timezone
from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core_backend.app.auth.dependencies import create_access_token
from core_backend.app.contents.models import ContentDB
from core_backend.app.contents.routers import _convert_record_to_schema
from core_backend.app.users.models import UserDB
from core_backend.app.utils import get_key_hash, get_password_salted_hash

from .conftest import async_fake_embedding

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


@pytest.fixture(
    scope="function",
    params=[
        ("test title 1", "test content - no metadata", {}),
        ("test title 2", "test content - with metadata", {"meta_key": "meta_value"}),
    ],
)
def existing_content_id(
    request: pytest.FixtureRequest,
    client: TestClient,
    fullaccess_token: str,
    existing_tag_id: int,
) -> Generator[str, None, None]:
    response = client.post(
        "/content",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
        json={
            "content_title": request.param[0],
            "content_text": request.param[1],
            "content_tags": [],
            "content_metadata": request.param[2],
        },
    )
    content_id = response.json()["content_id"]
    yield content_id
    client.delete(
        f"/content/{content_id}",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
    )


@pytest.fixture(scope="class")
def temp_user_token_and_quota(
    request: pytest.FixtureRequest, client: TestClient, db_session: Session
) -> Generator[tuple[str, int], None, None]:
    username = request.param["username"]
    content_quota = request.param["content_quota"]

    temp_user_db = UserDB(
        username=username,
        hashed_password=get_password_salted_hash("temp_password"),
        hashed_api_key=get_key_hash("temp_api_key"),
        content_quota=content_quota,
        is_admin=False,
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
    )
    db_session.add(temp_user_db)
    db_session.commit()
    yield (create_access_token(username), content_quota)
    db_session.delete(temp_user_db)
    db_session.commit()


class TestContentQuota:
    @pytest.mark.parametrize(
        "temp_user_token_and_quota",
        [
            {"username": "temp_user_limit_0", "content_quota": 0},
            {"username": "temp_user_limit_1", "content_quota": 1},
            {"username": "temp_user_limit_5", "content_quota": 5},
        ],
        indirect=True,
    )
    async def test_content_quota_integer(
        self,
        client: TestClient,
        temp_user_token_and_quota: tuple[str, int],
    ) -> None:
        temp_user_token, content_quota = temp_user_token_and_quota

        added_content_ids = []
        for i in range(content_quota):
            response = client.post(
                "/content",
                headers={"Authorization": f"Bearer {temp_user_token}"},
                json={
                    "content_title": f"test title {i}",
                    "content_text": f"test content {i}",
                    "content_language": "ENGLISH",
                    "content_tags": [],
                    "content_metadata": {},
                },
            )
            assert response.status_code == 200
            added_content_ids.append(response.json()["content_id"])

        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {temp_user_token}"},
            json={
                "content_title": "test title",
                "content_text": "test content",
                "content_language": "ENGLISH",
                "content_tags": [],
                "content_metadata": {},
            },
        )
        assert response.status_code == 403

        for content_id in added_content_ids:
            response = client.delete(
                f"/content/{content_id}",
                headers={"Authorization": f"Bearer {temp_user_token}"},
            )
            assert response.status_code == 200

    @pytest.mark.parametrize(
        "temp_user_token_and_quota",
        [{"username": "temp_user_unlimited", "content_quota": None}],
        indirect=True,
    )
    async def test_content_quota_unlimited(
        self,
        client: TestClient,
        temp_user_token_and_quota: tuple[str, int],
    ) -> None:
        temp_user_token, content_quota = temp_user_token_and_quota

        # in this case we need to just be able to add content
        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {temp_user_token}"},
            json={
                "content_title": "test title",
                "content_text": "test content",
                "content_language": "ENGLISH",
                "content_tags": [],
                "content_metadata": {},
            },
        )
        assert response.status_code == 200

        content_id = response.json()["content_id"]
        response = client.delete(
            f"/content/{content_id}",
            headers={"Authorization": f"Bearer {temp_user_token}"},
        )
        assert response.status_code == 200


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
        existing_tag_id: int,
        content_metadata: Dict[Any, Any],
    ) -> None:
        content_tags = [existing_tag_id]
        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": content_title,
                "content_text": content_text,
                "content_tags": content_tags,
                "content_metadata": content_metadata,
            },
        )
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["content_metadata"] == content_metadata
        assert json_response["content_tags"] == content_tags
        assert "content_id" in json_response

        response = client.delete(
            f"/content/{json_response['content_id']}",
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
        content_metadata: Dict[Any, Any],
        existing_tag_id: int,
    ) -> None:
        content_tags = [existing_tag_id]
        response = client.put(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": content_title,
                "content_text": content_text,
                "content_tags": [existing_tag_id],
                "content_metadata": content_metadata,
            },
        )

        assert response.status_code == 200

        response = client.get(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == 200
        assert response.json()["content_title"] == content_title
        assert response.json()["content_text"] == content_text
        assert response.json()["content_tags"] == content_tags
        edited_metadata = response.json()["content_metadata"]

        assert all(edited_metadata[k] == v for k, v in content_metadata.items())

    def test_edit_content_not_found(
        self, client: TestClient, fullaccess_token: str
    ) -> None:
        response = client.put(
            "/content/12345",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "title",
                "content_text": "sample text",
                "content_metadata": {"key": "value"},
            },
        )

        assert response.status_code == 404

    def test_list_content(
        self,
        client: TestClient,
        existing_content_id: int,
        fullaccess_token: str,
        existing_tag_id: int,
    ) -> None:
        response = client.get(
            "/content", headers={"Authorization": f"Bearer {fullaccess_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_delete_content(
        self, client: TestClient, existing_content_id: int, fullaccess_token: str
    ) -> None:
        response = client.delete(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == 200


class TestMultUserManageContent:
    def test_user2_get_user1_content(
        self,
        client: TestClient,
        existing_content_id: str,
        fullaccess_token_user2: str,
    ) -> None:
        response = client.get(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
        )
        assert response.status_code == 404

    def test_user2_edit_user1_content(
        self,
        client: TestClient,
        existing_content_id: str,
        fullaccess_token_user2: str,
    ) -> None:
        response = client.put(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
            json={
                "content_title": "user2 title 3",
                "content_text": "user2 test content 3",
                "content_metadata": {},
            },
        )
        assert response.status_code == 404

    def test_user2_delete_user1_content(
        self,
        client: TestClient,
        existing_content_id: str,
        fullaccess_token_user2: str,
    ) -> None:
        response = client.delete(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
        )
        assert response.status_code == 404


async def test_convert_record_to_schema() -> None:
    content_id = 1
    user_id = 123
    record = ContentDB(
        content_id=content_id,
        user_id=user_id,
        content_title="sample title for content",
        content_text="sample text",
        content_embedding=await async_fake_embedding(),
        positive_votes=0,
        negative_votes=0,
        content_metadata={"extra_field": "extra value"},
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
        is_archived=False,
    )
    result = _convert_record_to_schema(record)
    assert result.content_id == content_id
    assert result.user_id == user_id
    assert result.content_text == "sample text"
    assert result.content_metadata["extra_field"] == "extra value"
