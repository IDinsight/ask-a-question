"""This module contains functions to send requests to Turn.io API."""

from typing import Any
from urllib.parse import urljoin

import httpx

from ..config import TURNIO_API_BASE, TURNIO_API_KEY
from .schemas import TurnMessageBody, TurnTextMessage


async def send_turn_text_message(
    *, httpx_client: httpx.AsyncClient, text: str, whatsapp_id: str
) -> dict[str, Any]:
    """Send a text message via Turn API.

    Parameters
    ----------
    text
        The text message to send.
    whatsapp_id
        The recipient's WhatsApp ID.
    httpx_client
        An HTTPX async client for making HTTP requests.

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
        headers={"Authorization": f"Bearer {TURNIO_API_KEY}"},
    )
    response.raise_for_status()

    return response.json()
