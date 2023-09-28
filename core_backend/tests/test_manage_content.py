import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any


class TestManageContent:
    @pytest.mark.parametrize(
        "content_text, content_metadata",
        [("test content 3", {}), ("test content 2", {"meta_key": "meta_value"})],
    )
    def test_create_content(
        self, client: TestClient, content_text: str, content_metadata: Dict[Any, Any]
    ) -> None:
        response = client.post(
            "/content/create",
            json={"content_text": content_text, "content_metadata": content_metadata},
        )
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["content_metadata"] == content_metadata
        assert "content_id" in json_response

        pass
