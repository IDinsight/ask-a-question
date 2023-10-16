import datetime
import uuid
from typing import Any, Dict, Generator, Union

import pytest
from fastapi.testclient import TestClient
from qdrant_client.models import Record

from core_backend.app.db.vector_db import get_qdrant_client
from core_backend.app.routers.manage_content import (
    _add_content_to_qdrant,
    _convert_record_to_schema,
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


@pytest.mark.parametrize(
    "content_id_type, content_text, content_metadata, payload",
    [
        ("str", "content text 1", {}, {"id": "content_id_1"}),
        ("str", "content text 2", {"meta_key": "meta_value"}, {}),
        ("uuid", "content text 3", {}, {"id": "content_id_3"}),
        ("uuid", "content text 4", {"meta_key": "meta_value"}, {}),
    ],
)
def test_add_content_to_qdrant(
    content_id_type: str,
    content_text: str,
    content_metadata: Union[Dict[Any, Any], None],
    payload: Dict[Any, Any],
) -> None:
    qdrant_client = get_qdrant_client()
    _uuid_id = uuid.uuid4()

    input_id: Union[str, uuid.UUID] = _uuid_id

    if content_id_type == "str":
        input_id = str(_uuid_id)
    elif content_id_type != "uuid":
        raise ValueError("Invalid content_id_type: " + content_id_type)

    payload["created_datetime_utc"] = datetime.datetime(2023, 9, 1, 0, 0, 0)

    result = _add_content_to_qdrant(
        input_id,
        ContentCreate(content_text=content_text, content_metadata=content_metadata),
        payload,
        qdrant_client=qdrant_client,
    )
    assert isinstance(result, ContentRetrieve)
    assert result.content_id == _uuid_id
    assert result.content_text == content_text


def test_basic_conversion() -> None:
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


def test_missing_payload() -> None:
    content_uuid = uuid.uuid4()
    record = Record(id=str(content_uuid))
    with pytest.raises(
        KeyError
    ):  # Expecting an error due to missing payload attributes
        _convert_record_to_schema(record)


def test_missing_metadata_fields() -> None:
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


def test_invalid_uuid() -> None:
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
