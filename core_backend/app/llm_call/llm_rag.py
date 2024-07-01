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
    response_language: IdentifiedLanguage,
    metadata: Optional[dict] = None,
) -> RAG:
    """
    This function is used to get an answer from the LLM model.
    """

    if metadata is None:
        metadata = {}

    prompt = RAG.prompt.format(context=context)

    result = await _ask_llm_async(
        question=question,
        prompt=prompt,
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
