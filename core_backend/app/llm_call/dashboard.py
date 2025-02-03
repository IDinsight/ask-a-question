"""
These are LLM functions used by the dashboard.
"""

from bertopic import BERTopic

from ..config import LITELLM_MODEL_DASHBOARD_SUMMARY, LITELLM_MODEL_TOPIC_MODEL
from ..dashboard.config import DISABLE_DASHBOARD_LLM
from ..utils import create_langfuse_metadata, setup_logger
from .llm_prompts import TopicModelLabelling, get_feedback_summary_prompt
from .utils import _ask_llm_async

logger = setup_logger("DASHBOARD AI SUMMARY")


async def generate_ai_summary(
    user_id: int,
    content_title: str,
    content_text: str,
    feedback: list[str],
) -> str | None:
    """
    Generates AI summary for Page 2 of the dashboard.
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
    topic_id: int,
    user_id: int,
    context: str,
    sample_texts: list[str],
    topic_model: BERTopic,
) -> dict[str, str]:
    """
    Generates topic labels for example queries.
    """
    if topic_id == -1:
        return {"topic_title": "Unclassified", "topic_summary": "Not available."}

    if DISABLE_DASHBOARD_LLM:
        logger.info("LLM functionality is disabled. Generating labels using KeyBERT.")
        # Use KeyBERT-inspired method to generate topic labels
        # Assume topic_model is provided
        topic_info = topic_model.get_topic(topic_id)
        if not topic_info:
            logger.warning(f"No topic info found for topic_id {topic_id}.")
            return {"topic_title": "Unknown", "topic_summary": "Not available."}

        # Extract top keywords
        top_keywords = [word for word, _ in topic_info]
        topic_title = ", ".join(top_keywords[:3])  # Use top 3 keywords as title
        # Use all keywords as summary
        # Line formatting looks odd since 'pre-wrap' is enabled on the frontend
        topic_summary = f"""{" ".join(top_keywords)}

Hint: To enable full AI summaries please set the DASHBOARD_LLM environment variable to "True" in your configuration."""  # noqa: E501
        logger.info(
            f"Generated topic label for topic_id {topic_id} using basic keywords."
        )
        return {"topic_title": topic_title, "topic_summary": topic_summary}

    # If LLM is enabled, proceed with LLM-based label generation
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
        json_=True,
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
