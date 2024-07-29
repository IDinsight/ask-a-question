from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class UrgencyRuleCreate(BaseModel):
    """
    Schema for creating a new urgency rule
    """

    urgency_rule_text: Annotated[
        str,
        Field(
            ...,
            max_length=255,
            examples=[
                "Blurry vision and dizziness",
                "Blurry vision, dizziness, and nausea",
            ],
        ),
    ]
    urgency_rule_metadata: dict = {}

    model_config = ConfigDict(from_attributes=True)


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

    urgency_rule: str = Field(..., examples=["Blurry vision and dizziness"])
    distance: float = Field(..., examples=[0.1])
