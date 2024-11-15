"""This module contains utility functions related to LLM calls."""

import json
import re
from textwrap import dedent
from typing import Any, Optional

import redis.asyncio as aioredis
import requests
from litellm import acompletion, token_counter
from termcolor import colored

from ..config import (
    LITELLM_ENDPOINT,
    LITELLM_MODEL_DEFAULT,
)
from ..utils import generate_random_int32, setup_logger

logger = setup_logger("LLM_call")


async def _ask_llm_async(
    user_message: Optional[str] = None,
    system_message: Optional[str] = None,
    messages: Optional[list[dict[str, str]]] = None,
    litellm_model: str | None = LITELLM_MODEL_DEFAULT,
    litellm_endpoint: str | None = LITELLM_ENDPOINT,
    metadata: dict | None = None,
    json: bool = False,
    llm_generation_params: Optional[dict[str, Any]] = None,
) -> str:
    """This is a generic function to send an LLM call to a model provider using
    `litellm`.

    Parameters
    ----------
    user_message
        The user message. If `None`, then `messages` must be provided.
    system_message
        The system message. If `None`, then `messages` must be provided.
    messages
        List of dictionaries containing the messages. Each dictionary must contain the
        keys `content` and `role` at a minimum. If `None`, then `user_message` and
        `system_message` must be provided.
    litellm_model
        The name of the LLM model for the `litellm` proxy server.
    litellm_endpoint
        The litellm endpoint.
    metadata
        Dictionary containing additional metadata for the `litellm` LLM call.
    json
        Specifies whether the response should be returned as a JSON object.
    llm_generation_params
        The LLM generation parameters. If `None`, then a default set of parameters will
        be used.

    Returns
    -------
    str
        The appropriate response from the LLM model.
    """

    if metadata is not None:
        metadata["generation_name"] = litellm_model

    extra_kwargs = {}
    if json:
        extra_kwargs["response_format"] = {"type": "json_object"}

    if not messages:
        assert isinstance(user_message, str) and isinstance(system_message, str)
        messages = [
            {
                "content": system_message,
                "role": "system",
            },
            {
                "content": user_message,
                "role": "user",
            },
        ]
    llm_generation_params = llm_generation_params or {
        "max_tokens": 1024,
        "temperature": 0,
    }

    logger.info(f"LLM input: 'model': {litellm_model}, 'endpoint': {litellm_endpoint}")

    llm_response_raw = await acompletion(
        model=litellm_model,
        messages=messages,
        # api_base=litellm_endpoint,
        # api_key=LITELLM_API_KEY,
        metadata=metadata,
        **extra_kwargs,
        **llm_generation_params,
    )
    logger.info(f"LLM output: {llm_response_raw.choices[0].message.content}")
    return llm_response_raw.choices[0].message.content


async def _get_chat_response(
    *,
    chat_cache_key: str,
    chat_history: list[dict[str, str]],
    chat_params: dict[str, Any],
    original_message_params: dict[str, Any],
    redis_client: aioredis.Redis,
    session_id: str,
    use_zero_shot_cot: bool = False,
) -> str:
    """Get the appropriate response and update the chat history. This method also wraps
    potential Zero-Shot CoT calls.

    Parameters
    ----------
    chat_cache_key
        The chat cache key.
    chat_history
        The chat history buffer.
    chat_params
        Dictionary containing the chat parameters.
    original_message_params
        Dictionary containing the original message parameters.
    redis_client
        The Redis client.
    session_id
        The session ID for the chat.
    use_zero_shot_cot
        Specifies whether to use Zero-Shot CoT to answer the query.

    Returns
    -------
    str
        The appropriate chat response.
    """

    if use_zero_shot_cot:
        original_message_params["prompt"] += "\n\nLet's think step by step."

    prompt = format_prompt(
        prompt=original_message_params["prompt"],
        prompt_kws=original_message_params.get("prompt_kws", None),
    )
    chat_history = append_message_to_chat_history(
        chat_history=chat_history,
        content=prompt,
        model=chat_params["model"],
        model_context_length=chat_params["max_input_tokens"],
        name=session_id,
        role="user",
        total_tokens_for_next_generation=chat_params["max_output_tokens"],
    )
    content = await _ask_llm_async(
        # litellm_model=LITELLM_MODEL_CHAT,
        litellm_model="gpt-4o-mini",
        llm_generation_params={
            "frequency_penalty": 0.0,
            "max_tokens": chat_params["max_output_tokens"],
            "n": 1,
            "presence_penalty": 0.0,
            "temperature": 0.7,
            "top_p": 0.9,
        },
        messages=chat_history,
    )
    chat_history = append_message_to_chat_history(
        chat_history=chat_history,
        message={"content": content, "role": "assistant"},
        model=chat_params["model"],
        model_context_length=chat_params["max_input_tokens"],
        total_tokens_for_next_generation=chat_params["max_output_tokens"],
    )

    await redis_client.set(chat_cache_key, json.dumps(chat_history))
    return content


def _truncate_chat_history(
    *,
    chat_history: list[dict[str, str]],
    model: str,
    model_context_length: int,
    total_tokens_for_next_generation: int,
) -> None:
    """Truncate the chat history if necessary. This process removes older messages past
    the total token limit of the model (but maintains the initial system message if
    any) and effectively mimics an infinite chat buffer.

    NB: This process does not reset or summarize the chat history. Reset and
    summarization are done explicitly. Instead, this function should be invoked each
    time a message is appended to the chat history.

    Parameters
    ----------
    chat_history
        The chat history buffer.
    model
        The name of the LLM model.
    model_context_length
        The maximum number of tokens allowed for the model. This is the context window
        length for the model (i.e, maximum number of input + output tokens).
    total_tokens_for_next_generation
        The total number of tokens used during ext generation.
    """

    chat_history_tokens = token_counter(messages=chat_history, model=model)
    remaining_tokens = model_context_length - (
        chat_history_tokens + total_tokens_for_next_generation
    )
    if remaining_tokens > 0:
        return
    logger.warning(
        f"Truncating chat history for next generation.\n"
        f"Model context length: {model_context_length}\n"
        f"Total tokens so far: {chat_history_tokens}\n"
        f"Total tokens requested for next generation: "
        f"{total_tokens_for_next_generation}"
    )
    index = 1 if chat_history[0].get("role", None) == "system" else 0
    while remaining_tokens <= 0 and chat_history:
        index = min(len(chat_history) - 1, index)
        chat_history_tokens -= token_counter(
            messages=[chat_history.pop(index)], model=model
        )
        remaining_tokens = model_context_length - (
            chat_history_tokens + total_tokens_for_next_generation
        )
    if not chat_history:
        logger.warning("Empty chat history after truncating chat buffer!")


def append_message_to_chat_history(
    *,
    chat_history: list[dict[str, str]],
    content: Optional[str] = "",
    message: Optional[dict[str, Any]] = None,
    model: str,
    model_context_length: int,
    name: Optional[str] = None,
    role: Optional[str] = None,
    total_tokens_for_next_generation: int,
) -> list[dict[str, str]]:
    """Append a message to the chat history.

    Parameters
    ----------
    chat_history
        The chat history buffer.
    content
        The contents of the message. `content` is required for all messages, and may be
        null for assistant messages with function calls.
    message
        If provided, this dictionary will be appended to the chat history instead of
        constructing one using the other arguments.
    model
        The name of the LLM model.
    model_context_length
        The maximum number of tokens allowed for the model. This is the context window
        length for the model (i.e, maximum number of input + output tokens).
    name
        The name of the author of this message. `name` is required if role is
        `function`, and it should be the name of the function whose response is in
        the content. May contain a-z, A-Z, 0-9, and underscores, with a maximum length
        of 64 characters.
    role
        The role of the messages author.
    total_tokens_for_next_generation
        The total number of tokens during text generation.

    Returns
    -------
    list[dict[str, str]]
        The chat history buffer with the message appended.
    """

    roles = ["assistant", "function", "system", "user"]
    if not message:
        assert name, "`name` is required if `message` is `None`."
        assert len(name) <= 64, f"`name` must be <= 64 characters: {name}"
        assert role in roles, f"Invalid role: {role}. Valid roles are: {roles}"
        message = {"content": content, "name": name, "role": role}
    chat_history.append(message)
    _truncate_chat_history(
        chat_history=chat_history,
        model=model,
        model_context_length=model_context_length,
        total_tokens_for_next_generation=total_tokens_for_next_generation,
    )
    return chat_history


def append_system_message_to_chat_history(
    *,
    chat_history: Optional[list[dict[str, str]]] = None,
    model: str,
    model_context_length: int,
    session_id: str,
    total_tokens_for_next_generation: int,
) -> list[dict[str, str]]:
    """Append the system message to the chat history.

    Parameters
    ----------
    chat_history
        The chat history buffer.
    model
        The name of the LLM model.
    model_context_length
        The maximum number of tokens allowed for the model. This is the context window
        length for the model (i.e, maximum number of input + output tokens).
    session_id
        The session ID for the chat.
    total_tokens_for_next_generation
        The total number of tokens during text generation.

    Returns
    -------
    list[dict[str, str]]
        The chat history buffer with the system message appended.
    """

    chat_history = chat_history or []
    system_message = dedent(
        """You are an AI assistant designed to help expecting and new mothers with
        their questions/concerns related to prenatal and newborn care. You interact
        with mothers via a chat interface.

        For each message from a mother, follow these steps:

        1. Determine the Type of Message:
            - Follow-up Message: These are messages that build upon the conversation so
            far and/or seeks more information on a previously discussed
            question/concern.
            - Clarification Message: These are messages that seek to clarify something
            that was previously mentioned in the conversation.
            - New Message: These are messages that introduce a new topic that was not
            previously discussed in the conversation.

        2. Obtain More Information to Help Address the Message:
            - Keep in mind the context given by the conversation history thus far.
            - Use the conversation history and the Type of Message to formulate a
            precise query to execute against a vector database that contains
            information relevant to the current message.
            - Ensure the query is specific and accurately reflects the mother's
            information needs.
            - Use specific keywords that captures the semantic meaning of the mother's
            information needs.

        Output the vector database query between the tags <Query> and </Query>, without
        any additional text.
        """
    )
    return append_message_to_chat_history(
        chat_history=chat_history,
        content=system_message,
        model=model,
        model_context_length=model_context_length,
        name=session_id,
        role="system",
        total_tokens_for_next_generation=total_tokens_for_next_generation,
    )


def format_prompt(
    *,
    prompt: str,
    prompt_kws: Optional[dict[str, Any]] = None,
    remove_leading_blank_spaces: bool = True,
) -> str:
    """Format prompt.

    Parameters
    ----------
    prompt
        String denoting the prompt.
    prompt_kws
        If not `None`, then a dictionary containing <key, value> pairs of parameters to
        use for formatting `prompt`.
    remove_leading_blank_spaces
        Specifies whether to remove leading blank spaces from the prompt.

    Returns
    -------
    str
        The formatted prompt.
    """

    if remove_leading_blank_spaces:
        prompt = "\n".join([m.lstrip() for m in prompt.split("\n")])
    return prompt.format(**prompt_kws) if prompt_kws else prompt


async def get_chat_response(
    *,
    chat_cache_key: Optional[str] = None,
    chat_params_cache_key: Optional[str] = None,
    original_message_params: str | dict[str, Any],
    redis_client: aioredis.Redis,
    session_id: str,
    use_zero_shot_cot: bool = False,
) -> str:
    """Get the appropriate chat response.

    Parameters
    ----------
    chat_cache_key
        The chat cache key. If `None`, then the key is constructed using the session ID.
    chat_params_cache_key
        The chat parameters cache key. If `None`, then the key is constructed using the
        session ID.
    original_message_params
        Dictionary containing the original message parameters or a string containing
        the message itself. If a dictionary, then the dictionary must contain the key
        `prompt` and, optionally, the key `prompt_kws`. `prompt` contains the prompt
        for the LLM. If `prompt_kws` is specified, then it is a dictionary whose
        <key, value> pairs will be used to string format `prompt`.
    redis_client
        The Redis client.
    session_id
        The session ID for the chat.
    use_zero_shot_cot
        Specifies whether to use Zero-Shot CoT to answer the query.

    Returns
    -------
    str
        The appropriate chat response.
    """

    (chat_cache_key, chat_params_cache_key, chat_history, session_id) = (
        await init_chat_history(
            chat_cache_key=chat_cache_key,
            chat_params_cache_key=chat_params_cache_key,
            redis_client=redis_client,
            reset=False,
            session_id=session_id,
        )
    )
    assert (
        isinstance(chat_history, list) and chat_history
    ), f"Empty chat history for session: {session_id}"

    if isinstance(original_message_params, str):
        original_message_params = {"prompt": original_message_params}
    prompt_kws = original_message_params.get("prompt_kws", None)
    formatted_prompt = format_prompt(
        prompt=original_message_params["prompt"], prompt_kws=prompt_kws
    )

    return await _get_chat_response(
        chat_cache_key=chat_cache_key,
        chat_history=chat_history,
        chat_params=json.loads(await redis_client.get(chat_params_cache_key)),
        original_message_params={"prompt": formatted_prompt},
        redis_client=redis_client,
        session_id=session_id,
        use_zero_shot_cot=use_zero_shot_cot,
    )


async def init_chat_history(
    *,
    chat_cache_key: Optional[str] = None,
    chat_params_cache_key: Optional[str] = None,
    redis_client: aioredis.Redis,
    reset: bool,
    session_id: Optional[str] = None,
) -> tuple[str, str, list[dict[str, str]], str]:
    """Initialize the chat history. Chat history initialization involves initializing
    both the chat parameters **and** the chat history for the session. Thus, chat
    parameters are assumed to be constant for a given session.

    Parameters
    ----------
    chat_cache_key
        The chat cache key. If `None`, then the key is constructed using the session ID.
    chat_params_cache_key
        The chat parameters cache key. If `None`, then the key is constructed using the
        session ID.
    redis_client
        The Redis client.
    reset
        Specifies whether to reset the chat history prior to initialization. If `True`,
        the chat history is completed cleared and reinitialized. If `False` **and** the
        chat history is previously initialized, then the existing chat history will be
        used.
    session_id
        The session ID for the chat. If `None`, then a randomly generated session ID
        will be used.

    Returns
    -------
    tuple[str, str, list[dict[str, Any]], str]
        The chat cache key, chat parameters cache key, chat history, and session ID.
    """

    session_id = session_id or str(generate_random_int32())

    # Get the chat parameters for the session from the LLM model info endpoint or the
    # Redis cache.
    chat_params_cache_key = chat_params_cache_key or f"chatParamsCache:{session_id}"
    chat_params_exists = await redis_client.exists(chat_params_cache_key)
    if not chat_params_exists:
        model_info_endpoint = LITELLM_ENDPOINT.rstrip("/") + "/model/info"
        model_info = requests.get(
            model_info_endpoint, headers={"accept": "application/json"}
        ).json()
        for dict_ in model_info["data"]:
            if dict_["model_name"] == "chat":
                chat_params = dict_["model_info"]
                assert "model" not in chat_params
                chat_params["model"] = dict_["litellm_params"]["model"]
                await redis_client.set(chat_params_cache_key, json.dumps(chat_params))
                break

    # Get the chat history for the session from the Redis cache.
    chat_cache_key = chat_cache_key or f"chatCache:{session_id}"
    chat_cache_exists = await redis_client.exists(chat_cache_key)
    chat_history = (
        json.loads(await redis_client.get(chat_cache_key)) if chat_cache_exists else []
    )

    if chat_history and reset is False:
        logger.info(
            f"Chat history is already initialized for session: {session_id}. Using "
            f"existing chat history."
        )
        return chat_cache_key, chat_params_cache_key, chat_history, session_id

    logger.info(f"Initializing chat history for session: {session_id}")
    assert not chat_history or reset is True, (
        f"Non-empty chat history during initialization: {chat_history}\n"
        f"Set 'reset' to `True` to initialize chat history."
    )
    chat_params = json.loads(await redis_client.get(chat_params_cache_key))
    assert isinstance(chat_params, dict) and chat_params

    chat_history = append_system_message_to_chat_history(
        model=chat_params["model"],
        model_context_length=chat_params["max_input_tokens"],
        session_id=session_id,
        total_tokens_for_next_generation=chat_params["max_output_tokens"],
    )
    await redis_client.set(session_id, json.dumps(chat_history))
    logger.info(f"Finished initializing chat history for session: {session_id}")
    return chat_cache_key, chat_params_cache_key, chat_history, session_id


async def log_chat_history(
    *,
    chat_cache_key: Optional[str] = None,
    context: Optional[str] = None,
    redis_client: aioredis.Redis,
    session_id: str,
) -> None:
    """Log the chat history.

    Parameters
    ----------
    chat_cache_key
        The chat cache key. If `None`, then the key is constructed using the session ID.
    context
        Optional string that denotes the context in which the chat history is being
        logged. Useful to keep track of the call chain execution.
    redis_client
        The Redis client.
    session_id
        The session ID for the chat.
    """

    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
    }

    if context:
        logger.info(f"\n###Chat history for session {session_id}: {context}###")
    else:
        logger.info(f"\n###Chat history for session {session_id}###")
    chat_cache_key = chat_cache_key or f"chatCache:{session_id}"
    chat_cache_exists = await redis_client.exists(chat_cache_key)
    chat_history = (
        json.loads(await redis_client.get(chat_cache_key)) if chat_cache_exists else []
    )
    for message in chat_history:
        role, content = message["role"], message["content"]
        name = message.get("name", session_id)
        function_call = message.get("function_call", None)
        role_color = role_to_color[role]
        if role in ["system", "user"]:
            logger.info(colored(f"\n{role}:\n{content}\n", role_color))
        elif role == "assistant":
            logger.info(colored(f"\n{role}:\n{function_call or content}\n", role_color))
        elif role == "function":
            logger.info(colored(f"\n{role}:\n({name}): {content}\n", role_color))


def remove_json_markdown(text: str) -> str:
    """Remove json markdown from text."""

    json_str = text.removeprefix("```json").removesuffix("```").strip()
    json_str = json_str.replace("\{", "{").replace("\}", "}")

    return json_str


async def reset_chat_history(
    *,
    chat_cache_key: Optional[str] = None,
    redis_client: aioredis.Redis,
    session_id: str,
) -> None:
    """Reset the chat history.

    Parameters
    ----------
    chat_cache_key
        The chat cache key. If `None`, then the key is constructed using the session ID.
    redis_client
        The Redis client.
    session_id
        The session ID for the chat.
    """

    logger.info(f"Resetting chat history for session: {session_id}")
    chat_cache_key = chat_cache_key or f"chatCache:{session_id}"
    await redis_client.delete(chat_cache_key)


def strip_tags(*, tag: str, text: str) -> list[str]:
    """Remove tags from `text`.

    Parameters
    ----------
    tag
        The tag to be stripped.
    text
        The input text.

    Returns
    -------
    list[str]
        text: The stripped text.
    """

    assert tag
    matches = re.findall(rf"<{tag}>\s*([\s\S]*?)\s*</{tag}>", text)
    return matches if matches else [text]
