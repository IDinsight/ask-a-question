from typing import Optional

from litellm import acompletion

from ..config import LITELLM_ENDPOINT_DEFAULT, LITELLM_MODEL_DEFAULT
from ..utils import setup_logger

logger = setup_logger("LLM_call")


async def _ask_llm_async(
    question: str,
    prompt: str,
    litellm_model: Optional[str] = LITELLM_MODEL_DEFAULT,
    litellm_endpoint: Optional[str] = LITELLM_ENDPOINT_DEFAULT,
) -> str:
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
    logger.info(f"LLM input: 'model': {litellm_model}, 'endpoint': {litellm_endpoint}")
    llm_response_raw = await acompletion(
        model=litellm_model, messages=messages, temperature=0, api_base=litellm_endpoint
    )
    logger.info(f"LLM output: {llm_response_raw.choices[0].message.content}")

    return llm_response_raw.choices[0].message.content
