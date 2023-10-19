import datetime
import uuid
from typing import Any, Dict, Generator, List

import pytest
from fastapi.testclient import TestClient
from qdrant_client.http import models
from qdrant_client.models import Record

from core_backend.app.configs.app_config import (
    QDRANT_COLLECTION_NAME,
)
from core_backend.app.db.vector_db import get_qdrant_client
from core_backend.app.routers.manage_content import (
    _convert_record_to_schema,
    _create_payload_for_qdrant_upsert,
    _upsert_content_to_qdrant,
)
from core_backend.app.schemas import ContentCreate

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


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


class TestUpsertContentToQdrant:
    @pytest.fixture(scope="function")
    def valid_payload(self) -> Dict[Any, Any]:
        return _create_payload_for_qdrant_upsert(content_text="content", metadata={})

    @pytest.fixture(scope="function")
    def random_uuid(self) -> pytest.FixtureRequest:
        yield uuid.uuid4()

    @pytest.fixture(scope="function", autouse=True)
    def clean(self, random_uuid: uuid.UUID) -> pytest.FixtureRequest:
        """Clean record created by the test"""
        yield
        qdrant_client = get_qdrant_client()
        qdrant_client.delete(
            collection_name=QDRANT_COLLECTION_NAME, points_selector=[str(random_uuid)]
        )

    def _search_qdrant_collection_by_id(self, content_id: uuid.UUID) -> List[Record]:
        qdrant_client = get_qdrant_client()
        return qdrant_client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.HasIdCondition(has_id=[str(content_id)]),
                ],
            ),
        )[0]

    @pytest.mark.parametrize(
        "content_text, content_metadata",
        [
            ("content text 1", {}),
            ("content text 2", {"meta_key": "meta_value"}),
        ],
    )
    def test_upsert_content_to_qdrant_return_value(
        self,
        content_text: str,
        content_metadata: Dict[Any, Any],
        random_uuid: pytest.FixtureRequest,
        valid_payload: pytest.FixtureRequest,
        client: TestClient,
    ) -> None:
        qdrant_client = get_qdrant_client()

        result = _upsert_content_to_qdrant(
            random_uuid,
            ContentCreate(content_text=content_text, content_metadata=content_metadata),
            valid_payload,
            qdrant_client=qdrant_client,
        )

        assert result.content_id == random_uuid
        assert result.content_text == content_text

        updated_content_text = content_text + " updated"

        updated_result = _upsert_content_to_qdrant(
            random_uuid,
            ContentCreate(
                content_text=updated_content_text, content_metadata=content_metadata
            ),
            valid_payload,
            qdrant_client=qdrant_client,
        )

        assert updated_result.content_id == random_uuid
        assert updated_result.content_text == updated_content_text

    def test_upsert_content_to_qdrant_correctly_adds_or_updates_content(
        self, random_uuid: pytest.FixtureRequest, client: TestClient
    ) -> None:
        qdrant_client = get_qdrant_client()

        timestamp = datetime.datetime.utcnow()
        payload = {
            "created_datetime_utc": timestamp,
            "updated_datetime_utc": timestamp,
            "test_key": "test_value",
        }
        _upsert_content_to_qdrant(
            random_uuid,
            ContentCreate(content_text="content text", content_metadata={}),
            payload,
            qdrant_client=qdrant_client,
        )

        matches = self._search_qdrant_collection_by_id(random_uuid)

        assert len(matches) == 1
        assert matches[0].payload["test_key"] == "test_value"

        updated_content_text = "updated content text"
        updated_timestamp = datetime.datetime.utcnow()
        payload["updated_datetime_utc"] = updated_timestamp

        _upsert_content_to_qdrant(
            random_uuid,
            ContentCreate(content_text=updated_content_text, content_metadata={}),
            payload,
            qdrant_client=qdrant_client,
        )

        new_matches = self._search_qdrant_collection_by_id(random_uuid)

        assert len(new_matches) == 1
        assert (
            new_matches[0].payload["created_datetime_utc"]
            == matches[0].payload["created_datetime_utc"]
        )
        assert new_matches[0].payload[
            "updated_datetime_utc"
        ] == updated_timestamp.strftime(DATETIME_FORMAT)


def test_convert_record_to_schema() -> None:
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


@pytest.mark.parametrize(
    "content_text, content_metadata",
    [
        ("", {}),
        ("sample text", {"meta_key": "meta_value"}),
        (
            "sample text",
            {"created_datetime_utc": datetime.datetime(2023, 9, 1, 0, 0, 0)},
        ),
        (
            "sample text",
            {"updated_datetime_utc": datetime.datetime(2023, 9, 1, 0, 0, 0)},
        ),
    ],
)
def test_create_payload_for_qdrant_upsert_return_dict(
    content_text: str, content_metadata: Dict[str, Any]
) -> None:
    payload = _create_payload_for_qdrant_upsert(
        content_text=content_text, metadata=content_metadata
    )

    assert payload["content_text"] == content_text
    assert payload["updated_datetime_utc"] >= payload["created_datetime_utc"]

    for key in content_metadata:
        assert key in payload
