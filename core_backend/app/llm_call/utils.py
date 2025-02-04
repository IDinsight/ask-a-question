<<<<<<< Updated upstream
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
=======
import json
import uuid
from copy import deepcopy
from typing import Any, Optional

import redis.asyncio as aioredis

from litellm import acompletion, model_cost, token_counter
from termcolor import colored

from .playbooks import ConversationPlayBook
from ..config import LITELLM_API_KEY, LITELLM_ENDPOINT, LITELLM_MODEL_DEFAULT, LITELLM_MODEL_GENERATION
from ..utils import setup_logger


logger = setup_logger("LLM_call")
>>>>>>> Stashed changes


ROLE_TO_COLOR = {  # For message logging purposes
    "system": "red",
    "user": "green",
    "assistant": "blue",
    "function": "magenta",
}
ROLES = ["assistant", "function", "system", "user"]


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
        api_base=litellm_endpoint,
        api_key=LITELLM_API_KEY,
        metadata=metadata,
        **extra_kwargs,
        **llm_generation_params,
    )
    logger.info(f"LLM output: {llm_response_raw.choices[0].message.content}")
    return llm_response_raw.choices[0].message.content


<<<<<<< Updated upstream
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
=======
async def _get_response(
    *,
    client: aioredis.Redis,
    conversation_history: list[dict[str, str]],
    original_message_params: dict[str, Any],
    session_id: str,
    text_generation_params: dict[str, Any],
    use_zero_shot_cot: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """Get the appropriate response and update the conversation history. This method
    also wraps potential Zero-Shot CoT calls.

    Parameters
    ----------
    client
        The Redis client.
    conversation_history
        The conversation history buffer.
    original_message_params
        Dictionary containing the original message parameters.
    session_id
        The session ID for the conversation.
    text_generation_params
        Dictionary containing text generation parameters.
    use_zero_shot_cot
        Specifies whether to use Zero-Shot CoT to answer the query.
    kwargs
        Additional keyword arguments.

    Returns
    -------
    dict[str, Any]
        The appropriate response.
    """

    if use_zero_shot_cot:
        original_message_params["prompt"] += (
            "\n\n" + ConversationPlayBook.prompts["cot"]
        )

    prompt = format_prompt(
        prompt=original_message_params["prompt"],
        prompt_kws=original_message_params.get("prompt_kws", None),
    )
    conversation_history = append_message_to_conversation_history(
        content=prompt,
        conversation_history=conversation_history,
        model=text_generation_params["model"],
        name=session_id,
        role="user",
        total_tokens_for_next_generation=text_generation_params["max_tokens"],
    )
    response = await get_completion(
        is_async=True,
        messages=conversation_history,
        text_generation_params=text_generation_params,
        **kwargs,
    )
    assert isinstance(response, dict)

    # Only append the first message to the conversation history.
    conversation_history = append_message_to_conversation_history(
        conversation_history=conversation_history,
        message=response["choices"][0]["message"],
        model=text_generation_params["model"],
        total_tokens_for_next_generation=text_generation_params["max_tokens"],
    )
    await client.set(session_id, json.dumps(conversation_history))
    return response


def _truncate_conversation_history(
    *,
    conversation_history: list[dict[str, str]],
    model: str,
    total_tokens_for_next_generation: int,
) -> None:
    """Truncate the conversation history if necessary. This process removes older
    messages past the total token limit of the model (but maintains the initial system
    message if any) and effectively mimics an infinite conversation buffer.

    NB: This process does not reset or summarize the conversation history. Reset and
    summarization are done explicitly. Instead, this function should be invoked each
    time a message is appended to the conversation history.

    Parameters
    ----------
    conversation_history
        The conversation history buffer.
    model
        The name of the LLM model.
    total_tokens_for_next_generation
        The total number of tokens used during ext generation.
    """

    conversation_history_tokens = token_counter(
        messages=conversation_history, model=model
    )
    model_context_length = model_cost[model]["max_input_tokens"]
    remaining_tokens = model_context_length - (
        conversation_history_tokens + total_tokens_for_next_generation
    )
    if remaining_tokens > 0:
        return
    logger.warning(
        f"Truncating conversation history for next generation.\n"
        f"Model context length: {model_context_length}\n"
        f"Total tokens so far: {conversation_history_tokens}\n"
        f"Total tokens requested for next generation: "
        f"{total_tokens_for_next_generation}"
    )
    index = 1 if conversation_history[0].get("role", None) == "system" else 0
    while remaining_tokens <= 0 and conversation_history:
        index = min(len(conversation_history) - 1, index)
        conversation_history_tokens -= token_counter(
            messages=[conversation_history.pop(index)], model=model
        )
        remaining_tokens = model_context_length - (
            conversation_history_tokens + total_tokens_for_next_generation
        )
    if not conversation_history:
        logger.warning(
            "Empty conversation history after truncating conversation buffer!"
        )


def append_message_to_conversation_history(
    *,
    content: Optional[str] = "",
    conversation_history: list[dict[str, str]],
    message: Optional[dict[str, Any]] = None,
    model: str,
    name: Optional[str] = None,
    role: Optional[str] = None,
    total_tokens_for_next_generation: int,
) -> list[dict[str, str]]:
    """Append a message to the conversation history.

    Parameters
    ----------
    content
        The contents of the message. `content` is required for all messages, and may be
        null for assistant messages with function calls.
    conversation_history
        The conversation history buffer.
    message
        If provided, this dictionary will be appended to the conversation history
        instead of constructing one using the other arguments.
    model
        The name of the LLM model.
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
        The conversation history buffer with the message appended.
    """

    if not message:
        assert name, f"`name` is required if `message` is `None`."
        assert len(name) <= 64, f"`name` must be <= 64 characters: {name}"
        assert role in ROLES, f"Invalid role: {role}. Valid roles are: {ROLES}"
        message = {"content": content, "name": name, "role": role}
    conversation_history.append(message)
    _truncate_conversation_history(
        conversation_history=conversation_history,
        model=model,
        total_tokens_for_next_generation=total_tokens_for_next_generation,
    )
    return conversation_history


def append_system_message_to_conversation_history(
    *,
    conversation_history: Optional[list[dict[str, str]]] = None,
    model: str,
    session_id: str,
    total_tokens_for_next_generation: int,
) -> list[dict[str, str]]:
    """Append the system message to the conversation history.

    Parameters
    ----------
    conversation_history
        The conversation history buffer.
    model
        The name of the LLM model.
    session_id
        The session ID for the conversation.
    total_tokens_for_next_generation
        The total number of tokens during text generation.

    Returns
    -------
    list[dict[str, str]]
        The conversation history buffer with the system message appended.
    """

    conversation_history = conversation_history or []
    system_message = format_prompt(
        prompt=ConversationPlayBook.system_messages.momconnect
    )
    return append_message_to_conversation_history(
        content=system_message,
        conversation_history=conversation_history,
        model=model,
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


async def get_response(
    *,
    original_message_params: dict[str, Any],
    redis_client: aioredis.Redis,
    session_id: str,
    text_generation_params: dict[str, Any],
    use_zero_shot_cot: bool = False,
) -> dict[str, Any]:
    """Get the appropriate response.

    Parameters
    ----------
    original_message_params
        Dictionary containing the original message parameters. This dictionary must
        contain the key `prompt` and, optionally, the key `prompt_kws`. `prompt`
        contains the prompt for the LLM. If `prompt_kws` is specified, then it is a
        dictionary whose <key, value> pairs will be used to string format `prompt`.
    redis_client
        The Redis client.
    session_id
        The session ID for the conversation.
    text_generation_params
        Dictionary containing text generation parameters.
    use_zero_shot_cot
        Specifies whether to use Zero-Shot CoT to answer the query.

    Returns
    -------
    dict[str, Any]
        The appropriate response.
    """

    conversation_history = await init_conversation_history(
        redis_client=redis_client, reset=False, session_id=session_id
    )
    assert conversation_history, f"Empty conversation history for session: {session_id}"

    prompt_kws = original_message_params.get("prompt_kws", None)
    formatted_prompt = format_prompt(
        prompt=original_message_params["prompt"], prompt_kws=prompt_kws
    )

    return await _get_response(
        conversation_history=conversation_history,
        fallback_to_longer_context_model=fallback_to_longer_context_model,
        fallbacks=fallbacks,
        original_message_params={"prompt": formatted_prompt},
        redis_client=redis_client,
        session_id=session_id,
        text_generation_params=text_generation_params,
        trim_ratio=trim_ratio,
        use_zero_shot_cot=use_zero_shot_cot,
    )


async def init_conversation_history(
    *,
    litellm_endpoint: str | None = LITELLM_ENDPOINT,
    litellm_model: str | None = LITELLM_MODEL_GENERATION,
    redis_client: aioredis.Redis,
    reset: bool,
    session_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Initialize the conversation history.

    Parameters
    ----------
    litellm_endpoint
        The litellm LLM endpoint.
    litellm_model
        The litellm LLM model.
    redis_client
        The Redis client.
    reset
        Specifies whether to reset the conversation history prior to initialization. If
        `True`, the conversation history is completed cleared and reinitialized. If
        `False` **and** the conversation history is previously initialized, then the
        existing conversation history will be used.
    session_id
        The session ID for the conversation.

    Returns
    -------
    list[dict[str, Any]]
        The conversation history.
    """

    # Specify text generation parameters.
    text_generation_params = {
        "frequency_penalty": 0.0,
        # "max_tokens": min(model_cost[litellm_model]["max_output_tokens"], 4096),
        "max_tokens": min(model_cost["gpt-4o-mini"]["max_output_tokens"], 4096),
        # "model": litellm_model,
        "model": "gpt-4o-mini",
        "n": 1,
        "presence_penalty": 0.0,
        "temperature": 0.7,
        "top_p": 0.9,
    }

    # Get the conversation history from the Redis cache. NB: The conversation history
    # cache is referenced as "conversationCache:<session_id>".
    session_id = session_id or str(uuid.uuid4())
    if not session_id.startswith("conversationCache:"):
        session_id = f"conversationCache:{session_id}"
    session_exists = await redis_client.exists(session_id)
    conversation_history = (
        json.loads(await redis_client.get(session_id)) if session_exists else []
    )

    # Session exists and reset is False --> we just return the existing conversation
    # history.
    if session_exists and reset is False:
        logger.info(
            f"Conversation history is already initialized for session: {session_id}\n"
            f"Using existing conversation history."
        )
        return conversation_history

    # Either session does not exist or reset is True --> we initialize the conversation
    # history for the session and cache in Redis.
    logger.info(f"Initializing conversation history for session: {session_id}")
    assert not conversation_history or reset is True, (
        f"Non-empty conversation history during initialization: "
        f"{conversation_history}\nSet 'reset' to `True` to initialize conversation "
        f"history."
    )
    conversation_history = append_system_message_to_conversation_history(
        model=text_generation_params["model"],
        session_id=session_id,
        total_tokens_for_next_generation=text_generation_params["max_tokens"],
    )
    await redis_client.set(session_id, json.dumps(conversation_history))
    return conversation_history


async def log_conversation_history(
    *, context: Optional[str] = None, redis_client: aioredis.Redis, session_id: str
) -> None:
    """Log the conversation history.

    Parameters
    ----------
    context
        Optional string that denotes the context in which the conversation history is
        being logged. Useful to keep track of the call chain execution.
    redis_client
        The Redis client.
    session_id
        The session ID for the conversation.
    """

    if context:
        logger.info(f"\n###Conversation history for session {session_id}: {context}###")
    else:
        logger.info(f"\n###Conversation history for session {session_id}###")
    session_exists = await redis_client.exists(session_id)
    conversation_history = (
        json.loads(await redis_client.get(session_id)) if session_exists else []
    )
    for message in conversation_history:
        role, content = message["role"], message["content"]
        name = message.get("name", session_id)
        function_call = message.get("function_call", None)
        role_color = ROLE_TO_COLOR[role]
        if role in ["system", "user"]:
            logger.info(colored(f"\n{role}:\n{content}\n", role_color))
        elif role == "assistant":
            logger.info(colored(f"\n{role}:\n{function_call or content}\n", role_color))
        elif role == "function":
            logger.info(colored(f"\n{role}:\n({name}): {content}\n", role_color))


def remove_json_markdown(text: str) -> str:
    """Remove json markdown from text."""
>>>>>>> Stashed changes

    NB: This process does not reset or summarize the chat history. Reset and
    summarization are done explicitly. Instead, this function should be invoked each
    time a message is appended to the chat history.

<<<<<<< Updated upstream
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
=======
    return json_str


async def reset_conversation_history(
    *, redis_client: aioredis.Redis, session_id: str
) -> None:
    """Reset the conversation history.

    Parameters
    ----------
    redis_client
        The Redis client.
    session_id
        The session ID for the conversation.
    """

    logger.info(f"Resetting conversation history for session: {session_id}")
    await redis_client.delete(session_id)


async def summarize_conversation_history(
    *,
    redis_client: aioredis.Redis,
    session_id: str,
    text_generation_params: dict[str, Any],
) -> list[Any]:
    """Summarize and update the conversation history.

    Parameters
    ----------
    redis_client
        The Redis client.
    session_id
        The session ID for the conversation.
    text_generation_params
        Dictionary containing text generation parameters.

    Returns
    -------
    list[Any]
        The conversation history.
    """

    session_exists = await redis_client.exists(session_id)
    conversation_history = (
        json.loads(await redis_client.get(session_id)) if session_exists else []
    )

    if not conversation_history:
        logger.warning("No messages to summarize in the conversation history!")
        return conversation_history

    summary_index = 1 if conversation_history[0].get("role", None) == "system" else 0
    if len(conversation_history) <= summary_index:
        logger.warning(
            "The existing conversation history does not contain any messages to "
            "summarize!"
        )
        return conversation_history

    # Create the prompt for summarizing the conversation.
    conversation = ""
    for message in conversation_history[summary_index:]:
        role = message.get("role", "N/A")
        content = message.get("content", "")
        conversation += f"Role: {role}\tContent: {content}\n\n"
    assert conversation, (
        f"Got empty conversation for summarization!\n"
        f"{summary_index = }\n"
        f"{conversation_history = }"
    )

    # Invoke the LLM to summarize the conversation.
    messages = [
        {
            "content": format_prompt(
                prompt=ConversationPlayBook.prompts.summarize_conversation,
                prompt_kws={"conversation": conversation},
            ),
            "role": "user",
        }
    ]
    text_generation_params = deepcopy(text_generation_params)
    text_generation_params["n"] = 1
    response = await get_completion(
        fallback_to_longer_context_model=True,
        is_async=True,
        messages=messages,
        text_generation_params=text_generation_params,
    )
    assert isinstance(response, dict)
    summary_content = response["choices"][0]["message"]["content"]
    logger.debug(f"Summary of conversation history: {summary_content}")

    # Update the conversation history with the summary.
    system_message = conversation_history.pop(0) if summary_index == 1 else {}
    conversation_history = []
    if system_message:
        conversation_history = append_message_to_conversation_history(
            conversation_history=conversation_history,
            message=system_message,
            model=text_generation_params["model"],
            total_tokens_for_next_generation=text_generation_params["max_tokens"],
        )
    conversation_history = append_message_to_conversation_history(
        content=f"The following is a summary of the conversation so far:\n\n{summary_content}",  # noqa: E501
        conversation_history=conversation_history,
        model=text_generation_params["model"],
        name=session_id,
        role="user",
        total_tokens_for_next_generation=text_generation_params["max_tokens"],
    )
    await redis_client.set(session_id, json.dumps(conversation_history))
    return conversation_history
>>>>>>> Stashed changes
