"""This module contains tests for turnio/requests.py."""

from typing import Any
from urllib.parse import urljoin

import httpx
import pytest
from fastapi import status

from core_backend.app.config import TURNIO_API_BASE
from core_backend.app.turnio.requests import send_turn_text_message


class FakeResponse:
    """A fake HTTP response for testing purposes."""

    def __init__(self, status_code: int, data: dict[str, Any]) -> None:
        """Initialize the fake response.

        Parameters
        ----------
        status_code
            The HTTP status code of the response.
        data
            The JSON data of the response.
        """

        self._data = data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise an error for bad status codes."""

        if self.status_code >= status.HTTP_400_BAD_REQUEST:
            # Raise an HTTPStatusError similar to what httpx would do.
            raise httpx.HTTPStatusError(
                message="Request failed",
                request=httpx.Request("POST", "https://example.com/messages"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict[str, Any]:
        """Return the JSON data of the response.

        Returns
        -------
        dict[str, Any]
            The JSON data of the response.
        """

        return self._data


class RecordingAsyncClient:
    """Fake async client that records the last POST call."""

    def __init__(self, response: FakeResponse) -> None:
        """Initialize the recording client.

        Parameters
        ----------
        response
            The fake response to return on POST requests.
        """

        self.last_headers: dict[str, Any] = {}
        self.last_json: dict[str, Any] = {}
        self.last_url: str = ""
        self.response = response

    async def post(
        self, url: str, json: dict[str, Any], headers: dict[str, Any]
    ) -> FakeResponse:
        """Record the POST request parameters and return the fake response.

        Parameters
        ----------
        url
            The URL of the POST request.
        json
            The JSON payload of the POST request.
        headers
            The headers of the POST request.

        Returns
        -------
        FakeResponse
            The fake response.
        """

        self.last_headers = headers
        self.last_json = json
        self.last_url = url

        return self.response


@pytest.mark.asyncio
async def test_send_turn_text_message_success() -> None:
    """Test sending a text message via Turn.io API successfully."""

    expected_response = {"id": "msg_123", "status": "queued"}

    fake_response = FakeResponse(data=expected_response, status_code=status.HTTP_200_OK)
    fake_client = RecordingAsyncClient(response=fake_response)

    text = "Hello from tests"
    api_key = "test-api-key"
    whatsapp_id = "whatsapp:+1234567890"

    result = await send_turn_text_message(
        httpx_client=fake_client,  # type: ignore
        text=text,
        turnio_api_key=api_key,
        whatsapp_id=whatsapp_id,
    )

    assert result == expected_response
    assert fake_client.last_url == urljoin(TURNIO_API_BASE, "messages")

    assert fake_client.last_json["to"] == whatsapp_id
    assert fake_client.last_json["type"] == "text"
    assert fake_client.last_json["text"]["body"] == text

    assert fake_client.last_json["recipient_type"] == "individual"
    assert fake_client.last_json["preview_url"] is False

    assert fake_client.last_headers["Authorization"] == f"Bearer {api_key}"


@pytest.mark.asyncio
async def test_send_turn_text_message_raises_on_http_error() -> None:
    """Test that sending a text message raises an error on HTTP failure."""

    # Arrange response so that it will raise HTTPStatusError.
    error_response = FakeResponse(
        data={"error": "Bad Request"}, status_code=status.HTTP_400_BAD_REQUEST
    )
    fake_client = RecordingAsyncClient(response=error_response)

    with pytest.raises(httpx.HTTPStatusError):
        await send_turn_text_message(
            httpx_client=fake_client,  # type: ignore
            text="This will fail",
            turnio_api_key="bad-key",
            whatsapp_id="whatsapp:+0000000000",
        )
