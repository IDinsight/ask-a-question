from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class UrgencyRuleCreate(BaseModel):
    """
    Schema for creating a new urgency rule
    """

    urgency_rule_text: Annotated[str, StringConstraints(max_length=255)]
    urgency_rule_metadata: dict = {}

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "urgency_rule_text": "Blurry vision and dizziness",
                },
                {
                    "urgency_rule_text": "Blurry vision, dizziness, and nausea",
                },
            ]
        },
    )


class UrgencyRuleRetrieve(UrgencyRuleCreate):
    """
    Schema for retrieving an urgency rule
    """

    urgency_rule_id: int
    user_id: int
    created_datetime_utc: datetime
    updated_datetime_utc: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "urgency_rule_id": 1,
                    "user_id": 1,
                    "created_datetime_utc": "2024-01-01T00:00:00",
                    "updated_datetime_utc": "2024-01-01T00:00:00",
                    "urgency_rule_text": "Blurry vision and dizziness",
                    "urgency_rule_metadata": {},
                },
            ]
        },
    )


class UrgencyRuleCosineDistance(BaseModel):
    """
    Schema for urgency detection result when using the cosine
    distance method (i.e. environment variable LLM_CLASSIFIER
    is set to "cosine_distance_classifier")
    """

    urgency_rule: str
    distance: float

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "urgency_rule": "Blurry vision and dizziness",
                    "distance": 0.1,
                },
            ]
        },
    )
