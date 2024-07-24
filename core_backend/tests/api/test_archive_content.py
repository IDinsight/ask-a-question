"""This module tests the archive content API endpoint."""

from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestArchiveContent:
    @pytest.fixture(scope="function")
    def existing_content_id(
        self,
        client: TestClient,
        fullaccess_token: str,
    ) -> Generator[str, None, None]:
        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "Title in DB",
                "content_text": "Text in DB",
                "content_tags": [],
                "content_metadata": {},
            },
        )
        content_id = response.json()["content_id"]
        yield content_id
        client.delete(
            f"/content/{content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )

    def test_save_content_returns_content(
        self, client: TestClient, fullaccess_token: str
    ) -> None:
        """This test checks:

        1. Saving content to DB returns the saved content with the "is_archived" field
            set to `False`.
        2. Retrieving te saved content from the DB returns the content.
        """

        # 1.
        response = client.post(
            "/content",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": "Title in DB",
                "content_text": "Text in DB",
                "content_tags": [],
                "content_metadata": {},
            },
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["is_archived"] is False

        # 2.
        response = client.get(
            "/content", headers={"Authorization": f"Bearer {fullaccess_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert len(json_response) == 1
        assert json_response[0]["is_archived"] is False

    def test_archive_existing_content(
        self, client: TestClient, existing_content_id: int, fullaccess_token: str
    ) -> None:
        """This test checks:

        1. Existing content can be retrieved before archiving.
        2. The archive content API endpoint archives the existing content and returns
            `None`.
        3. The archived content can no longer be retrieved.
        4. The archived content can still be retrieved if the query parameter
            "exclude_archived" is set to "False". In addition, the "is_archived" field
            is still set to `True`.
        """

        # 1.
        response = client.get(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["is_archived"] is False

        # 2.
        response = client.patch(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response is None

        # 3.
        response = client.get(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 4.
        response = client.get(
            f"/content/{existing_content_id}?exclude_archived=False",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
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
        client: TestClient,
        existing_content_id: int,
        fullaccess_token: str,
        content_title: str,
        content_text: str,
        content_metadata: dict[str, str],
    ) -> None:
        """This test checks:

        1. Archived content cannot be edited.
        2. Archived content can still be edited if the query parameter
            "exclude_archived" is set to "False".
        """

        # 1.
        response = client.patch(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response is None

        response = client.put(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": content_title,
                "content_text": content_text,
                "content_metadata": content_metadata,
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 2.
        response = client.put(
            f"/content/{existing_content_id}?exclude_archived=False",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            json={
                "content_title": content_title,
                "content_text": content_text,
                "content_metadata": content_metadata,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert json_response["content_title"] == content_title
        assert json_response["content_text"] == content_text
        assert json_response["content_metadata"] == content_metadata
