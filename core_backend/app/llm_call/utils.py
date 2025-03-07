"""This module contains utility functions related to LLM calls."""

import json
from typing import Any, Optional

import redis.asyncio as aioredis
import requests  # type: ignore
from litellm import acompletion, token_counter

from ..config import (
    LITELLM_API_KEY,
    LITELLM_ENDPOINT,
    LITELLM_MODEL_CHAT,
    LITELLM_MODEL_DEFAULT,
    REDIS_CHAT_CACHE_EXPIRY_TIME,
)
from ..utils import setup_logger

logger = setup_logger(name="LLM_call")


async def _ask_llm_async(
    *,
    json_: bool = False,
    litellm_endpoint: str | None = LITELLM_ENDPOINT,
    litellm_model: str | None = LITELLM_MODEL_DEFAULT,
    llm_generation_params: Optional[dict[str, Any]] = None,
    messages: Optional[list[dict[str, str | None]]] = None,
    metadata: dict | None = None,
    system_message: Optional[str] = None,
    user_message: Optional[str] = None,
) -> str:
    """This is a generic function to send an LLM call to a model provider using
    `litellm`.

    Parameters
    ----------
    json_
        Specifies whether the response should be returned as a JSON object.
    litellm_endpoint
        The litellm endpoint.
    litellm_model
        The name of the LLM model for the `litellm` proxy server.
    llm_generation_params
        The LLM generation parameters. If `None`, then a default set of parameters will
        be used.
    messages
        List of dictionaries containing the messages. Each dictionary must contain the
        keys `content` and `role` at a minimum. If `None`, then `user_message` and
        `system_message` must be provided.
    metadata
        Dictionary containing additional metadata for the `litellm` LLM call.
    system_message
        The system message. If `None`, then `messages` must be provided.
    user_message
        The user message. If `None`, then `messages` must be provided.

    Returns
    -------
    str
        The appropriate response from the LLM model.
    """

    if metadata is not None:
        metadata["generation_name"] = litellm_model

    extra_kwargs = {}
    if json_:
        extra_kwargs["response_format"] = {"type": "json_object"}

    if not messages:
        assert isinstance(user_message, str) and isinstance(system_message, str)
        messages = [
            {"content": system_message, "role": "system"},
            {"content": user_message, "role": "user"},
        ]

    llm_generation_params = llm_generation_params or {
        "max_tokens": 1024,
        "temperature": 0,
    }

    logger.info(f"LLM input: 'model': {litellm_model}, 'endpoint': {litellm_endpoint}")

    try:
        llm_response_raw = await acompletion(
            model=litellm_model,
            messages=messages,
            api_base=litellm_endpoint,
            api_key=LITELLM_API_KEY,
            metadata=metadata,
            **extra_kwargs,
            **llm_generation_params,
        )
    except Exception as err:
        logger.error("Error calling the LLM", exc_info=True)
        raise LLMCallException(f"Error during LLM call: {err}") from err

    # Optionally check if the returned response contains an error field
    if hasattr(llm_response_raw, "error") and llm_response_raw.error:
        error_msg = getattr(llm_response_raw, "error", "Unknown error")
        logger.error(f"LLM call returned an error: {error_msg}")
        raise LLMCallException(f"LLM call returned an error: {error_msg}")

    # Ensure that the response has valid content
    try:
        content = llm_response_raw.choices[0].message.content
    except (AttributeError, IndexError) as e:
        logger.error("LLM response structure is not as expected", exc_info=True)
        raise LLMCallException("LLM response structure is not as expected") from e

    logger.info(f"LLM output: {content}")
    return content


class LLMCallException(Exception):
    """Custom exception for LLM call errors."""

    pass


def _truncate_chat_history(
    *,
    chat_history: list[dict[str, str | None]],
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
        f"Truncating earlier chat messages for next generation.\n"
        f"Model context length: {model_context_length}\n"
        f"Total tokens so far: {chat_history_tokens}\n"
        f"Total tokens requested for next generation: "
        f"{total_tokens_for_next_generation}"
    )
    index = 1 if chat_history[0]["role"] == "system" else 0
    while remaining_tokens <= 0 and chat_history:
        index = min(len(chat_history) - 1, index)
        last_message = chat_history.pop(index)
        chat_history_tokens -= token_counter(messages=[last_message], model=model)
        remaining_tokens = model_context_length - (
            chat_history_tokens + total_tokens_for_next_generation
        )
        if remaining_tokens <= 0 and not chat_history:
            chat_history.append(last_message)
            break
    if not chat_history:
        logger.warning("Empty chat history after truncating chat messages!")


def append_message_content_to_chat_history(
    *,
    chat_history: list[dict[str, str | None]],
    message_content: Optional[str] = None,
    model: str,
    model_context_length: int,
    name: str,
    role: str,
    total_tokens_for_next_generation: int,
    truncate_history: bool = True,
) -> None:
    """Append a single message content to the chat history.

    Parameters
    ----------
    chat_history
        The chat history buffer.
    message_content
        The contents of the message. `message_content` is required for all messages,
        and may be null for assistant messages with function calls.
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
    truncate_history
        Specifies whether to truncate the chat history. Truncation is done after all
        messages are appended to the chat history.
    """

    roles = ["assistant", "function", "system", "user"]
    assert len(name) <= 64, f"`name` must be <= 64 characters: {name}"
    assert role in roles, f"Invalid role: {role}. Valid roles are: {roles}"
    if role not in ["assistant", "function"]:
        assert (
            message_content is not None
        ), "`message_content` can only be `None` for `assistant` and `function` roles."
    message = {"content": message_content, "name": name, "role": role}
    chat_history.append(message)
    if truncate_history:
        _truncate_chat_history(
            chat_history=chat_history,
            model=model,
            model_context_length=model_context_length,
            total_tokens_for_next_generation=total_tokens_for_next_generation,
        )


def append_messages_to_chat_history(
    *,
    chat_history: list[dict[str, str | None]],
    messages: dict[str, str | None] | list[dict[str, str | None]],
    model: str,
    model_context_length: int,
    total_tokens_for_next_generation: int,
) -> None:
    """Append a list of messages to the chat history. Truncation is done after all
    messages are appended to the chat history.

    Parameters
    ----------
    chat_history
        The chat history buffer.
    messages
        A list of messages to be appended to the chat history. The order of the
        messages in the list is the order in which they are appended to the chat
        history.
    model
        The name of the LLM model.
    model_context_length
        The maximum number of tokens allowed for the model. This is the context window
        length for the model (i.e, maximum number of input + output tokens).
    total_tokens_for_next_generation
        The total number of tokens during text generation.
    """

    if not isinstance(messages, list):
        messages = [messages]
    for message in messages:
        name = message.get("name", None)
        role = message.get("role", None)
        assert name and role
        append_message_content_to_chat_history(
            chat_history=chat_history,
            message_content=message.get("content", None),
            model=model,
            model_context_length=model_context_length,
            name=name,
            role=role,
            total_tokens_for_next_generation=total_tokens_for_next_generation,
            truncate_history=False,
        )
    _truncate_chat_history(
        chat_history=chat_history,
        model=model,
        model_context_length=model_context_length,
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
    chat_history: Optional[list[dict[str, str | None]]] = None,
    chat_params: dict[str, Any],
    message_params: str | dict[str, Any],
    session_id: str,
    **kwargs: Any,
) -> str:
    """Get the appropriate chat response.

    Parameters
    ----------
    chat_history
        The chat history buffer.
    chat_params
        Dictionary containing the chat parameters.
    message_params
        Dictionary containing the message parameters or a string containing the message
        itself. If a dictionary, then the dictionary must contain the key `prompt` and,
        optionally, the key `prompt_kws`. `prompt` contains the prompt for the LLM. If
        `prompt_kws` is specified, then it is a dictionary whose <key, value> pairs
        will be used to string format `prompt`.
    session_id
        The session ID for the chat.
    kwargs
        Additional keyword arguments for `_ask_llm_async`.

    Returns
    -------
    str
        The appropriate response from the LLM model.
    """

    chat_history = chat_history or []
    model = chat_params["model"]
    model_context_length = chat_params["max_input_tokens"]
    total_tokens_for_next_generation = chat_params["max_output_tokens"]

    if isinstance(message_params, str):
        message_params = {"prompt": message_params}
    prompt_kws = message_params.get("prompt_kws", None)
    formatted_prompt = format_prompt(
        prompt=message_params["prompt"], prompt_kws=prompt_kws
    )

    append_message_content_to_chat_history(
        chat_history=chat_history,
        message_content=formatted_prompt,
        model=model,
        model_context_length=model_context_length,
        name=session_id,
        role="user",
        total_tokens_for_next_generation=total_tokens_for_next_generation,
    )
    message_content = await _ask_llm_async(
        litellm_model=LITELLM_MODEL_CHAT,
        llm_generation_params={
            "frequency_penalty": 0.0,
            "max_tokens": total_tokens_for_next_generation,
            "n": 1,
            "presence_penalty": 0.0,
            "temperature": 0.7,
            "top_p": 0.9,
        },
        messages=chat_history,
        **kwargs,
    )
    append_message_content_to_chat_history(
        chat_history=chat_history,
        message_content=message_content,
        model=model,
        model_context_length=model_context_length,
        name=session_id,
        role="assistant",
        total_tokens_for_next_generation=total_tokens_for_next_generation,
    )

    return message_content


async def init_chat_history(
    *,
    chat_cache_key: Optional[str] = None,
    chat_params_cache_key: Optional[str] = None,
    redis_client: aioredis.Redis,
    reset: bool,
    session_id: str,
    system_message: str = "You are a helpful assistant.",
) -> tuple[str, str, list[dict[str, str | None]], dict[str, Any]]:
    """Initialize the chat history. Chat history initialization involves initializing
    both the chat parameters **and** the chat history for the session. Chat parameters
    are assumed to be static for a given session.

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
        The session ID for the chat.
    system_message
        The system message to be added to the beginning of the chat history.

    Returns
    -------
    tuple[str, str, list[dict[str, str]], dict[str, Any]]
        The chat cache key, the chat parameters cache key, the chat history, and the
        chat parameters.
    """

    # Get the chat history and chat parameters for the session.
    chat_cache_key = chat_cache_key or f"chatCache:{session_id}"
    chat_params_cache_key = chat_params_cache_key or f"chatParamsCache:{session_id}"

    logger.info(f"Using chat cache ID: {chat_cache_key}")
    logger.info(f"Using chat params cache ID: {chat_params_cache_key}")

    chat_cache_exists = await redis_client.exists(chat_cache_key)
    chat_params_cache_exists = await redis_client.exists(chat_params_cache_key)
    chat_history = (
        json.loads(await redis_client.get(chat_cache_key)) if chat_cache_exists else []
    )
    chat_params = (
        json.loads(await redis_client.get(chat_params_cache_key))
        if chat_params_cache_exists
        else {}
    )

    if chat_history and chat_params and reset is False:
        logger.info(
            f"Chat history and chat parameters are already initialized for session: "
            f"{session_id}. Using existing values."
        )
        return chat_cache_key, chat_params_cache_key, chat_history, chat_params

    # Get the chat parameters for the session.
    logger.info(f"Initializing chat parameters for session: {session_id}")
    model_info_endpoint = LITELLM_ENDPOINT.rstrip("/") + "/model/info"
    model_info = requests.get(
        model_info_endpoint, headers={"accept": "application/json"}, timeout=600
    ).json()
    for dict_ in model_info["data"]:
        if dict_["model_name"] == "chat":
            chat_params = dict_["model_info"]
            assert "model" not in chat_params
            chat_params["model"] = dict_["litellm_params"]["model"]
            await redis_client.set(
                chat_params_cache_key,
                json.dumps(chat_params),
                ex=REDIS_CHAT_CACHE_EXPIRY_TIME,
            )
            break
    logger.info(f"Finished initializing chat parameters for session: {session_id}")

    logger.info(f"Initializing chat history for session: {session_id}")
    chat_params = json.loads(await redis_client.get(chat_params_cache_key))
    assert isinstance(chat_params, dict) and chat_params, f"{chat_params = }"
    chat_history = []
    append_message_content_to_chat_history(
        chat_history=chat_history,
        message_content=system_message,
        model=chat_params["model"],
        model_context_length=chat_params["max_input_tokens"],
        name=session_id,
        role="system",
        total_tokens_for_next_generation=chat_params["max_output_tokens"],
    )
    await redis_client.set(
        chat_cache_key, json.dumps(chat_history), ex=REDIS_CHAT_CACHE_EXPIRY_TIME
    )
    logger.info(f"Finished initializing chat history for session: {session_id}")
    return chat_cache_key, chat_params_cache_key, chat_history, chat_params


def log_chat_history(
    *, chat_history: list[dict[str, str | None]], context: Optional[str] = None
) -> None:
    """Log the chat history.

    Parameters
    ----------
    chat_history
        The chat history to log. If `None`, then the chat history is retrieved from the
        Redis cache using `chat_cache_key`.
    context
        Optional string that denotes the context in which the chat history is being
        logged. Useful to keep track of the call chain execution.
    """

    if context:
        logger.info(f"\n###Chat history: {context}###")
    else:
        logger.info("\n###Chat history###")
    for message in chat_history:
        role, content = message["role"], message.get("content", None)
        name = message.get("name", "")
        function_call = message.get("function_call", None)
        if role in ["system", "user"]:
            logger.info(f"\n{role}:\n{content}\n")
        elif role == "assistant":
            logger.info(f"\n{role}:\n{function_call or content}\n")
        else:
            logger.info(f"\n{role}:\n({name}): {content}\n")


def remove_json_markdown(*, text: str) -> str:
    """Remove json markdown from text.

    Parameters
    ----------
    text
        The text containing the json markdown.

    Returns
    -------
    str
        The text with the json markdown removed.
    """

    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.removeprefix("```json").removesuffix("```")
    text = text.replace(r"\{", "{").replace(r"\}", "}")
    return text.strip()


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
    logger.info(f"Finished resetting chat history for session: {session_id}")
