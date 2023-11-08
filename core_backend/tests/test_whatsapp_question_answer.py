import json
import uuid

import pytest
from fastapi.testclient import TestClient
from qdrant_client.models import PointStruct

from core_backend.app.configs.app_config import (
    EMBEDDING_MODEL,
    QDRANT_COLLECTION_NAME,
    WHATSAPP_VERIFY_TOKEN,
)
from core_backend.app.db.vector_db import get_qdrant_client
from core_backend.app.routers.manage_content import _create_payload_for_qdrant_upsert

from .conftest import fake_embedding


class TestWhatsAppWebhook:
    @pytest.fixture
    def faq_contents(self, client: TestClient) -> None:
        """Load the test FAQ contents into the Qdrant DB."""
        with open("tests/data/content.json", "r") as f:
            json_data = json.load(f)

        points = []
        for content in json_data:
            point_id = str(uuid.uuid4())
            content_embedding = (
                fake_embedding(EMBEDDING_MODEL, content["content_text"])
                .data[0]
                .embedding
            )
            metadata = content.get("content_metadata", {})
            payload = _create_payload_for_qdrant_upsert(
                content["content_text"], metadata
            )
            points.append(
                PointStruct(id=point_id, vector=content_embedding, payload=payload)
            )

        qdrant_client = get_qdrant_client()
        qdrant_client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points)

    def test_post_webhook_response(
        self, client: TestClient, patch_httpx_call: pytest.FixtureRequest
    ) -> None:
        """Test that the webhook response is correct."""

        # Incoming valid post data used for testing
        data = {
            "object": "whatever",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "+1234567890",
                                        "text": {"body": "What is ocean?"},
                                        "id": "your_message_id",
                                    }
                                ],
                                "metadata": {"phone_number_id": "your_phone_number_id"},
                            }
                        }
                    ]
                }
            ],
        }
        response = client.post("/webhook", json=data)
        assert response.status_code == 200
        assert response.json() == {"status": "success"}

    def test_get_webhook_correct_token(self, client: TestClient) -> None:
        """Test resopnse when token is correct."""
        response = client.get(
            "/webhook",
            params={"hub.verify_token": WHATSAPP_VERIFY_TOKEN, "hub.challenge": "1234"},
        )
        assert response.status_code == 200
        assert response.text == "1234"

    def test_get_webhook_incorrect_token(self, client: TestClient) -> None:
        """Test response when token is incorrect."""
        response = client.get(
            "/webhook",
            params={"hub.verify_token": "incorrecttoken", "hub.challenge": "1234"},
        )
        assert response.status_code == 200
        assert response.json() == {"status": 403}
