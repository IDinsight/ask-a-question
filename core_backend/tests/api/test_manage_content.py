"""This module contains tests for the content management API endpoints."""

from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from core_backend.app.contents.models import ContentDB
from core_backend.app.contents.routers import _convert_record_to_schema

from .conftest import async_fake_embedding

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


@pytest.fixture(
    scope="function",
    params=[
        ("test title 1", "test content - no metadata", {}),
        ("test title 2", "test content - with metadata", {"meta_key": "meta_value"}),
    ],
)
def existing_content_id_in_workspace_1(
    access_token_admin_1: str,
    client: TestClient,
    existing_tag_id_in_workspace_1: int,
    request: pytest.FixtureRequest,
) -> Generator[str, None, None]:
    """Create a content record in workspace 1.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1.
    client
        The test client.
    existing_tag_id_in_workspace_1
        The tag ID for the tag created in workspace 1.
    request
        The pytest request object.

    Yields
    ------
    Generator[str, None, None]
        The content ID of the created content record in workspace 1.
    """

    response = client.post(
        "/content",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
        json={
            "content_metadata": request.param[2],
            "content_tags": [],
            "content_text": request.param[1],
            "content_title": request.param[0],
        },
    )
    content_id = response.json()["content_id"]

    yield content_id

    client.delete(
        f"/content/{content_id}",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )


class TestContentQuota:
    """Tests for the content quota feature."""

    @pytest.mark.parametrize(
        "temp_workspace_token_and_quota",
        [
            {
                "content_quota": 0,
                "username": "temp_user_limit_0",
                "workspace_name": "temp_workspace_limit_0",
            },
            {
                "content_quota": 1,
                "username": "temp_user_limit_1",
                "workspace_name": "temp_workspace_limit_1",
            },
            {
                "content_quota": 5,
                "username": "temp_user_limit_5",
                "workspace_name": "temp_user_limit_5",
            },
        ],
        indirect=True,
    )
    async def test_content_quota_integer(
        self, client: TestClient, temp_workspace_token_and_quota: tuple[str, int]
    ) -> None:
        """Test the content quota feature with integer values.

        Parameters
        ----------
        client
            The test client.
        temp_workspace_token_and_quota
            The temporary workspace token and content quota.
        """

        temp_workspace_token, content_quota = temp_workspace_token_and_quota
        added_content_ids = []
        for i in range(content_quota):
            response = client.post(
                "/content",
                headers={"Authorization": f"Bearer {temp_workspace_token}"},
                json={
                    "content_language": "ENGLISH",
                    "content_metadata": {},
                    "content_tags": [],
                    "content_text": f"test content {i}",
                    "content_title": f"test title {i}",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            added_content_ids.append(response.json()["content_id"])

        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {temp_workspace_token}"},
            json={
                "content_language": "ENGLISH",
                "content_metadata": {},
                "content_tags": [],
                "content_text": "test content",
                "content_title": "test title",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        for content_id in added_content_ids:
            response = client.delete(
                f"/content/{content_id}",
                headers={"Authorization": f"Bearer {temp_workspace_token}"},
            )
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize(
        "temp_workspace_token_and_quota",
        [
            {
                "content_quota": None,
                "username": "temp_user_unlimited",
                "workspace_name": "temp_workspace_unlimited",
            }
        ],
        indirect=True,
    )
    async def test_content_quota_unlimited(
        self, client: TestClient, temp_workspace_token_and_quota: tuple[str, int]
    ) -> None:
        """Test the content quota feature with unlimited quota.

        Parameters
        ----------
        client
            The test client.
        temp_workspace_token_and_quota
            The temporary workspace token and content quota.
        """

        temp_workspace_token, _ = temp_workspace_token_and_quota

        # In this case we need to just be able to add content.
        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {temp_workspace_token}"},
            json={
                "content_language": "ENGLISH",
                "content_metadata": {},
                "content_tags": [],
                "content_text": "test content",
                "content_title": "test title",
            },
        )
        assert response.status_code == status.HTTP_200_OK

        content_id = response.json()["content_id"]
        response = client.delete(
            f"/content/{content_id}",
            headers={"Authorization": f"Bearer {temp_workspace_token}"},
        )
        assert response.status_code == status.HTTP_200_OK


class TestManageContent:
    """Tests for the content management API endpoints."""

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
        content_metadata: dict,
        access_token_admin_1: str,
        existing_tag_id_in_workspace_1: int,
    ) -> None:
        """Test creating and deleting content.

        Parameters
        ----------
        client
            The test client.
        content_title
            The title of the content.
        content_text
            The text of the content.
        access_token_admin_1
            The access token for admin user 1.
        existing_tag_id_in_workspace_1
            The ID of the existing tag in workspace 1.
        content_metadata
            The metadata of the content.
        """

        content_tags = [existing_tag_id_in_workspace_1]
        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": content_metadata,
                "content_tags": content_tags,
                "content_text": content_text,
                "content_title": content_title,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["content_metadata"] == content_metadata
        assert json_response["content_tags"] == content_tags
        assert "content_id" in json_response
        assert "workspace_id" in json_response

        response = client.delete(
            f"/content/{json_response['content_id']}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

        assert response.status_code == status.HTTP_200_OK

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
        access_token_admin_1: str,
        client: TestClient,
        existing_content_id_in_workspace_1: int,
        existing_tag_id_in_workspace_1: int,
        content_metadata: dict,
        content_text: str,
        content_title: str,
    ) -> None:
        """Test editing and retrieving content.

        Parameters
        ----------
        access_token_admin_1
            The access token for admin user 1.
        client
            The test client.
        existing_content_id_in_workspace_1
            The ID of the existing content in workspace 1.
        existing_tag_id_in_workspace_1
            The ID of the existing tag in workspace 1.
        content_metadata
            The metadata of the content.
        content_text
            The text of the content.
        content_title
            The title of the content.
        """

        content_tags = [existing_tag_id_in_workspace_1]
        response = client.put(
            f"/content/{existing_content_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": content_metadata,
                "content_tags": [existing_tag_id_in_workspace_1],
                "content_text": content_text,
                "content_title": content_title,
            },
        )

        assert response.status_code == status.HTTP_200_OK

        response = client.get(
            f"/content/{existing_content_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        json_response = response.json()
        assert response.status_code == status.HTTP_200_OK
        assert json_response["content_title"] == content_title
        assert json_response["content_text"] == content_text
        assert json_response["content_tags"] == content_tags
        edited_metadata = json_response["content_metadata"]
        assert all(edited_metadata[k] == v for k, v in content_metadata.items())

    def test_edit_content_not_found(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test editing a content that does not exist.

        Parameters
        ----------
        access_token_admin_1
            The access token for admin user 1.
        client
            The test client.
        """

        response = client.put(
            "/content/12345",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": {"key": "value"},
                "content_text": "sample text",
                "content_title": "title",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_content(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_content_id_in_workspace_1: int,
        existing_tag_id_in_workspace_1: int,
    ) -> None:
        """Test listing content.

        Parameters
        ----------
        access_token_admin_1
            The access token for admin user 1.
        client
            The test client.
        existing_content_id_in_workspace_1
            The ID of the existing content in workspace 1.
        existing_tag_id_in_workspace_1
            The ID of the existing tag in workspace 1.
        """

        response = client.get(
            "/content", headers={"Authorization": f"Bearer {access_token_admin_1}"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) > 0

    def test_delete_content(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_content_id_in_workspace_1: int,
    ) -> None:
        """Test deleting content.

        Parameters
        ----------
        access_token_admin_1
            The access token for admin user 1.
        client
            The test client.
        existing_content_id_in_workspace_1
            The ID of the existing content in workspace 1.
        """

        response = client.delete(
            f"/content/{existing_content_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_200_OK


class TestMultiUserManageContent:
    """Tests for managing content with multiple users."""

    def test_admin_2_get_admin_1_content(
        self,
        access_token_admin_2: str,
        client: TestClient,
        existing_content_id_in_workspace_1: str,
    ) -> None:
        """Test admin user 2 getting admin user 1's content.

        Parameters
        ----------
        access_token_admin_2
            The access token for admin user 2.
        client
            The test client.
        existing_content_id_in_workspace_1
            The ID of the existing content in workspace 1.
        """

        response = client.get(
            f"/content/{existing_content_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_2_edit_admin_1_content(
        self,
        access_token_admin_2: str,
        client: TestClient,
        existing_content_id_in_workspace_1: str,
    ) -> None:
        """Test admin user 2 editing admin user 1's content.

        Parameters
        ----------
        access_token_admin_2
            The access token for admin user 2.
        client
            The test client.
        existing_content_id_in_workspace_1
            The ID of the existing content in workspace 1.
        """

        response = client.put(
            f"/content/{existing_content_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
            json={
                "content_metadata": {},
                "content_text": "admin2 test content 3",
                "content_title": "admin2 title 3",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_2_delete_admin_1_content(
        self,
        access_token_admin_2: str,
        client: TestClient,
        existing_content_id_in_workspace_1: str,
    ) -> None:
        """Test admin user 2 deleting admin user 1's content.

        Parameters
        ----------
        access_token_admin_2
            The access token for admin user 2.
        client
            The test client.
        existing_content_id_in_workspace_1
            The ID of the existing content in workspace 1.
        """

        response = client.delete(
            f"/content/{existing_content_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_display_number_increases(
    client: TestClient,
    access_token_admin_1: str,
    existing_tag_id_in_workspace_1: int,
) -> None:
    """Test creating and deleting content.

    Parameters
    ----------
    client
        The test client.
    access_token_admin_1
        The access token for admin user 1.
    existing_tag_id_in_workspace_1
        The ID of the existing tag in workspace 1.
    content_metadata
        The metadata of the content.
    """

    content_tags = [existing_tag_id_in_workspace_1]
    response = client.post(
        "/content",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
        json={
            "content_metadata": {},
            "content_tags": content_tags,
            "content_text": "Content text 1",
            "content_title": "Content title 1",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    display_number = json_response["display_number"]

    response = client.post(
        "/content",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
        json={
            "content_metadata": {},
            "content_tags": content_tags,
            "content_text": "Content text 2",
            "content_title": "Content title 2",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    display_number_2 = json_response["display_number"]
    assert display_number_2 == display_number + 1


class TestRelatedContent:
    """Tests for related content."""

    def test_related_content_invalid(
        self,
        client: TestClient,
        access_token_admin_1: str,
    ) -> None:
        """Test the related content is invalid."""

        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": {},
                "content_text": "Content text 2",
                "content_title": "Content title 2",
                "related_contents_id": [10000000, 12230000, 43340000],
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_related_content_valid(
        self,
        client: TestClient,
        access_token_admin_1: str,
        existing_content_id_in_workspace_1: int,
    ) -> None:
        """Test the related content is valid."""

        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": {},
                "content_text": "Content text 2",
                "content_title": "Content title 2",
                "related_contents_id": [existing_content_id_in_workspace_1],
            },
        )
        assert response.status_code == status.HTTP_200_OK
        client.delete(
            f"/content/{response.json()['content_id']}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

    def test_related_content_wrong_workspace(
        self,
        client: TestClient,
        access_token_admin_2: str,
        existing_content_id_in_workspace_1: int,
    ) -> None:
        """Test the related content is valid."""

        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
            json={
                "content_metadata": {},
                "content_text": "Content text 2",
                "content_title": "Content title 2",
                "related_contents_id": [existing_content_id_in_workspace_1],
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_related_content_archived(
        self,
        client: TestClient,
        access_token_admin_1: str,
        existing_content_id_in_workspace_1: int,
    ) -> None:
        """Test that adding an archived content as a related content is not allowed."""

        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": {},
                "content_tags": [],
                "content_text": "Content text 1",
                "content_title": "Content title 1",
                "related_contents_id": [existing_content_id_in_workspace_1],
            },
        )
        assert response.status_code == status.HTTP_200_OK
        content_id = response.json()["content_id"]
        response = client.patch(
            f"/content/{content_id}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

        assert response.status_code == status.HTTP_200_OK

        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": {},
                "content_tags": [],
                "content_text": "Content text 2",
                "content_title": "Content title 2",
                "related_contents_id": [content_id],
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        client.delete(
            f"/content/{content_id}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

    def test_related_content_mixed_valid_and_invalid(
        self,
        client: TestClient,
        access_token_admin_1: str,
        existing_content_id_in_workspace_1: int,
    ) -> None:
        """Test that adding a mixed valid and invalid related content is not allowed."""

        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": {},
                "content_tags": [],
                "content_text": "Content text 1",
                "content_title": "Content title 1",
                "related_contents_id": [10000000, existing_content_id_in_workspace_1],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["related_contents_id"] == [
            existing_content_id_in_workspace_1
        ]

        client.delete(
            f"/content/{response.json()['content_id']}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

    def test_edit_invalid_related_content(
        self,
        client: TestClient,
        access_token_admin_1: str,
        existing_content_id_in_workspace_1: int,
    ) -> None:
        """Test that editing a related content is not allowed."""

        response = client.put(
            f"/content/{existing_content_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": {},
                "content_tags": [],
                "content_text": "Content text 1",
                "content_title": "Content title 1",
                "related_contents_id": [10000000],
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_edit_valid_related_content(
        self,
        client: TestClient,
        access_token_admin_1: str,
        existing_content_id_in_workspace_1: int,
        faq_contents_in_workspace_1: list[int],
    ) -> None:
        """Test that editing a valid related content is allowed."""

        response = client.put(
            f"/content/{existing_content_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": {},
                "content_tags": [],
                "content_text": "Content text 1",
                "content_title": "Content title 1",
                "related_contents_id": faq_contents_in_workspace_1,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["related_contents_id"] == faq_contents_in_workspace_1


async def test_convert_record_to_schema() -> None:
    """Test the conversion of a record to a schema."""

    content_id = 1
    workspace_id = 123
    record = ContentDB(
        content_embedding=await async_fake_embedding(),
        content_id=content_id,
        content_metadata={"extra_field": "extra value"},
        content_text="sample text",
        content_title="sample title for content",
        created_datetime_utc=datetime.now(timezone.utc),
        display_number=2,
        is_archived=False,
        positive_votes=0,
        negative_votes=0,
        updated_datetime_utc=datetime.now(timezone.utc),
        workspace_id=workspace_id,
    )
    result = _convert_record_to_schema(record=record)
    assert result.content_id == content_id
    assert result.workspace_id == workspace_id
    assert result.content_text == "sample text"
    assert result.content_metadata["extra_field"] == "extra value"
