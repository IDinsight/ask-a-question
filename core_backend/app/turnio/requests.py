"""This module contains functions to send requests to Turn.io API."""

from typing import Any
from urllib.parse import urljoin

import httpx

from ..config import TURNIO_API_BASE
from .schemas import TurnMessageBody, TurnTextMessage


async def send_turn_text_message(
    *, httpx_client: httpx.AsyncClient, text: str, turnio_api_key: str, whatsapp_id: str
) -> dict[str, Any]:
    """Send a text message via Turn API.

    Parameters
    ----------
    httpx_client
        An HTTPX async client for making HTTP requests.
    text
        The text message to send.
    turnio_api_key
        The Turn.io API key for authentication.
    whatsapp_id
        The recipient's WhatsApp ID.

    Returns
    -------
    dict[str, Any]
        The JSON response from the Turn.io API.
    """

    message = TurnTextMessage(to=whatsapp_id, text=TurnMessageBody(body=text))
    payload = message.model_dump(exclude_none=True)

    response = await httpx_client.post(
        urljoin(TURNIO_API_BASE, "messages"),
        json=payload,
        headers={"Authorization": f"Bearer {turnio_api_key}"},
    )
    response.raise_for_status()

    return response.json()
