"""Tests for the content management API endpoints in `app.contents.router`.

Covers content CRUD, quotas, related contents, archiving, validation, CSV import,
authentication/authorization failures and request validation. Business-logic edge
cases that are expensive to reach over HTTP live in `test_contents_service.py`.
"""

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Generator
from unittest.mock import AsyncMock

import pandas as pd
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.contents.models import ContentDB
from app.core.exceptions import (
    AppError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
)
from app.workspaces.repository import get_workspace_by_workspace_name
from tests.conftest import async_fake_embedding

# Dedicated workspace for the unvalidated-queue tests.
_VALIDATION_WORKSPACE = "temp_workspace_contents_validation"

# Minimal valid request body for creating/editing content.
VALID_CONTENT_BODY = {
    "content_metadata": {},
    "content_tags": [],
    "content_text": "auth check text",
    "content_title": "auth check title",
}


def _dict_to_csv_bytes(*, data: dict) -> BytesIO:
    """Convert a dictionary to a CSV file in bytes.

    Parameters
    ----------
    data
        The dictionary to convert to a CSV file in bytes.

    Returns
    -------
    BytesIO
        The CSV file in bytes.
    """

    df = pd.DataFrame(data)
    csv_bytes = BytesIO()
    df.to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)

    return csv_bytes


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


class TestArchiveContent:
    """Tests for the archive content API endpoints."""

    @pytest.fixture(scope="function")
    def existing_content(
        self, access_token_admin_4: pytest.FixtureRequest, client: TestClient
    ) -> Generator[tuple[int, str, int], None, None]:
        """Create a content in the database and yield the content ID, content text,
        and user ID. The content will be deleted after the test is run.

        Parameters
        ----------
        access_token_admin_4
            Access token for admin user 4.
        client
            The test client.

        Yields
        ------
        tuple[int, str, int]
            The content ID, content text, and workspace ID.
        """

        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
            json={
                "content_metadata": {},
                "content_tags": [],
                "content_text": "Text in DB",
                "content_title": "Title in DB",
            },
        )
        json_response = response.json()
        content_id = json_response["content_id"]
        content_text = json_response["content_text"]
        workspace_id = json_response["workspace_id"]
        yield content_id, content_text, workspace_id
        client.delete(
            f"/content/{content_id}?exclude_archived=False",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
        )

    def test_save_content_returns_content(
        self, access_token_admin_4: str, client: TestClient
    ) -> None:
        """This test checks:

        1. Saving content to DB returns the saved content with the "is_archived" field
            set to `False`.
        2. Retrieving te saved content from the DB returns the content.

        Parameters
        ----------
        access_token_admin_4
            Access token for admin user 4.
        client
            The test client.
        """

        # 1.
        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
            json={
                "content_metadata": {},
                "content_tags": [],
                "content_text": "Text in DB",
                "content_title": "Title in DB",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["is_archived"] is False

        # 2.
        response = client.get(
            "/content", headers={"Authorization": f"Bearer {access_token_admin_4}"}
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert len(json_response) == 1
        assert json_response[0]["is_archived"] is False

        client.delete(
            f"/content/{json_response[0]['content_id']}",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
        )

    def test_archive_existing_content(
        self,
        access_token_admin_4: str,
        client: TestClient,
        existing_content: tuple[int, str, int],
    ) -> None:
        """This test checks:

        1. Existing content can be retrieved before archiving.
        2. The archive content API endpoint archives the existing content and returns
            `None`.
        3. The archived content can no longer be retrieved.
        4. The archived content can still be retrieved if the query parameter
            "exclude_archived" is set to "False". In addition, the "is_archived" field
            is still set to `True`.

        Parameters
        ----------
        access_token_admin_4
            Access token for admin user 4.
        client
            The test client.
        existing_content
            The existing content ID, content text, and workspace ID.
        """

        existing_content_id = existing_content[0]

        # 1.
        response = client.get(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["is_archived"] is False

        # 2.
        response = client.patch(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response is None

        # 3.
        response = client.get(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 4.
        response = client.get(
            f"/content/{existing_content_id}?exclude_archived=False",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["is_archived"] is True

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
    def test_unable_to_update_archived_content(
        self,
        access_token_admin_4: str,
        client: TestClient,
        existing_content: tuple[int, str, int],
        content_title: str,
        content_text: str,
        content_metadata: dict[str, str],
    ) -> None:
        """This test checks:

        1. Archived content cannot be edited.
        2. Archived content can still be edited if the query parameter
            "exclude_archived" is set to "False".

        Parameters
        ----------
        access_token_admin_4
            Access token for admin user 4.
        client
            The test client.
        existing_content
            The existing content ID, content text, and workspace ID.
        content_title
            The new content title.
        content_text
            The new content text.
        content_metadata
            The new content metadata.
        """

        existing_content_id = existing_content[0]

        # 1.
        response = client.patch(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response is None

        response = client.put(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
            json={
                "content_metadata": content_metadata,
                "content_text": content_text,
                "content_title": content_title,
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 2.
        response = client.put(
            f"/content/{existing_content_id}?exclude_archived=False",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
            json={
                "content_metadata": content_metadata,
                "content_text": content_text,
                "content_title": content_title,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["content_title"] == content_title
        assert json_response["content_text"] == content_text
        assert json_response["content_metadata"] == content_metadata

    def test_bulk_csv_import_of_archived_content(
        self, access_token_admin_4: str, client: TestClient
    ) -> None:
        """The scenario is as follows:

        A. A user has already uploaded a CSV file with contents. Uploading the CSV file
            with a duplicated title and/or text should fail.
        B. The user then archives one or more existing contents.

        Then, this test checks:

        1. The user then uploads another CSV file. This one contains a content that was
            previously archived and a new content. The previously archived content will
            pass duplication checks because it is archived. Because it is archived, it
            will NOT be retrieved from the content database by default.
        2. After the user uploads the new CSV file, the previously archived content
            will not be retrieved by default. However, it is still accessible via the
            query parameter "exclude_archived".

        Parameters
        ----------
        access_token_admin_4
            Access token for admin user 4.
        client
            The test client.
        """

        # A.
        data = _dict_to_csv_bytes(
            data={
                "tag": ["test-tag", "new-tag"],
                "text": ["csv text 1", "csv text 2"],
                "title": ["csv title 1", "csv title 2"],
            }
        )
        response = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
            files={"file": ("test.csv", data, "text/csv")},
        )
        assert response.status_code == status.HTTP_200_OK
        content_id = [x["content_id"] for x in response.json()["contents"]][0]

        data = _dict_to_csv_bytes(
            data={
                "tag": ["test-tag", "some-new-tag"],
                "text": ["csv text 1", "some new text"],
                "title": ["csv title 1", "some new title"],
            }
        )
        response = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
            files={"file": ("test.csv", data, "text/csv")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # B.
        response = client.patch(
            f"/content/{content_id}",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
        )
        assert response.status_code == status.HTTP_200_OK

        # 1.
        data = _dict_to_csv_bytes(
            data={
                "tag": ["test-tag", "some-new-tag"],
                "text": ["csv text 1", "some new text"],
                "title": ["csv title 1", "some new title"],
            }
        )
        response = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
            files={"file": ("test.csv", data, "text/csv")},
        )
        assert response.status_code == status.HTTP_200_OK

        # 2.
        response = client.get(
            "/content/?exclude_archived=False",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
        )
        assert response.status_code == status.HTTP_200_OK

        for dict_ in response.json():
            client.delete(
                f"/content/{dict_['content_id']}?exclude_archived=False",
                headers={"Authorization": f"Bearer {access_token_admin_4}"},
            )


class TestImportContentQuota:
    """Tests for the import content quota API endpoint."""

    @pytest.mark.parametrize(
        "temp_workspace_token_and_quota",
        [
            {
                "content_quota": 10,
                "username": "temp_username_limit_10",
                "workspace_name": "temp_workspace_limit_10",
            },
            {
                "content_quota": None,
                "username": "temp_username_limit_unlimited",
                "workspace_name": "temp_workspace_limit_unlimited",
            },
        ],
        indirect=True,
    )
    async def test_import_content_success(
        self, client: TestClient, temp_workspace_token_and_quota: tuple[str, int]
    ) -> None:
        """Test importing content with a valid CSV file.

        Parameters
        ----------
        client
            The test client.
        temp_workspace_token_and_quota
            The temporary workspace access token and content quota.
        """

        temp_workspace_token, _ = temp_workspace_token_and_quota
        data = _dict_to_csv_bytes(
            data={
                "text": ["csv text 1", "csv text 2"],
                "title": ["csv title 1", "csv title 2"],
            }
        )

        response = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {temp_workspace_token}"},
            files={"file": ("test.csv", data, "text/csv")},
        )
        assert response.status_code == status.HTTP_200_OK

        json_response = response.json()
        contents_list = json_response["contents"]
        for content in contents_list:
            content_id = content["content_id"]
            response = client.delete(
                f"/content/{content_id}",
                headers={"Authorization": f"Bearer {temp_workspace_token}"},
            )
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize(
        "temp_workspace_token_and_quota",
        [
            {
                "content_quota": 0,
                "username": "temp_user_limit_10",
                "workspace_name": "temp_workspace_limit_10",
            },
        ],
        indirect=True,
    )
    async def test_import_content_failure(
        self, client: TestClient, temp_workspace_token_and_quota: tuple[str, int]
    ) -> None:
        """Test importing content with a CSV file that exceeds the content quota.

        Parameters
        ----------
        client
            The test client.
        temp_workspace_token_and_quota
            The temporary workspace access token and content quota.
        """

        temp_workspace_token, _ = temp_workspace_token_and_quota
        data = _dict_to_csv_bytes(
            data={
                "text": ["csv text 1", "csv text 2"],
                "title": ["csv title 1", "csv title 2"],
            }
        )
        response = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {temp_workspace_token}"},
            files={"file": ("test.csv", data, "text/csv")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"]["errors"][0]["type"] == "exceeds_quota"


class TestImportContent:
    """Tests for the import content API endpoint."""

    @pytest.fixture
    def data_duplicate_texts(self) -> BytesIO:
        """Create a CSV file with duplicate text in bytes.

        Returns
        -------
        BytesIO
            The CSV file with duplicate text in bytes.
        """

        data = {
            "text": ["Duplicate text", "Duplicate text"],
            "title": ["Title 1", "Title 2"],
        }
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_duplicate_titles(self) -> BytesIO:
        """Create a CSV file with duplicate titles in bytes.

        Returns
        -------
        BytesIO
            The CSV file with duplicate titles in bytes.
        """

        data = {
            "text": ["Text 1", "Text 2"],
            "title": ["Duplicate title", "Duplicate title"],
        }
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_empty_csv(self) -> BytesIO:
        """Create an empty CSV file in bytes.

        Returns
        -------
        BytesIO
            The empty CSV file in bytes.
        """

        data: dict = {}
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_long_text(self) -> BytesIO:
        """Create a CSV file with text that is too long in bytes.

        Returns
        -------
        BytesIO
            The CSV file with text that is too long in bytes.
        """

        data = {"text": ["a" * 2001], "title": ["Valid title"]}
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_long_title(self) -> BytesIO:
        """Create a CSV file with a title that is too long in bytes.

        Returns
        -------
        BytesIO
            The CSV file with a title that is too long in bytes.
        """

        data = {"text": ["Valid text"], "title": ["a" * 151]}
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_missing_columns(self) -> BytesIO:
        """Create a CSV file with missing columns in bytes.

        Returns
        -------
        BytesIO
            The CSV file with missing columns in bytes.
        """

        data = {
            "wrong_column_1": ["Value 1", "Value 2"],
            "wrong_column_2": ["Value 3", "Value 4"],
        }
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_no_rows(self) -> BytesIO:
        """Create a CSV file with no rows in bytes.

        Returns
        -------
        BytesIO
            The CSV file with no rows in bytes.
        """

        data: dict = {"text": [], "title": []}
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_text_missing(self) -> BytesIO:
        """Create a CSV file with missing text in bytes.

        Returns
        -------
        BytesIO
            The CSV file with missing text in bytes.
        """

        data = {"text": ["", "csv text 2"], "title": ["csv title 1", "csv title 2"]}
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_title_missing(self) -> BytesIO:
        """Create a CSV file with missing titles in bytes.

        Returns
        -------
        BytesIO
            The CSV file with missing titles in bytes.
        """

        data = {"text": ["csv title 2", "csv text 2"], "title": ["", "csv text 1"]}
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_text_spaces_only(self) -> BytesIO:
        """Create a CSV file with text that contains only spaces in bytes.

        Returns
        -------
        BytesIO
            The CSV file with text that contains only spaces in bytes.
        """

        data: dict = {"text": ["  "], "title": ["csv title 1"]}
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_title_spaces_only(self) -> BytesIO:
        """Create a CSV file with titles that contain only spaces in bytes.

        Returns
        -------
        BytesIO
            The CSV file with titles that contain only spaces in bytes.
        """

        data: dict = {"text": ["csv text 1"], "title": ["  "]}
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_valid(self) -> BytesIO:
        """Create a valid CSV file in bytes.

        Returns
        -------
        BytesIO
            The valid CSV file in bytes.
        """

        data = {
            "text": ["csv text 1", "csv text 2"],
            "title": ["csv title 1", "csv title 2"],
        }
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_valid_with_tags(self) -> BytesIO:
        """Create a valid CSV file with tags in bytes.

        Returns
        -------
        BytesIO
            The valid CSV file with tags in bytes.
        """

        data = {
            "tags": ["tag1, tag2", "tag1, tag4"],
            "text": ["csv text 1", "csv text 2"],
            "title": ["csv title 1", "csv title 2"],
        }
        return _dict_to_csv_bytes(data=data)

    @pytest.mark.parametrize("mock_csv_data", ["data_valid", "data_valid_with_tags"])
    async def test_csv_import_success(
        self,
        client: TestClient,
        access_token_admin_1: str,
        mock_csv_data: BytesIO,
        request: pytest.FixtureRequest,
    ) -> None:
        """Test importing content with a valid CSV file.

        Parameters
        ----------
        client
            The test client.
        access_token_admin_1
            The access token for the admin user 1.
        mock_csv_data
            The mock CSV data.
        request
            The pytest request object.
        """

        mock_csv_file = request.getfixturevalue(mock_csv_data)  # type: ignore

        response = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            files={"file": ("test.csv", mock_csv_file, "text/csv")},
        )
        assert response.status_code == status.HTTP_200_OK

        # Cleanup contents and tags.
        json_response = response.json()
        contents_list = json_response["contents"]
        for content in contents_list:
            content_id = content["content_id"]
            response = client.delete(
                f"/content/{content_id}",
                headers={"Authorization": f"Bearer {access_token_admin_1}"},
            )
            assert response.status_code == status.HTTP_200_OK

        tags_list = json_response["tags"]
        for tag in tags_list:
            tag_id = tag["tag_id"]
            response = client.delete(
                f"/tag/{tag_id}",
                headers={"Authorization": f"Bearer {access_token_admin_1}"},
            )
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize(
        "mock_csv_data, expected_error_type",
        [
            ("data_empty_csv", "empty_data"),
            ("data_no_rows", "no_rows_csv"),
            ("data_title_spaces_only", "empty_title"),
            ("data_text_spaces_only", "empty_text"),
            ("data_missing_columns", "missing_columns"),
            ("data_title_missing", "empty_title"),
            ("data_text_missing", "empty_text"),
            ("data_long_title", "title_too_long"),
            ("data_long_text", "texts_too_long"),
            ("data_duplicate_titles", "duplicate_titles"),
            ("data_duplicate_texts", "duplicate_texts"),
        ],
    )
    async def test_csv_import_checks(
        self,
        access_token_admin_1: str,
        client: TestClient,
        mock_csv_data: BytesIO,
        expected_error_type: str,
        request: pytest.FixtureRequest,
    ) -> None:
        """Test importing content with a CSV file that fails the checks.

        Parameters
        ----------
        access_token_admin_1
            The access token for the admin user 1.
        client
            The test client.
        mock_csv_data
            The mock CSV data.
        expected_error_type
            The expected error type.
        request
            The pytest request object.
        """

        # Fetch data from the fixture.
        mock_csv_file = request.getfixturevalue(mock_csv_data)  # type: ignore

        response = client.post(
            "/content/csv-upload",
            files={"file": ("test.csv", mock_csv_file, "text/csv")},
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"]["errors"][0]["type"] == expected_error_type


class TestDBDuplicates:
    """Tests for importing content with duplicates in the database."""

    @pytest.fixture
    def data_text_in_db(self) -> BytesIO:
        """Create a CSV file with text that already exists in the database in bytes.

        Returns
        -------
        BytesIO
            The CSV file with text that already exists in the database in bytes.
        """

        # Assuming "Text in DB" is a text that exists in the database.
        data = {"text": ["Text in DB"], "title": ["New title"]}
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture
    def data_title_in_db(self) -> BytesIO:
        """Create a CSV file with a title that already exists in the database in bytes.

        Returns
        -------
        BytesIO
            The CSV file with a title that already exists in the database in bytes.
        """

        # Assuming "Title in DB" is a title that exists in the database.
        data = {"text": ["New text"], "title": ["Title in DB"]}
        return _dict_to_csv_bytes(data=data)

    @pytest.fixture(scope="function")
    def existing_content_in_db(
        self, access_token_admin_1: str, client: TestClient
    ) -> Generator[str, None, None]:
        """Create a content in the database and yield the content ID.

        Parameters
        ----------
        access_token_admin_1
            The access token for admin user 1.
        client
            The test client.

        Yields
        ------
        Generator[str, None, None]
            The content ID.
        """

        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={
                "content_metadata": {},
                "content_tags": [],
                "content_text": "Text in DB",
                "content_title": "Title in DB",
            },
        )
        content_id = response.json()["content_id"]

        yield content_id

        client.delete(
            f"/content/{content_id}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

    @pytest.mark.parametrize(
        "mock_csv_data, expected_error_type",
        [("data_title_in_db", "title_in_db"), ("data_text_in_db", "text_in_db")],
    )
    async def test_csv_import_db_duplicates(
        self,
        access_token_admin_1: str,
        client: TestClient,
        mock_csv_data: BytesIO,
        expected_error_type: str,
        request: pytest.FixtureRequest,
        existing_content_in_db: str,
    ) -> None:
        """This test uses the `existing_content_in_db` fixture to create a content in
        the database and then tries to import a CSV file with a title or text that
        already exists in the database.

        Parameters
        ----------
        access_token_admin_1
            The access token for admin user 1.
        client
            The test client.
        mock_csv_data
            The mock CSV data.
        expected_error_type
            The expected error type.
        request
            The pytest request object.
        existing_content_in_db
            The existing content in the database.
        """

        mock_csv_file = request.getfixturevalue(mock_csv_data)  # type: ignore
        response_text_dupe = client.post(
            "/content/csv-upload",
            files={"file": ("test.csv", mock_csv_file, "text/csv")},
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response_text_dupe.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            response_text_dupe.json()["detail"]["errors"][0]["type"]
            == expected_error_type
        )


# Every content endpoint with a request that would otherwise be valid. Used to check
# that authentication is enforced uniformly.
_CSV_FILE = {"file": ("test.csv", b"title,text\nsome title,some text\n", "text/csv")}
ALL_ENDPOINTS: list[tuple[str, str, dict[str, Any]]] = [
    ("post", "/content/", {"json": VALID_CONTENT_BODY}),
    ("put", "/content/1", {"json": VALID_CONTENT_BODY}),
    ("get", "/content/", {}),
    ("get", "/content/next-unvalidated", {}),
    ("patch", "/content/validate/1", {}),
    ("get", "/content/unvalidated-count", {}),
    ("patch", "/content/1", {}),
    ("delete", "/content/1", {}),
    ("get", "/content/1", {}),
    ("post", "/content/csv-upload", {"files": _CSV_FILE}),
]

# Read endpoints only need a valid token; every other endpoint requires the admin role.
_READ_ENDPOINTS = {("get", "/content/"), ("get", "/content/1")}
ADMIN_ONLY_ENDPOINTS = [e for e in ALL_ENDPOINTS if e[:2] not in _READ_ENDPOINTS]


class TestAuthAndValidation:
    """Authentication, authorization and request-validation failures."""

    @pytest.mark.parametrize(
        "headers",
        [{}, {"Authorization": "Bearer not-a-valid-jwt"}],
        ids=["no_token", "invalid_token"],
    )
    @pytest.mark.parametrize("method, path, kwargs", ALL_ENDPOINTS)
    def test_unauthenticated_request_returns_401(
        self,
        client: TestClient,
        headers: dict[str, str],
        kwargs: dict[str, Any],
        method: str,
        path: str,
    ) -> None:
        """Requests without a valid access token are rejected.

        Parameters
        ----------
        client
            The test client.
        headers
            The request headers (missing or invalid token).
        kwargs
            Extra arguments for the request (body or files).
        method
            The HTTP method.
        path
            The endpoint path.
        """

        response = client.request(method, path, headers=headers, **kwargs)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("method, path, kwargs", ADMIN_ONLY_ENDPOINTS)
    def test_read_only_user_is_forbidden(
        self,
        access_token_read_only_1: str,
        client: TestClient,
        kwargs: dict[str, Any],
        method: str,
        path: str,
    ) -> None:
        """Read-only users cannot call admin-only content endpoints.

        The role check runs before any lookup, so the content ID does not need to
        exist.

        Parameters
        ----------
        access_token_read_only_1
            Access token for read-only user 1 (workspace 1).
        client
            The test client.
        kwargs
            Extra arguments for the request (body or files).
        method
            The HTTP method.
        path
            The endpoint path.
        """

        response = client.request(
            method,
            path,
            headers={"Authorization": f"Bearer {access_token_read_only_1}"},
            **kwargs,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("path", ["/content/", "/content/next-unvalidated"])
    def test_read_only_user_can_read(
        self, access_token_read_only_1: str, client: TestClient, path: str
    ) -> None:
        """Listing content is allowed for read-only users, but the unvalidated queue
        is not.

        Parameters
        ----------
        access_token_read_only_1
            Access token for read-only user 1 (workspace 1).
        client
            The test client.
        path
            The endpoint path.
        """

        response = client.get(
            path, headers={"Authorization": f"Bearer {access_token_read_only_1}"}
        )
        expected = (
            status.HTTP_200_OK if path == "/content/" else status.HTTP_403_FORBIDDEN
        )
        assert response.status_code == expected

    @pytest.mark.parametrize(
        "method, path, kwargs",
        [
            ("post", "/content/", {"json": {"content_title": "no text"}}),
            ("post", "/content/", {"json": {**VALID_CONTENT_BODY, "content_tags": 1}}),
            ("put", "/content/not-an-int", {"json": VALID_CONTENT_BODY}),
            ("put", "/content/1", {"json": {"content_text": "no title"}}),
            ("get", "/content/?skip=abc", {}),
            ("get", "/content/not-an-int", {}),
            ("delete", "/content/not-an-int", {}),
            ("patch", "/content/validate/not-an-int", {}),
            ("post", "/content/csv-upload", {}),
        ],
        ids=[
            "create_missing_text",
            "create_bad_tags",
            "edit_bad_id",
            "edit_missing_title",
            "list_bad_skip",
            "get_bad_id",
            "delete_bad_id",
            "validate_bad_id",
            "upload_missing_file",
        ],
    )
    def test_invalid_request_returns_422(
        self,
        access_token_admin_1: str,
        client: TestClient,
        kwargs: dict[str, Any],
        method: str,
        path: str,
    ) -> None:
        """Malformed requests are rejected by FastAPI before reaching the service.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            The test client.
        kwargs
            Extra arguments for the request (body or files).
        method
            The HTTP method.
        path
            The endpoint path.
        """

        response = client.request(
            method,
            path,
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            **kwargs,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "detail" in response.json()


class TestRouterWiring:
    """Check how the router hands requests to, and errors from, the service layer.

    The service functions are replaced with mocks so these tests do not touch the
    database beyond authenticating the caller.
    """

    def test_retrieve_content_forwards_query_params(
        self,
        access_token_admin_1: str,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Query parameters for listing content are passed through to the service.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            The test client.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        fake = AsyncMock(return_value=[])
        monkeypatch.setattr("app.contents.router.service.retrieve_content", fake)

        response = client.get(
            "/content/?skip=2&limit=3&exclude_archived=false&exclude_unvalidated=false",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
        assert fake.await_args is not None
        kwargs = fake.await_args.kwargs
        assert kwargs["skip"] == 2
        assert kwargs["limit"] == 3
        assert kwargs["exclude_archived"] is False
        assert kwargs["exclude_unvalidated"] is False
        assert kwargs["workspace_name"] == "test_workspace_1"

    @pytest.mark.parametrize(
        "error, expected_status",
        [
            (BadRequestError("bad"), status.HTTP_400_BAD_REQUEST),
            (NotFoundError("missing"), status.HTTP_404_NOT_FOUND),
            (InternalServerError("boom"), status.HTTP_500_INTERNAL_SERVER_ERROR),
            (AppError("upstream", status_code=502), status.HTTP_502_BAD_GATEWAY),
        ],
        ids=["bad_request", "not_found", "internal", "bad_gateway"],
    )
    def test_service_errors_map_to_http_errors(
        self,
        access_token_admin_1: str,
        client: TestClient,
        error: AppError,
        expected_status: int,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Domain errors raised by the service become JSON error responses.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            The test client.
        error
            The domain error raised by the (mocked) service.
        expected_status
            The expected HTTP status code.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        monkeypatch.setattr(
            "app.contents.router.service.delete_content",
            AsyncMock(side_effect=error),
        )

        response = client.delete(
            "/content/1", headers={"Authorization": f"Bearer {access_token_admin_1}"}
        )

        assert response.status_code == expected_status
        assert response.json() == {"detail": error.detail}


@pytest.mark.parametrize(
    "method, path, kwargs",
    [
        ("get", "/content/99999999", {}),
        ("put", "/content/99999999", {"json": VALID_CONTENT_BODY}),
        ("patch", "/content/99999999", {}),
        ("patch", "/content/validate/99999999", {}),
        ("delete", "/content/99999999", {}),
    ],
    ids=["get", "edit", "archive", "validate", "delete"],
)
def test_missing_content_returns_404(
    access_token_admin_1: str,
    client: TestClient,
    kwargs: dict[str, Any],
    method: str,
    path: str,
) -> None:
    """Operations on a content ID that does not exist return 404.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1.
    client
        The test client.
    kwargs
        Extra arguments for the request (body).
    method
        The HTTP method.
    path
        The endpoint path.
    """

    response = client.request(
        method,
        path,
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
        **kwargs,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "temp_workspace_token_and_quota",
    [
        {
            "content_quota": None,
            "username": "temp_user_contents_validation",
            "workspace_name": _VALIDATION_WORKSPACE,
        }
    ],
    indirect=True,
)
class TestValidateContent:
    """Tests for the unvalidated-content queue endpoints.

    A dedicated workspace is used so the unvalidated count is deterministic.
    """

    async def test_validation_workflow(
        self,
        asession: AsyncSession,
        client: TestClient,
        temp_workspace_token_and_quota: tuple[str, int],
    ) -> None:
        """Walk through the review queue: count, fetch next, validate.

        Unvalidated rows are inserted directly because creating them through
        `POST /content` currently fails (see `test_create_unvalidated_content`).

        Parameters
        ----------
        asession
            Async session used to seed unvalidated content.
        client
            The test client.
        temp_workspace_token_and_quota
            The temporary workspace access token and content quota.
        """

        token, _ = temp_workspace_token_and_quota
        headers = {"Authorization": f"Bearer {token}"}

        # 1. A fresh workspace has nothing to validate.
        response = client.get("/content/unvalidated-count", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == 0
        response = client.get("/content/next-unvalidated", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 2. Seed two unvalidated cards.
        workspace_db = await get_workspace_by_workspace_name(
            asession=asession, workspace_name=_VALIDATION_WORKSPACE
        )
        now = datetime.now(timezone.utc)
        rows = [
            ContentDB(
                content_embedding=await async_fake_embedding(),
                content_metadata={},
                content_text=f"unvalidated text {i}",
                content_title=f"unvalidated title {i}",
                created_datetime_utc=now,
                display_number=i + 1,
                is_validated=False,
                updated_datetime_utc=now,
                workspace_id=workspace_db.workspace_id,
            )
            for i in range(2)
        ]
        asession.add_all(rows)
        await asession.commit()
        content_ids = [row.content_id for row in rows]

        assert client.get("/content/unvalidated-count", headers=headers).json() == 2
        # Unvalidated cards are hidden from the default listing.
        assert client.get("/content/", headers=headers).json() == []

        # 3. The queue returns the card with the lowest display number first.
        response = client.get("/content/next-unvalidated", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["content_id"] == content_ids[0]

        # 4. Validating it moves the queue on and makes it visible in listings.
        response = client.patch(f"/content/validate/{content_ids[0]}", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert client.get("/content/unvalidated-count", headers=headers).json() == 1
        response = client.get("/content/next-unvalidated", headers=headers)
        assert response.json()["content_id"] == content_ids[1]
        listed = client.get("/content/", headers=headers).json()
        assert [c["content_id"] for c in listed] == [content_ids[0]]

        for content_id in content_ids:
            response = client.delete(f"/content/{content_id}", headers=headers)
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "App bug: save_content_to_db re-reads the new row with "
            "exclude_unvalidated=True, misses it and returns an instance whose "
            "content_tags are not loaded -> MissingGreenlet (500). The response "
            "schema also never copies is_validated."
        ),
    )
    def test_create_unvalidated_content(
        self, client: TestClient, temp_workspace_token_and_quota: tuple[str, int]
    ) -> None:
        """Creating content with `is_validated=False` should succeed and say so.

        Parameters
        ----------
        client
            The test client.
        temp_workspace_token_and_quota
            The temporary workspace access token and content quota.
        """

        token, _ = temp_workspace_token_and_quota
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = client.post(
                "/content/",
                headers=headers,
                json={**VALID_CONTENT_BODY, "is_validated": False},
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["is_validated"] is False
        finally:
            # The failing request commits the row before crashing; remove it so the
            # queue test in this class still starts from an empty workspace.
            listed = client.get(
                "/content/?exclude_unvalidated=false", headers=headers
            ).json()
            for content in listed:
                client.delete(f"/content/{content['content_id']}", headers=headers)


@pytest.mark.parametrize("filename", ["test.txt", "test.csv.bak"])
def test_csv_upload_rejects_non_csv_file(
    access_token_admin_1: str, client: TestClient, filename: str
) -> None:
    """Uploading a file without a `.csv` extension fails with `invalid_format`.

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1.
    client
        The test client.
    filename
        The name of the uploaded file.
    """

    response = client.post(
        "/content/csv-upload",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
        files={"file": (filename, b"title,text\na,b\n", "text/plain")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"]["errors"][0]["type"] == "invalid_format"
