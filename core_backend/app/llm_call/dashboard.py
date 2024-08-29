"""
These are LLM functions used by the dashbaord.
"""

from ..config import LITELLM_MODEL_DASHBOARD_SUMMARY, LITELLM_MODEL_TOPIC_MODEL
from ..utils import create_langfuse_metadata, setup_logger
from .llm_prompts import TopicModelLabelling, get_feedback_summary_prompt
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


async def generate_topic_label(
    user_id: int,
    context: str,
    sample_texts: list[str],
) -> dict[str, str]:
    """
    Generates topic labels for example queries
    """
    metadata = create_langfuse_metadata(feature_name="topic-modeling", user_id=user_id)
    topic_model_labelling = TopicModelLabelling(context)

    combined_texts = "\n".join(
        [f"{i+1}. {text}" for i, text in enumerate(sample_texts)]
    )

    topic_json = await _ask_llm_async(
        user_message=combined_texts,
        system_message=topic_model_labelling.get_prompt(),
        litellm_model=LITELLM_MODEL_TOPIC_MODEL,
        metadata=metadata,
        json=True,
    )

    try:
        topic = topic_model_labelling.parse_json(topic_json)
    except ValueError as e:
        logger.warning(
            (
                f"Error generating topic label for {context}: {e}. "
                "Setting topic to 'Unknown'"
            )
        )
        topic = {"topic_title": "Unknown", "topic_summary": "Not available."}

    logger.info(f"Topic label generated for {context}: {topic}")
    return topic
