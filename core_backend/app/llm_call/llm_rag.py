from ..configs.llm_prompts import ANSWER_QUESTION_PROMPT
from .utils import _ask_llm


def get_llm_rag_answer(question: str, faq_data: str) -> str:
    """
    This function is used to get an answer from the LLM model.
    """

    prompt = ANSWER_QUESTION_PROMPT.format(faq=faq_data)

    return _ask_llm(question, prompt)
