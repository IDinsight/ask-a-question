"""This module contains functions for interacting with the LLM model for Retrieval
Augmented Generation (RAG).
"""

from typing import Optional

from pydantic import ValidationError

from ..config import LITELLM_MODEL_GENERATION
from ..utils import setup_logger
from .llm_prompts import RAG, IdentifiedLanguage
from .utils import _ask_llm_async, remove_json_markdown

logger = setup_logger("RAG")


async def get_llm_rag_answer(
    question: str,
    context: str,
    original_language: IdentifiedLanguage,
    metadata: Optional[dict] = None,
) -> RAG:
    """Get an answer from the LLM model using RAG.

    Parameters
    ----------
    question
        The question to ask the LLM model.
    context
        The context to provide to the LLM model.
    response_language
        The language of the response.
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
        json=True,
    )

    result = remove_json_markdown(result)

    try:
        response = RAG.model_validate_json(result)
    except ValidationError as e:
        logger.error(f"RAG output is not a valid json: {e}")
        response = RAG(extracted_info=[], answer=result)

    return response
