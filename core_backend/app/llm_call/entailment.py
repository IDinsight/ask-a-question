from json import loads
from typing import Any, Dict

from ..config import LITELLM_MODEL_URGENCY_DETECT
from .llm_prompts import get_urgency_detection_prompt
from .utils import _ask_llm_async


async def detect_urgency(urgency_rule: str, message: str) -> Dict[str, Any]:
    """
    Detects the urgency of a message based on a given urgency rule.
    """
    prompt = get_urgency_detection_prompt(urgency_rule, message)
    json = await _ask_llm_async("", prompt, LITELLM_MODEL_URGENCY_DETECT)
    json = json.replace("```json", "").replace("```", "")
    print(json)
    return loads(json)
