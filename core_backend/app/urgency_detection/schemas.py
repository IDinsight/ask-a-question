from typing import Any, Dict, List

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
    failed_rules: List[str]
    details: Dict[Any, Any]

    model_config = ConfigDict(from_attributes=True)
