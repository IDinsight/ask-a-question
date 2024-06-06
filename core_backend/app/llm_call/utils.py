from typing import Optional

from litellm import acompletion

from ..config import LITELLM_API_KEY, LITELLM_ENDPOINT, LITELLM_MODEL_DEFAULT
from ..utils import setup_logger

logger = setup_logger("LLM_call")


async def _ask_llm_async(
    question: str,
    prompt: str,
    litellm_model: Optional[str] = LITELLM_MODEL_DEFAULT,
    litellm_endpoint: Optional[str] = LITELLM_ENDPOINT,
    metadata: Optional[dict] = None,
) -> str:
    """
    This is a generic function to ask the LLM model a question.
    """
    if metadata is not None:
        metadata["generation_name"] = litellm_model

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
        model=litellm_model,
        messages=messages,
        temperature=0,
        api_base=litellm_endpoint,
        api_key=LITELLM_API_KEY,
        metadata=metadata,
    )
    logger.info(f"LLM output: {llm_response_raw.choices[0].message.content}")

    return llm_response_raw.choices[0].message.content
