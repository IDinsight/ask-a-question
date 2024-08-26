"""
These are LLM functions used by the dashbaord.
"""

from ..config import LITELLM_MODEL_DASHBOARD_SUMMARY
from ..utils import create_langfuse_metadata, setup_logger
from .llm_prompts import get_feedback_summary_prompt
from .utils import _ask_llm_async

logger = setup_logger("DASHBOARD AI SUMMARY")


async def generate_ai_summary(
    user_id: int,
    content_title: str,
    content_text: str,
    feedback: list[str],
) -> str:
    """
    Generates AI summary for the dashboard.
    """
    metadata = create_langfuse_metadata(feature_name="dashboard", user_id=user_id)
    ai_feedback_summary_prompt = get_feedback_summary_prompt(
        content_title, content_text
    )

    ai_summary = await _ask_llm_async(
        user_message="\n".join(feedback),
        system_message=ai_feedback_summary_prompt,
        litellm_model=LITELLM_MODEL_DASHBOARD_SUMMARY,
        metadata=metadata,
    )

    logger.info(f"AI Summary generated for {content_title} with feedback: {feedback}")
    return ai_summary
