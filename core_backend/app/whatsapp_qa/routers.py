from datetime import datetime
from typing import Union

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..contents.models import get_similar_content_async
from ..database import get_async_session
from .config import WHATSAPP_TOKEN, WHATSAPP_VERIFY_TOKEN
from .models import (
    save_wamessage_to_db,
    save_waresponse_to_db,
)
from .schemas import WhatsAppIncoming, WhatsAppResponse

router = APIRouter(tags=["WhatsApp"])


@router.post("/webhook")
async def process_whatsapp_message(
    request: Request, asession: AsyncSession = Depends(get_async_session)
) -> dict:
    """
    Processes incoming WhatsApp messages, saves them to
    the database, and sends a response.

    Args:
        request (Request): The incoming request object.
        asession (AsyncSession, optional): The asynchronous database session.
            Defaults to Depends(get_async_session).

    Returns:
        dict: A dictionary containing the status of the request.
    """
    payload = await request.json()

    if "object" in payload:
        if "entry" in payload and "changes" in payload["entry"][0]:
            change_value = payload["entry"][0]["changes"][0]["value"]

            if "messages" in change_value and change_value["messages"][0]:
                phone_number_id = change_value["metadata"]["phone_number_id"]
                from_phone = change_value["messages"][0]["from"]
                msg_body = change_value["messages"][0]["text"]["body"]
                msg_id = change_value["messages"][0]["id"]

                # Add incoming message to DB
                incoming_to_process = WhatsAppIncoming(
                    phone_number=from_phone,
                    message=msg_body,
                    phone_id=phone_number_id,
                    msg_id_from_whatsapp=msg_id,
                )
                incoming_db = await save_wamessage_to_db(
                    incoming=incoming_to_process, asession=asession
                )

                content_response = await get_similar_content_async(
                    user_id=1,  # hard codes user_id for now
                    question=msg_body,
                    n_similar=1,
                    asession=asession,
                )
                top_faq = content_response[0][1]
                data_obj = {
                    "messaging_product": "whatsapp",
                    "to": from_phone,
                    "text": {"body": "Top matching FAQ: " + top_faq},
                }

                async with httpx.AsyncClient() as client:
                    httpx_request = await client.post(
                        f"https://graph.facebook.com/v12.0/{phone_number_id}/messages",
                        params={"access_token": WHATSAPP_TOKEN},
                        headers={"Content-Type": "application/json"},
                        json=data_obj,
                    )
                    # Save response to DB
                    response = WhatsAppResponse(
                        incoming_id=incoming_db.incoming_id,
                        response_text=top_faq,
                        response_status=int(httpx_request.status_code),
                        response_datetime_utc=datetime.utcnow(),
                    )
                    await save_waresponse_to_db(
                        response=response,
                        asession=asession,
                    )

                    return httpx_request.json()
        return {"status": "No Message to Process"}
    else:
        raise HTTPException(status_code=404, detail="Invalid request")


@router.get("/webhook")
async def validate_webhook(
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> Union[int, dict]:
    """
    This function is used to validate the webhook.
    It checks if the token matches the verify token and returns the
    challenge if it does.

    Args:
        token: The token sent by WhatsApp.
        challenge: The challenge sent by WhatsApp.

    Returns:
        int: The challenge sent by WhatsApp.
        OR (in case of invalid token)
        dict: A dictionary containing the status of the response.
    """
    if token == WHATSAPP_VERIFY_TOKEN:
        return int(challenge)
    else:
        return {"status": 403}
