from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..models import Base
from .schemas import (
    WhatsAppIncoming,
    WhatsAppResponse,
)


class WhatsAppMessageDB(Base):
    """
    SQL Alchemy data model for incoming messages from user.
    """

    __tablename__ = "whatsapp_incoming_messages"

    incoming_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    msg_id_from_whatsapp: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    phonenumber_id: Mapped[str] = mapped_column(String, nullable=False)
    incoming_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    response = relationship(
        "WhatsAppResponseDB", back_populates="incoming_message", lazy=True
    )


class WhatsAppResponseDB(Base):
    """
    SQL Alchemy data model for responses sent to user.
    """

    __tablename__ = "whatsapp_responses"

    response_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    incoming_id = mapped_column(
        Integer, ForeignKey("whatsapp_incoming_messages.incoming_id"), nullable=False
    )
    response = mapped_column(String)
    response_datetime_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    incoming_message = relationship(
        "WhatsAppMessageDB", back_populates="response", lazy=True
    )


async def save_wamessage_to_db(
    incoming: WhatsAppIncoming,
    asession: AsyncSession,
) -> WhatsAppMessageDB:
    """
    Saves WhatsApp incoming messages to the database.
    """
    wa_incoming = WhatsAppMessageDB(
        phone_number=incoming.phone_number,
        msg_id_from_whatsapp=incoming.msg_id_from_whatsapp,
        message=incoming.message,
        phonenumber_id=incoming.phone_id,
        incoming_datetime_utc=datetime.utcnow(),
    )
    asession.add(wa_incoming)
    await asession.commit()
    await asession.refresh(wa_incoming)
    return wa_incoming


async def save_waresponse_to_db(
    response: WhatsAppResponse,
    asession: AsyncSession,
) -> WhatsAppResponseDB:
    """
    Saves WhatsApp responses to the database.
    """
    wa_response = WhatsAppResponseDB(
        incoming_id=response.incoming_id,
        response=response.response_text,
        response_datetime_utc=datetime.utcnow(),
        response_status=response.response_status,
    )
    asession.add(wa_response)
    await asession.commit()
    await asession.refresh(wa_response)
    return wa_response
