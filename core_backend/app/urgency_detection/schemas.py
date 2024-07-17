from typing import Dict, List

from pydantic import BaseModel, ConfigDict

from ..llm_call.entailment import UrgencyDetectionEntailment
from ..urgency_rules.schemas import UrgencyRuleCosineDistance


class UrgencyQuery(BaseModel):
    """
    Query for urgency detection
    """

    message_text: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "message_text": "Is it normal to feel dizzy and blurry vision?"
                    "I've also been feeling nauseous for the past few weeks.",
                }
            ]
        },
    )


class UrgencyResponse(BaseModel):
    """
    Urgency detection response class
    """

    is_urgent: bool
    flagged_rules: List[str]
    details: (
        Dict[int, UrgencyRuleCosineDistance]
        | UrgencyDetectionEntailment.UrgencyDetectionEntailmentResult
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {  # Cosine distance classifier example
                    "is_urgent": True,
                    "flagged_rules": [
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
                    "flagged_rules": [
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
