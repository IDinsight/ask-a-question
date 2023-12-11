from litellm import completion

from ..configs.app_config import OPENAI_LLM_TYPE


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
    llm_response_raw = completion(
        model=OPENAI_LLM_TYPE, messages=messages, temperature=0
    )

    return llm_response_raw.choices[0].message.content
