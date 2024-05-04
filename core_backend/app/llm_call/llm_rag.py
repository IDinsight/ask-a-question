from ..config import LITELLM_MODEL_SUMMARIZATION
from .llm_prompts import ANSWER_QUESTION_PROMPT, IdentifiedLanguage
from .utils import _ask_llm_async


async def get_llm_rag_answer(
    question: str, context: str, response_language: IdentifiedLanguage
) -> str:
    """
    This function is used to get an answer from the LLM model.
    """

    prompt = ANSWER_QUESTION_PROMPT.format(
        content=context, response_language=response_language.value
    )

    return await _ask_llm_async(
        question=question,
        prompt=prompt,
        litellm_model=LITELLM_MODEL_SUMMARIZATION,
    )
