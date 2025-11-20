"""This module contains tests for turnio/schemas.py."""

import pytest
from pydantic import ValidationError

from core_backend.app.turnio.schemas import (
    TurnMessage,
    TurnMessageBody,
    TurnTextMessage,
)


class DummyBody:
    """Helper class for testing from_attributes on TurnMessageBody."""

    def __init__(self, body: str) -> None:
        """

        Parameters
        ----------
        body
            The body of the message.
        """

        self.body = body


def test_turn_message_body_from_str() -> None:
    """TurnMessageBody should support direct initialization with a string."""

    msg_body = TurnMessageBody(body="Hello world")

    assert msg_body.body == "Hello world"
    assert msg_body.model_dump() == {"body": "Hello world"}


def test_turn_message_body_from_attributes() -> None:
    """TurnMessageBody should support from_attributes via ConfigDict."""

    dummy = DummyBody("Hello from attributes")
    msg_body = TurnMessageBody.model_validate(dummy)

    assert msg_body.body == "Hello from attributes"


def test_turn_message_defaults() -> None:
    """TurnMessage should have correct default values."""

    msg = TurnMessage(to="1234567890")

    assert msg.preview_url is False
    assert msg.recipient_type == "individual"
    assert msg.type == "text"
    assert msg.to == "1234567890"


def test_turn_message_all_fields_explicit() -> None:
    """TurnMessage should accept all fields explicitly."""

    msg = TurnMessage(
        to="9876543210",
        preview_url=True,
        recipient_type="individual",
        type="audio",
    )

    assert msg.preview_url is True
    assert msg.recipient_type == "individual"
    assert msg.type == "audio"
    assert msg.to == "9876543210"


def test_turn_message_invalid_recipient_type() -> None:
    """Non-allowed recipient_type should raise a ValidationError."""

    with pytest.raises(ValidationError):
        TurnMessage(to="123", recipient_type="group")  # type: ignore


def test_turn_message_invalid_type() -> None:
    """Non-allowed type should raise a ValidationError."""

    with pytest.raises(ValidationError):
        TurnMessage(to="123", type="document")  # type: ignore


def test_turn_text_message_valid_with_body_model() -> None:
    """TurnTextMessage should accept TurnMessageBody as text field."""

    body = TurnMessageBody(body="Hello via TurnTextMessage")
    msg = TurnTextMessage(to="1234567890", text=body)

    assert msg.to == "1234567890"
    assert msg.text is body
    assert msg.text.body == "Hello via TurnTextMessage"
    # type is fixed to "text"
    assert msg.type == "text"


def test_turn_text_message_valid_with_body_dict() -> None:
    """Pydantic should coerce dict to TurnMessageBody."""

    msg = TurnTextMessage(to="1234567890", text={"body": "Hello from dict"})  # type: ignore

    assert isinstance(msg.text, TurnMessageBody)
    assert msg.text.body == "Hello from dict"
    assert msg.type == "text"


def test_turn_text_message_ignores_non_text_type() -> None:
    """Passing a non-'text' type into TurnTextMessage should fail validation."""

    with pytest.raises(ValidationError):
        TurnTextMessage(
            to="1234567890",
            type="audio",  # type: ignore
            text={"body": "Should fail"},  # type: ignore
        )


def test_turn_text_message_requires_text_field() -> None:
    """TurnTextMessage must have a 'text' field."""

    with pytest.raises(ValidationError):
        TurnTextMessage(to="1234567890")  # type: ignore


def test_turn_text_message_inherits_defaults_from_turn_message() -> None:
    """TurnTextMessage should inherit preview_url and recipient_type defaults."""

    msg = TurnTextMessage(to="1234567890", text={"body": "Hello"})  # type: ignore

    assert msg.preview_url is False
    assert msg.recipient_type == "individual"
    assert msg.type == "text"
