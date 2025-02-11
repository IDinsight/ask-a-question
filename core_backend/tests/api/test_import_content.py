"""This module contains tests for the import content API endpoint."""

from io import BytesIO
from typing import Generator

import pandas as pd
import pytest
from fastapi import status
from fastapi.testclient import TestClient


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
