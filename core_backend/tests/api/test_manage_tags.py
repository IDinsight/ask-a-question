from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from core_backend.app.tags.models import TagDB
from core_backend.app.tags.routers import _convert_record_to_schema

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


@pytest.fixture(
    scope="function",
    params=[
        ("Tag1"),
        ("tag3",),
    ],
)
def existing_tag_id(
    request: pytest.FixtureRequest, client: TestClient, fullaccess_token: str
) -> Generator[str, None, None]:
    response = client.post(
        "/tag",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
        json={
            "tag_name": request.param[0],
        },
    )
    tag_id = response.json()["tag_id"]
    yield tag_id
    client.delete(
        f"/tag/{tag_id}",
        headers={"Authorization": f"Bearer {fullaccess_token}"},
    )


class TestManageTags:
    @pytest.mark.parametrize(
        "tag_name",
        [
            ("tag_first"),
            ("tag_second"),
        ],
    )
    async def test_create_and_delete_tag(
        self,
        client: TestClient,
        tag_name: str,
        fullaccess_token: str,
    ) -> None:
        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "tag_name": tag_name,
            },
        )
        assert response.status_code == 200
        json_response = response.json()
        assert "tag_id" in json_response

        response = client.delete(
            f"/tag/{json_response['tag_id']}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "tag_name",
        [
            ("TAG_FIRST"),
            ("TAG_SECOND"),
        ],
    )
    def test_edit_and_retrieve_tag(
        self,
        client: TestClient,
        existing_tag_id: int,
        tag_name: str,
        fullaccess_token: str,
    ) -> None:
        response = client.put(
            f"/tag/{existing_tag_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "tag_name": tag_name,
            },
        )

        assert response.status_code == 200

        response = client.get(
            f"/tag/{existing_tag_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == 200
        assert response.json()["tag_name"] == tag_name

    def test_edit_tag_not_found(
        self, client: TestClient, fullaccess_token: str
    ) -> None:
        response = client.put(
            "/tag/12345",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "tag_name": "tag",
            },
        )

        assert response.status_code == 404

    def test_list_tag(
        self,
        client: TestClient,
        existing_tag_id: int,
        fullaccess_token: str,
    ) -> None:
        response = client.get(
            "/tag", headers={"Authorization": f"Bearer {fullaccess_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0

    @pytest.mark.parametrize(
        "tag_name_1,tag_name_2",
        [
            ("TAG1", "TAG1"),
            ("Tag2", "TAG2"),
        ],
    )
    def test_add_tag_same_name_fails(
        self,
        client: TestClient,
        tag_name_1: str,
        tag_name_2: str,
        fullaccess_token: str,
    ) -> None:
        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "tag_name": tag_name_1,
            },
        )
        assert response.status_code == 200
        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "tag_name": tag_name_2,
            },
        )
        assert response.status_code == 400

    def test_delete_tag(
        self, client: TestClient, existing_tag_id: int, fullaccess_token: str
    ) -> None:
        response = client.delete(
            f"/tag/{existing_tag_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == 200

    def test_user2_get_user1_tag_fails(
        self,
        client: TestClient,
        existing_tag_id: int,
        fullaccess_token_user2: str,
    ) -> None:
        response = client.get(
            f"/tag/{existing_tag_id}",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
        )
        assert response.status_code == 404

    def test_add_tag_user1_edit_user2_fails(
        self,
        client: TestClient,
        fullaccess_token: str,
        fullaccess_token_user2: str,
    ) -> None:
        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "tag_name": "tag",
            },
        )
        assert response.status_code == 200
        tag_id = response.json()["tag_id"]
        response = client.put(
            f"/tag/{tag_id}",
            headers={"Authorization": f"Bearer {fullaccess_token_user2}"},
            json={
                "tag_name": "tag",
            },
        )
        assert response.status_code == 404


def test_convert_record_to_schema() -> None:
    tag_id = 1
    user_id = 123
    record = TagDB(
        tag_id=tag_id,
        user_id=user_id,
        tag_name="tag",
        created_datetime_utc=datetime.now(timezone.utc),
        updated_datetime_utc=datetime.now(timezone.utc),
    )
    result = _convert_record_to_schema(record)
    assert result.tag_id == tag_id
    assert result.user_id == user_id
    assert result.tag_name == "tag"
