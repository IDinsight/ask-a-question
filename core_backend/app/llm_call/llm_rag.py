"""This module contains functions for interacting with the LLM model for Retrieval
Augmented Generation (RAG).
"""

from typing import Any

from pydantic import ValidationError

from ..config import LITELLM_MODEL_GENERATION
from ..utils import setup_logger
from .llm_prompts import RAG, RAG_FAILURE_MESSAGE, ChatHistory, IdentifiedLanguage
from .utils import (
    _ask_llm_async,
    append_messages_to_chat_history,
    get_chat_response,
    remove_json_markdown,
)

logger = setup_logger("RAG")


async def get_llm_rag_answer(
    question: str,
    context: str,
    original_language: IdentifiedLanguage,
    metadata: dict | None = None,
) -> RAG:
    """Get an answer from the LLM model using RAG.

    Parameters
    ----------
    question
        The question to ask the LLM model.
    context
        The context to provide to the LLM model.
    original_language
        The original language of the question.
    metadata
        Additional metadata to provide to the LLM model.
    Returns
    -------
    RAG
        The response from the LLM model.
    """

    metadata = metadata or {}
    prompt = RAG.prompt.format(context=context, original_language=original_language)

    result = await _ask_llm_async(
        user_message=question,
        system_message=prompt,
        litellm_model=LITELLM_MODEL_GENERATION,
        metadata=metadata,
        json_=True,
    )

    result = remove_json_markdown(result)

    try:
        response = RAG.model_validate_json(result)
    except ValidationError as e:
        logger.error(f"RAG output is not a valid json: {e}")
        response = RAG(extracted_info=[], answer=result)

    return response


async def get_llm_rag_answer_with_chat_history(
    *,
    chat_history: list[dict[str, str | None]],
    chat_params: dict[str, Any],
    context: str,
    message_type: str,
    metadata: dict | None = None,
    original_language: IdentifiedLanguage,
    question: str,
    session_id: str,
) -> tuple[RAG, list[dict[str, str | None]]]:
    """Get an answer from the LLM model using RAG with chat history. The system message
    for the chat history is updated with the message type during this function call.

    Parameters
    ----------
    chat_history
        The chat history.
    chat_params
        The chat parameters.
    context
        The context to provide to the LLM model.
    message_type
        The type of the user's latest message.
    metadata
        Additional metadata to provide to the LLM model.
    original_language
        The original language of the question.
    question
        The question to ask the LLM model.
    session_id
        The session id for the chat.

    Returns
    -------
    tuple[RAG, list[dict[str, str]]
        The RAG response object and the updated chat history.
    """

    if chat_history[0]["role"] == "system":
        chat_history[0]["content"] = (
            ChatHistory.system_message_generate_response.format(
                failure_message=RAG_FAILURE_MESSAGE,
                message_type=message_type,
                original_language=original_language,
            )
        )
    content = (
        question
        + f""""\n\n
    ADDITIONAL RELEVANT INFORMATION BELOW
    =====================================

    {context}

    ADDITIONAL RELEVANT INFORMATION ABOVE
    =====================================
    """
    )
    content = await get_chat_response(
        chat_history=chat_history,
        chat_params=chat_params,
        message_params=content,
        session_id=session_id,
        json_=True,
        metadata=metadata or {},
    )
    result = remove_json_markdown(content)
    try:
        response = RAG.model_validate_json(result)
    except ValidationError as e:
        logger.error(f"RAG output is not a valid json: {e}")
        response = RAG(extracted_info=[], answer=result)

    # First pop is the assistant response.
    _, last_user_content = chat_history.pop(), chat_history.pop()

    # Revert the last user content to the original question.
    last_user_content["content"] = question
    append_messages_to_chat_history(
        chat_history=chat_history,
        messages=[
            last_user_content,
            {"content": response.answer, "name": session_id, "role": "assistant"},
        ],
        model=chat_params["model"],
        model_context_length=chat_params["max_input_tokens"],
        total_tokens_for_next_generation=chat_params["max_output_tokens"],
    )
    return response, chat_history
