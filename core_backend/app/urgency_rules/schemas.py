from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class UrgencyRuleCreate(BaseModel):
    """
    Schema for creating a new urgency rule
    """

    urgency_rule_text: Annotated[str, StringConstraints(max_length=255)]
    urgency_rule_metadata: dict = {}

    model_config = ConfigDict(from_attributes=True)


class UrgencyRuleRetrieve(UrgencyRuleCreate):
    """
    Schema for retrieving an urgency rule
    """

    urgency_rule_id: int
    user_id: str
    created_datetime_utc: datetime
    updated_datetime_utc: datetime
