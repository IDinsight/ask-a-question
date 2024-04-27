from typing import Any, Dict

from pydantic import BaseModel, ConfigDict


class UrgencyQuery(BaseModel):
    """
    UrgencyQuery schema
    """

    message_text: str

    model_config = ConfigDict(from_attributes=True)


class UrgencyResponse(BaseModel):
    """
    UrgencyResponse schema
    """

    is_urgent: bool
    details: Dict[Any, Any]

    model_config = ConfigDict(from_attributes=True)
