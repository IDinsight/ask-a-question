"""This module contains the unit tests related to multi-turn chat for question
answering.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litellm import token_counter
from redis import asyncio as aioredis

from core_backend.app.config import LITELLM_MODEL_CHAT
from core_backend.app.llm_call.utils import (
    _ask_llm_async,
    _truncate_chat_history,
    append_message_content_to_chat_history,
    init_chat_history,
)
from core_backend.app.question_answer.routers import init_user_query_and_chat_histories
from core_backend.app.question_answer.schemas import QueryBase


async def test_init_user_query_and_chat_histories(redis_client: aioredis.Redis) -> None:
    """Test that the `QueryBase` object returned after initializing the user query
    and chat histories contains the expected attributes.

    Parameters
    ----------
    redis_client
        The Redis client instance.
    """

    query_text = "I have a stomachache."
    reset_chat_history = False
    user_query_object = QueryBase(query_text=query_text)
    assert user_query_object.generate_llm_response is False
    assert user_query_object.session_id is None

    # Mock return values
    mock_init_chat_history_return_value = (
        None,
        None,
        [{"role": "system", "content": "You are a helpful assistant."}],
        {"model": "test-model", "max_input_tokens": 1000, "max_output_tokens": 200},
    )
    mock_search_query_json_str = (
        '{"message_type": "NEW", "query": "stomachache and possible remedies"}'
    )

    with (
        patch(
            "core_backend.app.question_answer.routers.init_chat_history",
            new_callable=AsyncMock,
        ) as mock_init_chat_history,
        patch(
            "core_backend.app.question_answer.routers.get_chat_response",
            new_callable=AsyncMock,
        ) as mock_get_chat_response,
    ):
        mock_init_chat_history.return_value = mock_init_chat_history_return_value
        mock_get_chat_response.return_value = mock_search_query_json_str

        # Call the function under test
        user_query = await init_user_query_and_chat_histories(
            redis_client=redis_client,
            reset_chat_history=reset_chat_history,
            user_query=user_query_object,
        )
        chat_query_params = user_query.chat_query_params
        assert isinstance(chat_query_params, dict)

        # Check that the mocked functions were called as expected.
        mock_init_chat_history.assert_called_once_with(
            chat_cache_key=f"chatCache:{user_query.session_id}",
            chat_params_cache_key=f"chatParamsCache:{user_query.session_id}",
            redis_client=redis_client,
            reset=reset_chat_history,
            session_id=str(user_query.session_id),
        )
        mock_get_chat_response.assert_called_once()

        # After initialization, the user query object should have the following
        # attributes set correctly.
        assert user_query.generate_llm_response is True
        assert user_query.query_text == query_text
        assert (
            chat_query_params["chat_cache_key"] == f"chatCache:{user_query.session_id}"
        )
        assert chat_query_params["message_type"] == "NEW"
        assert chat_query_params["search_query"] == "stomachache and possible remedies"


async def test__ask_llm_async() -> None:
    """Test expected operation for the `_ask_llm_async` function when neither
    messages nor system message and user message is supplied.
    """

    mock_object = MagicMock()
    mock_object.llm_response_raw.choices = [MagicMock()]
    mock_object.llm_response_raw.choices[0].message.content = "FooBar"
    mock_acompletion_return_value = mock_object

    with (
        patch(
            "core_backend.app.llm_call.utils.acompletion", new_callable=AsyncMock
        ) as mock_acompletion,
    ):
        mock_acompletion.return_value = mock_acompletion_return_value

        # Call the function under test. These calls should raise an `AssertionError`
        # because the function is called either without appropriate arguments or with
        # missing arguments.
        with pytest.raises(AssertionError):
            _ = await _ask_llm_async()
            _ = await _ask_llm_async(system_message="FooBar")
            _ = await _ask_llm_async(user_message="FooBar")


def test__truncate_chat_history() -> None:
    """Test chat history truncation scenarios."""

    # Empty chat should return empty chat.
    chat_history: list[dict[str, str | None]] = []
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        total_tokens_for_next_generation=50,
    )
    assert len(chat_history) == 0

    # Non-empty chat that fits within the model context length should not be truncated.
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]

    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        total_tokens_for_next_generation=50,
    )
    assert len(chat_history) == 1
    assert chat_history[0]["content"] == "You are a helpful assistant."
    assert chat_history[0]["role"] == "system"

    # Chat history that exceeds the model context length should be truncated. In this
    # case, however, since the chat history only has a system message, the system
    # message should NOT be truncated.
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        total_tokens_for_next_generation=150,
    )
    assert len(chat_history) == 1
    assert chat_history[0]["role"] == "system"
    assert chat_history[0]["content"] == "You are a helpful assistant."

    # Exact model context length should not be truncated.
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    chat_history_tokens = token_counter(messages=chat_history, model=LITELLM_MODEL_CHAT)
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=chat_history_tokens + 1,
        total_tokens_for_next_generation=0,
    )
    assert chat_history[0]["content"] == "You are a helpful assistant."
    assert chat_history[0]["role"] == "system"

    # Check truncation of 1 message in the chat history for system-user roles.
    chat_history = [
        {
            "content": "FooBar",
            "role": "system",
        },
        {
            "content": "What is the meaning of life?",
            "role": "user",
        },
    ]
    chat_history_tokens = token_counter(messages=chat_history, model=LITELLM_MODEL_CHAT)
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=chat_history_tokens,
        total_tokens_for_next_generation=4,
    )
    assert len(chat_history) == 1 and chat_history[0]["content"] == "FooBar"

    # Check truncation of 1 message in the chat history for user-user roles.
    chat_history = [
        {
            "content": "FooBar",
            "role": "user",
        },
        {
            "content": "What is the meaning of life?",
            "role": "user",
        },
    ]
    chat_history_tokens = token_counter(messages=chat_history, model=LITELLM_MODEL_CHAT)
    _truncate_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=chat_history_tokens,
        total_tokens_for_next_generation=4,
    )
    assert (
        len(chat_history) == 1
        and chat_history[0]["content"] == "What is the meaning of life?"
    )


def test_append_message_content_to_chat_history() -> None:
    """Test appending messages to chat histories."""

    # Should have expected message appended to chat history without any truncation even
    # with truncate_history set to True.
    chat_history: list[dict[str, str | None]] = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    append_message_content_to_chat_history(
        chat_history=chat_history,
        message_content="What is the meaning of life?",
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        name="123",
        role="user",
        total_tokens_for_next_generation=50,
        truncate_history=True,
    )
    assert (
        len(chat_history) == 2
        and chat_history[1]["role"] == "user"
        and chat_history[1]["content"] == "What is the meaning of life?"
        and chat_history[1]["name"] == "123"
    )

    # Should have expected message appended to chat history without any truncation even
    # if the total tokens for next generation exceeds the model context length.
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    append_message_content_to_chat_history(
        chat_history=chat_history,
        message_content="What is the meaning of life?",
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        name="123",
        role="user",
        total_tokens_for_next_generation=150,
        truncate_history=False,
    )
    assert (
        len(chat_history) == 2
        and chat_history[1]["role"] == "user"
        and chat_history[1]["content"] == "What is the meaning of life?"
    )

    # Check that empty message content with assistant role is correctly appended.
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    append_message_content_to_chat_history(
        chat_history=chat_history,
        model=LITELLM_MODEL_CHAT,
        model_context_length=100,
        name="123",
        role="assistant",
        total_tokens_for_next_generation=150,
        truncate_history=False,
    )
    assert (
        len(chat_history) == 2
        and chat_history[1]["role"] == "assistant"
        and chat_history[1]["content"] is None
    )

    # This should fail because message content is not provided and the role is not
    # "assistant" or "function".
    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    with pytest.raises(AssertionError):
        append_message_content_to_chat_history(
            chat_history=chat_history,
            model=LITELLM_MODEL_CHAT,
            model_context_length=100,
            name="123",
            role="user",
            total_tokens_for_next_generation=150,
            truncate_history=False,
        )


async def test_init_chat_history(redis_client: aioredis.Redis) -> None:
    """Test chat history initialization.

    Parameters
    ----------
    redis_client
        The Redis client instance.
    """

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "model_name": "chat",
                "model_info": {
                    "max_input_tokens": 1000,
                    "max_output_tokens": 200,
                },
                "litellm_params": {
                    "model": "test-model",
                },
            },
        ],
    }

    with patch(
        "core_backend.app.llm_call.utils.requests.get", return_value=mock_response
    ):
        # Call the function under test
        session_id = "12345"
        (chat_cache_key, chat_params_cache_key, chat_history, old_chat_params) = (
            await init_chat_history(
                redis_client=redis_client, reset=False, session_id=session_id
            )
        )

        # Check that attributes are generated correctly and that the chat history is
        # initialized with the system message.
        assert chat_cache_key == f"chatCache:{session_id}"
        assert chat_params_cache_key == f"chatParamsCache:{session_id}"
        assert chat_history == [
            {
                "content": "You are a helpful assistant.",
                "name": session_id,
                "role": "system",
            }
        ]
        assert isinstance(old_chat_params, dict)
        assert all(
            x in old_chat_params
            for x in ["max_input_tokens", "max_output_tokens", "model"]
        )

        # Check that initialization with reset=False does not clear existing chat
        # history.
        altered_chat_history = chat_history + [
            {
                "content": "What is the meaning of life?",
                "name": session_id,
                "role": "user",
            }
        ]
        await redis_client.set(chat_cache_key, json.dumps(altered_chat_history))
        _, _, new_chat_history, new_chat_params = await init_chat_history(
            redis_client=redis_client, reset=False, session_id=session_id
        )
        assert new_chat_history == [
            {
                "content": "You are a helpful assistant.",
                "name": session_id,
                "role": "system",
            },
            {
                "content": "What is the meaning of life?",
                "name": session_id,
                "role": "user",
            },
        ]

    # Check that initialization with reset=True clears existing chat history.
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "model_name": "chat",
                "model_info": {
                    "max_input_tokens": 1000,
                    "max_output_tokens": 200,
                },
                "litellm_params": {
                    "model": "test-model",
                },
            },
        ],
    }
    with patch(
        "core_backend.app.llm_call.utils.requests.get", return_value=mock_response
    ):
        _, _, reset_chat_history, new_chat_params = await init_chat_history(
            redis_client=redis_client, reset=True, session_id=session_id
        )
        assert reset_chat_history == [
            {
                "content": "You are a helpful assistant.",
                "name": session_id,
                "role": "system",
            }
        ]
