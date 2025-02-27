"""This module contains Pydantic models for the urgency detection."""

from pydantic import BaseModel, ConfigDict, Field

from ..llm_call.entailment import UrgencyDetectionEntailment
from ..urgency_rules.schemas import UrgencyRuleCosineDistance


class UrgencyQuery(BaseModel):
    """Pydantic model for urgency detection queries."""

    message_text: str = Field(
        ...,
        examples=[
            "Is it normal to feel dizzy and blurry vision? I've also been feeling nauseous for the past few weeks."  # noqa: E501
        ],
    )

    model_config = ConfigDict(from_attributes=True)


class UrgencyResponse(BaseModel):
    """Pydantic model for urgency detection responses."""

    details: (
        dict[int, UrgencyRuleCosineDistance]
        | UrgencyDetectionEntailment.UrgencyDetectionEntailmentResult
    )
    is_urgent: bool
    matched_rules: list[str]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {  # Cosine distance classifier example
                    "is_urgent": True,
                    "matched_rules": [
                        "Blurry vision and dizziness",
                        "Nausea that lasts for 3 days",
                    ],
                    "details": {
                        "0": {
                            "urgency_rule": "Blurry vision and dizziness",
                            "distance": 0.1,
                        },
                        "1": {
                            "urgency_rule": "Nausea that lasts for 3 days",
                            "distance": 0.2,
                        },
                    },
                },
                {  # LLM entailment classifier example
                    "is_urgent": True,
                    "matched_rules": [
                        "Blurry vision and dizziness",
                        "Nausea that lasts for 3 days",
                    ],
                    "details": {
                        "0": {
                            "urgency_rule": "Blurry vision and dizziness",
                            "distance": 0.1,
                        },
                        "1": {
                            "urgency_rule": "Nausea that lasts for 3 days",
                            "distance": 0.2,
                        },
                    },
                },
            ]
        },
    )
