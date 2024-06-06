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
        model=litellm_model,
        messages=messages,
        temperature=0,
        api_base=litellm_endpoint,
        api_key=LITELLM_API_KEY,
        metadata={"generation_name": litellm_model},
        # override default safety settings for gemini
        safety_settings=[
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ],
    )
    logger.info(f"LLM output: {llm_response_raw.choices[0].message.content}")

    return llm_response_raw.choices[0].message.content
