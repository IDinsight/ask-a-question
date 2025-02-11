"""This module contains LLM functions for the dashboard."""

from bertopic import BERTopic

from ..config import LITELLM_MODEL_DASHBOARD_SUMMARY, LITELLM_MODEL_TOPIC_MODEL
from ..dashboard.config import DISABLE_DASHBOARD_LLM
from ..utils import create_langfuse_metadata, setup_logger
from .llm_prompts import TopicModelLabelling, get_feedback_summary_prompt
from .utils import _ask_llm_async

logger = setup_logger(name="DASHBOARD AI SUMMARY")


async def generate_ai_summary(
    *, content_text: str, content_title: str, feedback: list[str], workspace_id: int
) -> str:
    """Generate AI summary for Page 2 of the dashboard.

    Parameters
    ----------
    content_text
        The text of the content to summarize.
    content_title
        The title of the content to summarize.
    feedback
        The user feedback to provide to the AI.
    workspace_id
        The workspace ID.

    Returns
    -------
    str
        The AI summary.
    """

    metadata = create_langfuse_metadata(
        feature_name="dashboard", workspace_id=workspace_id
    )
    ai_feedback_summary_prompt = get_feedback_summary_prompt(
        content=content_text, content_title=content_title
    )

    ai_summary = await _ask_llm_async(
        litellm_model=LITELLM_MODEL_DASHBOARD_SUMMARY,
        metadata=metadata,
        system_message=ai_feedback_summary_prompt,
        user_message="\n".join(feedback),
    )

    logger.info(f"AI Summary generated for {content_title} with feedback: {feedback}")
    return ai_summary


async def generate_topic_label(
    *,
    context: str,
    sample_texts: list[str],
    topic_id: int,
    topic_model: BERTopic,
    workspace_id: int,
) -> dict[str, str]:
    """Generate topic labels for example queries.

    Parameters
    ----------
    context
        The context of the topic label.
    sample_texts
        The sample texts to use for generating the topic label.
    topic_id
        The topic ID.
    topic_model
        The topic model object.
    workspace_id
        The workspace ID.

    Returns
    -------
    dict[str, str]
        The topic label.
    """

    if topic_id == -1:
        return {"topic_title": "Unclassified", "topic_summary": "Not available."}

    if DISABLE_DASHBOARD_LLM:
        logger.info("LLM functionality is disabled. Generating labels using KeyBERT.")

        # Use KeyBERT-inspired method to generate topic labels.
        # Assume topic_model is provided.
        topic_info = topic_model.get_topic(topic_id)
        if not topic_info:
            logger.warning(f"No topic info found for topic_id {topic_id}.")
            return {"topic_title": "Unknown", "topic_summary": "Not available."}

        # Extract top keywords.
        top_keywords = [word for word, _ in topic_info]
        topic_title = ", ".join(top_keywords[:3])  # Use top 3 keywords as title

        # Use all keywords as summary.
        # Line formatting looks odd since 'pre-wrap' is enabled on the frontend.
        topic_summary = f"""{" ".join(top_keywords)}

Hint: To enable full AI summaries please set the DASHBOARD_LLM environment variable to "True" in your configuration."""  # noqa: E501
        logger.info(
            f"Generated topic label for topic_id {topic_id} using basic keywords."
        )
        return {"topic_title": topic_title, "topic_summary": topic_summary}

    # If LLM is enabled, proceed with LLM-based label generation.
    metadata = create_langfuse_metadata(
        feature_name="topic-modeling", workspace_id=workspace_id
    )
    topic_model_labelling = TopicModelLabelling(context=context)

    combined_texts = "\n".join(
        [f"{i}. {text}" for i, text in enumerate(sample_texts, 1)]
    )

    topic_json = await _ask_llm_async(
        json_=True,
        litellm_model=LITELLM_MODEL_TOPIC_MODEL,
        metadata=metadata,
        system_message=topic_model_labelling.get_prompt(),
        user_message=combined_texts,
    )

    try:
        topic = topic_model_labelling.parse_json(json_str=topic_json)
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
