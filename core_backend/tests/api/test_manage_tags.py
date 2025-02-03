"""This module contains tests for tag endpoints."""

from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from core_backend.app.tags.models import TagDB
from core_backend.app.tags.routers import _convert_record_to_schema


@pytest.fixture(scope="function", params=["Tag1", ("tag3",)])
def existing_tag_id_in_workspace_1(
    access_token_admin_1: str, client: TestClient, request: pytest.FixtureRequest
) -> Generator[str, None, None]:
    """Create a tag ID in workspace 1 and return the tag ID

    Parameters
    ----------
    access_token_admin_1
        Access token for admin user 1.
    client
        Test client.
    request
        Pytest request object.

    Yields
    ------
    Generator[str, None, None]
        Tag ID.
    """

    response = client.post(
        "/tag",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
        json={"tag_name": request.param[0]},
    )
    tag_id = response.json()["tag_id"]

    yield tag_id

    client.delete(
        f"/tag/{tag_id}",
        headers={"Authorization": f"Bearer {access_token_admin_1}"},
    )


class TestManageTags:
    """Tests for tag endpoints."""

    @pytest.mark.parametrize("tag_name", ["tag_first", "tag_second"])
    async def test_create_and_delete_tag(
        self, access_token_admin_1: str, client: TestClient, tag_name: str
    ) -> None:
        """Test creating and deleting a tag.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        tag_name
            Tag name.
        """

        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": tag_name},
        )
        assert response.status_code == status.HTTP_200_OK
        json_response = response.json()
        assert "tag_id" in json_response
        assert "workspace_id" in json_response

        response = client.delete(
            f"/tag/{json_response['tag_id']}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("tag_name", ["TAG_FIRST", "TAG_SECOND"])
    def test_edit_and_retrieve_tag(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_tag_id_in_workspace_1: int,
        tag_name: str,
    ) -> None:
        """Test editing and retrieving a tag.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        existing_tag_id_in_workspace_1
            Existing tag ID in workspace 1.
        tag_name
            Tag name.
        """

        response = client.put(
            f"/tag/{existing_tag_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": tag_name},
        )

        assert response.status_code == status.HTTP_200_OK

        response = client.get(
            f"/tag/{existing_tag_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["tag_name"] == tag_name

    def test_edit_tag_not_found(
        self, access_token_admin_1: str, client: TestClient
    ) -> None:
        """Test editing a tag that does not exist.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        """

        response = client.put(
            "/tag/12345",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": "tag"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_tag(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_tag_id_in_workspace_1: int,
    ) -> None:
        """Test listing tags.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        existing_tag_id_in_workspace_1
            Existing tag ID in workspace 1.
        """

        response = client.get(
            "/tag", headers={"Authorization": f"Bearer {access_token_admin_1}"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) > 0

    @pytest.mark.parametrize(
        "tag_name_1,tag_name_2", [("TAG1", "TAG1"), ("Tag2", "TAG2")]
    )
    def test_add_tag_same_name_fails(
        self,
        access_token_admin_1: str,
        client: TestClient,
        tag_name_1: str,
        tag_name_2: str,
    ) -> None:
        """TEst adding a tag with the same name.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        tag_name_1
            Tag name 1.
        tag_name_2
            Tag name 2.
        """

        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": tag_name_1},
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": tag_name_2},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_tag(
        self,
        access_token_admin_1: str,
        client: TestClient,
        existing_tag_id_in_workspace_1: int,
    ) -> None:
        """Test deleting a tag.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        client
            Test client.
        existing_tag_id_in_workspace_1
            Existing tag ID in workspace 1.
        """

        response = client.delete(
            f"/tag/{existing_tag_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_admin_2_get_admin_1_tag_fails(
        self,
        access_token_admin_2: str,
        client: TestClient,
        existing_tag_id_in_workspace_1: int,
    ) -> None:
        """Test admin 2 getting admin 1's tag fails.

        Parameters
        ----------
        access_token_admin_2
            Access token for admin user 2.
        client
            Test client.
        existing_tag_id_in_workspace_1
            Existing tag ID in workspace 1.
        """

        response = client.get(
            f"/tag/{existing_tag_id_in_workspace_1}",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_tag_admin_1_edit_admin_2_fails(
        self, access_token_admin_1: str, access_token_admin_2: str, client: TestClient
    ) -> None:
        """Test admin 1 adding a tag and admin 2 editing it fails.

        Parameters
        ----------
        access_token_admin_1
            Access token for admin user 1.
        access_token_admin_2
            Access token for admin user 2.
        client
            Test client.
        """

        response = client.post(
            "/tag",
            headers={"Authorization": f"Bearer {access_token_admin_1}"},
            json={"tag_name": "tag"},
        )
        assert response.status_code == status.HTTP_200_OK

        tag_id = response.json()["tag_id"]
        response = client.put(
            f"/tag/{tag_id}",
            headers={"Authorization": f"Bearer {access_token_admin_2}"},
            json={"tag_name": "tag"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_convert_record_to_schema() -> None:
    """Test converting a record to a schema."""

    tag_id = 1
    workspace_id = 123
    record = TagDB(
        created_datetime_utc=datetime.now(timezone.utc),
        tag_id=tag_id,
        tag_name="tag",
        updated_datetime_utc=datetime.now(timezone.utc),
        workspace_id=workspace_id,
    )
    result = _convert_record_to_schema(record=record)
    assert result.tag_id == tag_id
    assert result.workspace_id == workspace_id
    assert result.tag_name == "tag"
