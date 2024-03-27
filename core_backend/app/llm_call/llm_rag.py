from ..config import LITELLM_ENDPOINT_SUMMARIZATION, LITELLM_MODEL_SUMMARIZATION
from .llm_prompts import ANSWER_QUESTION_PROMPT
from .utils import _ask_llm_async


async def get_llm_rag_answer(question: str, faq_data: str) -> str:
    """
    This function is used to get an answer from the LLM model.
    """

    prompt = ANSWER_QUESTION_PROMPT.format(content=faq_data)

    return await _ask_llm_async(
        question,
        prompt,
        litellm_model=LITELLM_MODEL_SUMMARIZATION,
        litellm_endpoint=LITELLM_ENDPOINT_SUMMARIZATION,
    )
