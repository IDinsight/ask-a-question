from datetime import datetime, timezone
from io import BytesIO
from typing import Generator

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core_backend.app.auth.dependencies import create_access_token
from core_backend.app.users.models import UserDB
from core_backend.app.utils import get_key_hash, get_password_salted_hash


def _dict_to_csv_bytes(data: dict) -> BytesIO:
    """
    Convert a dictionary to a CSV file in bytes
    """

    df = pd.DataFrame(data)
    csv_bytes = BytesIO()
    df.to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)

    return csv_bytes


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


class TestImportContentQuota:
    @pytest.mark.parametrize(
        "temp_user_token_and_quota",
        [
            {"username": "temp_user_limit_10", "content_quota": 10},
            {"username": "temp_user_limit_unlimited", "content_quota": None},
        ],
        indirect=True,
    )
    async def test_import_content_success(
        self,
        client: TestClient,
        temp_user_token_and_quota: tuple[str, int],
    ) -> None:
        temp_user_token, content_quota = temp_user_token_and_quota
        data = _dict_to_csv_bytes(
            {
                "title": ["csv title 1", "csv title 2"],
                "text": ["csv text 1", "csv text 2"],
            }
        )

        response = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {temp_user_token}"},
            files={"file": ("test.csv", data, "text/csv")},
        )
        assert response.status_code == 200

        if response.status_code == 200:
            json_response = response.json()
            contents_list = json_response["contents"]
            for content in contents_list:
                content_id = content["content_id"]
                response = client.delete(
                    f"/content/{content_id}",
                    headers={"Authorization": f"Bearer {temp_user_token}"},
                )
                assert response.status_code == 200

    @pytest.mark.parametrize(
        "temp_user_token_and_quota",
        [
            {"username": "temp_user_limit_10", "content_quota": 0},
        ],
        indirect=True,
    )
    async def test_import_content_failure(
        self,
        client: TestClient,
        temp_user_token_and_quota: tuple[str, int],
    ) -> None:
        temp_user_token, content_quota = temp_user_token_and_quota
        data = _dict_to_csv_bytes(
            {
                "title": ["csv title 1", "csv title 2"],
                "text": ["csv text 1", "csv text 2"],
            }
        )
        response = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {temp_user_token}"},
            files={"file": ("test.csv", data, "text/csv")},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["errors"][0]["type"] == "exceeds_quota"


class TestImportContent:
    @pytest.fixture
    def data_valid(self) -> BytesIO:
        data = {
            "title": ["csv title 1", "csv title 2"],
            "text": ["csv text 1", "csv text 2"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_valid_with_tags(self) -> BytesIO:
        data = {
            "title": ["csv title 1", "csv title 2"],
            "text": ["csv text 1", "csv text 2"],
            "tags": ["tag1, tag2", "tag1, tag4"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_empty_csv(self) -> BytesIO:
        data: dict = {}
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_no_rows(self) -> BytesIO:
        data: dict = {
            "title": [],
            "text": [],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_title_spaces_only(self) -> BytesIO:
        data: dict = {
            "title": ["  "],
            "text": ["csv text 1"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_text_spaces_only(self) -> BytesIO:
        data: dict = {
            "title": ["csv title 1"],
            "text": ["  "],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_missing_columns(self) -> BytesIO:
        data = {
            "wrong_column_1": ["Value 1", "Value 2"],
            "wrong_column_2": ["Value 3", "Value 4"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_title_missing(self) -> BytesIO:
        data = {
            "title": ["", "csv text 1"],
            "text": ["csv title 2", "csv text 2"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_text_missing(self) -> BytesIO:
        data = {
            "title": ["csv title 1", "csv title 2"],
            "text": ["", "csv text 2"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_long_title(self) -> BytesIO:
        data = {
            "title": ["a" * 151],
            "text": ["Valid text"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_long_text(self) -> BytesIO:
        data = {
            "title": ["Valid title"],
            "text": ["a" * 2001],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_duplicate_titles(self) -> BytesIO:
        data = {
            "title": ["Duplicate title", "Duplicate title"],
            "text": ["Text 1", "Text 2"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_duplicate_texts(self) -> BytesIO:
        data = {
            "title": ["Title 1", "Title 2"],
            "text": ["Duplicate text", "Duplicate text"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.mark.parametrize(
        "mock_csv_data",
        ["data_valid", "data_valid_with_tags"],
    )
    async def test_csv_import_success(
        self,
        client: TestClient,
        mock_csv_data: BytesIO,
        request: pytest.FixtureRequest,
        fullaccess_token: str,
    ) -> None:
        mock_csv_file = request.getfixturevalue(mock_csv_data)

        response = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            files={"file": ("test.csv", mock_csv_file, "text/csv")},
        )
        assert response.status_code == 200

        # cleanup
        json_response = response.json()
        # delete contents
        contents_list = json_response["contents"]
        for content in contents_list:
            content_id = content["content_id"]
            response = client.delete(
                f"/content/{content_id}",
                headers={"Authorization": f"Bearer {fullaccess_token}"},
            )
            assert response.status_code == 200
        # delete tags
        tags_list = json_response["tags"]
        for tag in tags_list:
            tag_id = tag["tag_id"]
            response = client.delete(
                f"/tag/{tag_id}",
                headers={"Authorization": f"Bearer {fullaccess_token}"},
            )
            assert response.status_code == 200

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
        client: TestClient,
        mock_csv_data: BytesIO,
        expected_error_type: str,
        request: pytest.FixtureRequest,
        fullaccess_token: str,
    ) -> None:
        # fetch data from the fixture
        mock_csv_file = request.getfixturevalue(mock_csv_data)

        response = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            files={"file": ("test.csv", mock_csv_file, "text/csv")},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["errors"][0]["type"] == expected_error_type


class TestDBDuplicates:
    @pytest.fixture(scope="function")
    def existing_content_in_db(
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

    @pytest.fixture
    def data_title_in_db(self) -> BytesIO:
        # Assuming "Title in DB" is a title that exists in the database
        data = {
            "title": ["Title in DB"],
            "text": ["New text"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.fixture
    def data_text_in_db(self) -> BytesIO:
        # Assuming "Text in DB" is a text that exists in the database
        data = {
            "title": ["New title"],
            "text": ["Text in DB"],
        }
        return _dict_to_csv_bytes(data)

    @pytest.mark.parametrize(
        "mock_csv_data, expected_error_type",
        [("data_title_in_db", "title_in_db"), ("data_text_in_db", "text_in_db")],
    )
    async def test_csv_import_db_duplicates(
        self,
        client: TestClient,
        fullaccess_token: str,
        mock_csv_data: BytesIO,
        expected_error_type: str,
        request: pytest.FixtureRequest,
        existing_content_in_db: str,
    ) -> None:
        """
        This test uses the existing_content_in_db fixture to create a content in the
        database and then tries to import a CSV file with a title or text that already
        exists in the database.
        """
        mock_csv_file = request.getfixturevalue(mock_csv_data)
        response_text_dupe = client.post(
            "/content/csv-upload",
            headers={"Authorization": f"Bearer {fullaccess_token}"},
            files={"file": ("test.csv", mock_csv_file, "text/csv")},
        )
        assert response_text_dupe.status_code == 400
        assert (
            response_text_dupe.json()["detail"]["errors"][0]["type"]
            == expected_error_type
        )
