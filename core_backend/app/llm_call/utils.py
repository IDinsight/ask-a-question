from litellm import completion

from ..configs.app_config import LLM_ENDPOINT, LLM_MODEL
from ..utils import setup_logger

logger = setup_logger("LLM_call")


def _ask_llm(question: str, prompt: str) -> str:
    """
    This is a generic function to ask the LLM model a question.
    """

    messages = [
        {
            "content": prompt,
            "role": "system",
        },
        {
            "content": question,
            "role": "user",
        },
    ]
    logger.info(f"LLM input: 'model': {LLM_MODEL}, 'endpoint': {LLM_ENDPOINT}")
    llm_response_raw = completion(
        model=LLM_MODEL, messages=messages, temperature=0, api_base=LLM_ENDPOINT
    )
    logger.info(f"LLM output: {llm_response_raw.choices[0].message.content}")

    return llm_response_raw.choices[0].message.content
