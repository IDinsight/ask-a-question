import datetime
import uuid
from typing import Any, Dict, Generator, Union

import pytest
from fastapi.testclient import TestClient
from qdrant_client.models import Record

from core_backend.app.configs.app_config import (
    QDRANT_COLLECTION_NAME,
)
from core_backend.app.db.vector_db import get_qdrant_client
from core_backend.app.routers.manage_content import (
    _add_content_to_qdrant,
    _convert_record_to_schema,
    _create_payload,
)
from core_backend.app.schemas import ContentCreate, ContentRetrieve


class TestManageContent:
    @pytest.fixture(
        scope="function",
        params=[
            ("test content - no metadata", {}),
            ("test content - with metadata", {"meta_key": "meta_value"}),
        ],
    )
    def existing_content_id(
        self, request: pytest.FixtureRequest, client: TestClient
    ) -> Generator[str, None, None]:
        response = client.post(
            "/content/create",
            json={
                "content_text": request.param[0],
                "content_metadata": request.param[1],
            },
        )
        content_id = response.json()["content_id"]
        yield content_id
        client.delete(f"/content/{content_id}/delete")

    @pytest.mark.parametrize(
        "content_text, content_metadata",
        [("test content 3", {}), ("test content 2", {"meta_key": "meta_value"})],
    )
    def test_create_and_delete_content(
        self,
        client: TestClient,
        content_text: str,
        content_metadata: Dict[Any, Any],
    ) -> None:
        response = client.post(
            "/content/create",
            json={"content_text": content_text, "content_metadata": content_metadata},
        )
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["content_metadata"] == content_metadata
        assert "content_id" in json_response

        response = client.delete(f"/content/{json_response['content_id']}/delete")
        assert response.status_code == 200

        pass

    @pytest.mark.parametrize(
        "content_text, content_metadata",
        [
            ("test content 3 - edited", {}),
            (
                "test content 4 - edited",
                {"new_meta_key": "new meta_value", "meta_key": "meta_value_edited #2"},
            ),
        ],
    )
    def test_edit_and_retrieve_content(
        self,
        client: TestClient,
        existing_content_id: str,
        content_text: str,
        content_metadata: Dict[Any, Any],
    ) -> None:
        response = client.put(
            f"/content/{existing_content_id}/edit",
            json={
                "content_text": content_text,
                "content_metadata": content_metadata,
            },
        )
        assert response.status_code == 200

        response = client.get(f"/content/{existing_content_id}")
        assert response.status_code == 200
        assert response.json()["content_text"] == content_text
        edited_metadata = response.json()["content_metadata"]

        assert all(edited_metadata[k] == v for k, v in content_metadata.items())

    def test_edit_content_not_found(self, client: TestClient) -> None:
        response = client.put(
            "/content/00000000-0000-0000-0000-000000000000/edit",
            json={"content_text": "sample text", "content_metadata": {"key": "value"}},
        )

        assert response.status_code == 404

    def test_list_content(self, client: TestClient, existing_content_id: str) -> None:
        response = client.get("/content/list")
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_delete_content(self, client: TestClient, existing_content_id: str) -> None:
        response = client.delete(f"/content/{existing_content_id}/delete")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "content_metadata",
        [{}, {"meta_key": "meta_value"}],
    )
    def test_creating_missing_content_text_returns_422(
        self, client: TestClient, content_metadata: Dict[Any, Any]
    ) -> None:
        response = client.post(
            "/content/create",
            json=content_metadata,
        )
        assert response.status_code == 422


class TestAddContentToQdrant:
    @pytest.fixture(scope="function")
    def valid_payload(self) -> Dict[Any, Any]:
        return _create_payload(content_text="content", metadata={})

    @pytest.fixture(scope="function")
    def random_uuid(self) -> pytest.FixtureRequest:
        """Generates random UUID for testing and deletes a record with the ID from the
        Qdrant test collection"""
        qdrant_client = get_qdrant_client()
        _uuid_id = uuid.uuid4()
        yield _uuid_id
        qdrant_client.delete(
            collection_name=QDRANT_COLLECTION_NAME, points_selector=[str(_uuid_id)]
        )

    @pytest.mark.parametrize(
        "content_text, content_metadata",
        [
            ("content text 1", {}),
            ("content text 2", {"meta_key": "meta_value"}),
        ],
    )
    def test_add_content_to_qdrant_return_value(
        self,
        content_text: str,
        content_metadata: Union[Dict[Any, Any], None],
        random_uuid: pytest.FixtureRequest,
        valid_payload: pytest.FixtureRequest,
        client: TestClient,
    ) -> None:
        qdrant_client = get_qdrant_client()

        result = _add_content_to_qdrant(
            random_uuid,
            ContentCreate(content_text=content_text, content_metadata=content_metadata),
            valid_payload,
            qdrant_client=qdrant_client,
        )
        assert isinstance(result, ContentRetrieve)
        assert result.content_id == random_uuid
        assert result.content_text == content_text

    def test_add_content_to_qdrant_correctly_adds_content(
        self, random_uuid: pytest.FixtureRequest, client: TestClient
    ) -> None:
        qdrant_client = get_qdrant_client()

        timestamp = datetime.datetime(2023, 9, 1, 0, 0, 0)
        payload = {
            "created_datetime_utc": timestamp,
            "updated_datetime_utc": timestamp,
            "test_key": "test_value",
        }
        _add_content_to_qdrant(
            random_uuid,
            ContentCreate(content_text="content text 1", content_metadata={}),
            payload,
            qdrant_client=qdrant_client,
        )

        records = qdrant_client.scroll(collection_name=QDRANT_COLLECTION_NAME)[0]

        assert any(str(random_uuid) == record.id for record in records)

        for record in records:
            if record.id == str(random_uuid):
                break

        assert record.payload["test_key"] == "test_value"


class TestConvertRecordToSchema:
    def test_basic_conversion(self) -> None:
        content_uuid = uuid.uuid4()

        record = Record(
            id=str(content_uuid),
            payload={
                "created_datetime_utc": datetime.datetime.utcnow(),
                "updated_datetime_utc": datetime.datetime.utcnow(),
                "content_text": "sample text",
                "extra_field": "extra value",
            },
        )
        result = _convert_record_to_schema(record)
        assert result.content_id == content_uuid
        assert result.content_text == "sample text"
        assert result.content_metadata["extra_field"] == "extra value"

    def test_with_missing_payload(self) -> None:
        content_uuid = uuid.uuid4()
        record = Record(id=str(content_uuid))
        with pytest.raises(
            KeyError
        ):  # Expecting an error due to missing payload attributes
            _convert_record_to_schema(record)

    def test_with_missing_metadata_fields(self) -> None:
        content_uuid = uuid.uuid4()
        record = Record(
            id=str(content_uuid),
            payload={
                "updated_datetime_utc": datetime.datetime.utcnow(),
                "content_text": "sample text",
            },
        )
        with pytest.raises(
            KeyError
        ):  # Expecting an error due to missing 'created_datetime_utc'
            _convert_record_to_schema(record)

    def test_with_invalid_uuid(self) -> None:
        record = Record(
            id="invalid_uuid",
            payload={
                "created_datetime_utc": datetime.datetime.utcnow(),
                "updated_datetime_utc": datetime.datetime.utcnow(),
                "content_text": "sample text",
            },
        )
        with pytest.raises(ValueError):  # Expecting an error due to invalid UUID format
            _convert_record_to_schema(record)
