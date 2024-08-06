"""This module contains functionalities for detecting the urgency of a message using
LLM entailment.
"""

from typing import Optional

from pydantic import ValidationError

from ..config import LITELLM_MODEL_URGENCY_DETECT
from ..utils import setup_logger
from .llm_prompts import UrgencyDetectionEntailment
from .utils import _ask_llm_async

logger = setup_logger()


async def detect_urgency(
    urgency_rules: list[str], message: str, metadata: Optional[dict] = None
) -> UrgencyDetectionEntailment.UrgencyDetectionEntailmentResult:
    """Detects the urgency of a message based on a set of urgency rules.

    Parameters
    ----------
    urgency_rules
        A list of urgency rules.
    message
        The message to detect the urgency of.
    metadata
        Additional metadata to pass to the LLM model.

    Returns
    -------
    UrgencyDetectionEntailment.UrgencyDetectionEntailmentResult
        The urgency detection result.
    """

    ud_entailment = UrgencyDetectionEntailment(urgency_rules=urgency_rules)
    prompt = ud_entailment.get_prompt()

    json_str = await _ask_llm_async(
        user_message=message,
        system_message=prompt,
        litellm_model=LITELLM_MODEL_URGENCY_DETECT,
        metadata=metadata,
        json=True,
    )

    try:
        parsed_json = ud_entailment.parse_json(json_str)
    except (ValidationError, ValueError) as e:
        logger.warning(f"JSON Decode failed. json_str: {json_str}. Exception: {e}")
        parsed_json = ud_entailment.default_json

    return UrgencyDetectionEntailment.UrgencyDetectionEntailmentResult(**parsed_json)
