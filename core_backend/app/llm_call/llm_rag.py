from ..configs.llm_prompts import ANSWER_QUESTION_PROMPT, Language
from .utils import _ask_llm_async


async def get_llm_rag_answer(
    question: str, content_text: str, response_language: Language
) -> str:
    """
    This function is used to get an answer from the LLM model.
    """

    prompt = ANSWER_QUESTION_PROMPT.format(
        content=content_text, response_language=response_language.value
    )

    return await _ask_llm_async(question, prompt)
