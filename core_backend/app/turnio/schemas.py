"""This module contains Pydantic models for Turn.io."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class TurnMessageBody(BaseModel):
    """
    Schema for the body of a text message using turn.io's API
    See: https://whatsapp.turn.io/docs/api/messages#text-messages
    """

    body: str

    model_config = ConfigDict(from_attributes=True)


class TurnMessage(BaseModel):
    """
    Schema for sending a message using turn.io's API.
    """

    preview_url: bool = False
    recipient_type: Literal["individual"] = "individual"
    to: str
    type: Literal["text", "audio", "image", "video", "interactive"] = "text"


class TurnTextMessage(TurnMessage):
    """
    Schema for sending a message using turn.io's API
    See: https://whatsapp.turn.io/docs/api/messages#text-messages
    """

    type: Literal["text"] = "text"
    text: TurnMessageBody
