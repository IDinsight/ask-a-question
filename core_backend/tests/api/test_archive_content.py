"""This module tests the archive content API endpoints."""

from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.contents.models import get_search_results
from core_backend.tests.api.conftest import async_fake_embedding
from core_backend.tests.api.test_import_content import _dict_to_csv_bytes


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

    async def test_archived_content_does_not_appear_in_search_results(
        self,
        access_token_admin_4: str,
        asession: AsyncSession,
        client: TestClient,
        existing_content: tuple[int, str, int],
    ) -> None:
        """Ensure that archived content does not appear in search results. This test
        checks that archived content will not propagate to the content search and AI
        response functionalities. To test this, we do the following:

        1. Archive the existing content (there is only one content).
        2. Ensure that the content still appears in the search results if
            "exclude_archived" is set to "False".
        3. Ensure that the content does not appear in the search results if
            "exclude_archived" is set to "True".

        Parameters
        ----------
        access_token_admin_4
            Access token for admin user 4.
        asession
            The SQLAlchemy async session to use for all database connections.
        client
            The test client.
        existing_content
            The existing content ID, content text, and workspace ID.
        """

        existing_content_id = existing_content[0]
        workspace_id = existing_content[2]

        # 1.
        response = client.patch(
            f"/content/{existing_content_id}",
            headers={"Authorization": f"Bearer {access_token_admin_4}"},
        )
        assert response.status_code == status.HTTP_200_OK

        # 2.
        question_embedding = await async_fake_embedding()
        results_with_archived = await get_search_results(
            asession=asession,
            exclude_archived=False,
            n_similar=10,
            question_embedding=question_embedding,
            workspace_id=workspace_id,
        )
        assert len(results_with_archived) == 1

        # 3.
        results_without_archived = await get_search_results(
            asession=asession,
            exclude_archived=True,
            n_similar=10,
            question_embedding=question_embedding,
            workspace_id=workspace_id,
        )
        assert len(results_without_archived) == 0

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
