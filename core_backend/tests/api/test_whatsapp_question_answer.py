import pytest
from fastapi.testclient import TestClient

from core_backend.app.configs.app_config import (
    WHATSAPP_VERIFY_TOKEN,
)


class TestWhatsAppWebhook:
    def test_post_webhook_response(
        self,
        client: TestClient,
        faq_contents: pytest.FixtureRequest,
        patch_httpx_call: pytest.FixtureRequest,
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
