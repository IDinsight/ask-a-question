from json import loads
from typing import Any, Dict, Optional

from ..config import LITELLM_MODEL_URGENCY_DETECT
from .llm_prompts import get_urgency_detection_prompt
from .utils import _ask_llm_async


async def detect_urgency(
    urgency_rule: str, message: str, metadata: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Detects the urgency of a message based on a given urgency rule.
    """
    if metadata is None:
        metadata = {}
    prompt = get_urgency_detection_prompt(urgency_rule, message)
    json = await _ask_llm_async(
        question="",
        prompt=prompt,
        litellm_model=LITELLM_MODEL_URGENCY_DETECT,
        metadata=metadata,
    )
    json = json.replace("```json", "").replace("```", "")
    return loads(json)
