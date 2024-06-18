from json import loads
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional

from ..config import LITELLM_MODEL_URGENCY_DETECT
from ..utils import setup_logger
from .llm_prompts import get_urgency_detection_prompt
from .utils import _ask_llm_async

logger = setup_logger()


async def detect_urgency(
    urgency_rules: List[str], message: str, metadata: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Detects the urgency of a message based on a set of urgency rules.
    """

    if len(urgency_rules) == 0:
        return {"is_urgent": False, "failed_rules": [], "details": {}}

    prompt = get_urgency_detection_prompt(urgency_rules)

    json = await _ask_llm_async(
        question=message,
        prompt=prompt,
        litellm_model=LITELLM_MODEL_URGENCY_DETECT,
        metadata=metadata,
    )
    json = json.replace("```json", "").replace("```", "")
    json = json.replace("\{", "{").replace("\}", "}")

    try:
        parsed = loads(json)
    except JSONDecodeError:

        logger.warning(f"JSON Decode failed: {json}")

        return {
            "best_matching_rule": "",
            "probability": 0.0,
            "reason": "JSON Decode failed",
        }
    return parsed
