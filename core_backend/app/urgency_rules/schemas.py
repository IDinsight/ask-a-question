"""This module contains Pydantic models for urgency rules."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class UrgencyRuleCosineDistance(BaseModel):
    """Pydantic model for urgency detection result when using the cosine distance
    method (i.e., environment variable LLM_CLASSIFIER is set to
    "cosine_distance_classifier").
    """

    distance: float = Field(..., examples=[0.1])
    urgency_rule: str = Field(..., examples=["Blurry vision and dizziness"])


class UrgencyRuleCreate(BaseModel):
    """Pydantic model for creating a new urgency rule."""

    urgency_rule_metadata: dict = Field(default_factory=dict)
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

    model_config = ConfigDict(from_attributes=True)


class UrgencyRuleRetrieve(UrgencyRuleCreate):
    """Pydantic model for retrieving an urgency rule."""

    created_datetime_utc: datetime
    updated_datetime_utc: datetime
    urgency_rule_id: int
    workspace_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "urgency_rule_id": 1,
                    "workspace_id": 1,
                    "created_datetime_utc": "2024-01-01T00:00:00",
                    "updated_datetime_utc": "2024-01-01T00:00:00",
                    "urgency_rule_text": "Blurry vision and dizziness",
                    "urgency_rule_metadata": {},
                },
            ]
        },
    )
