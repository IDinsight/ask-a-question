"""This module contains the unit tests related to multi-turn chat for question
answering.
"""

import json

import pytest
from litellm import token_counter
from redis import asyncio as aioredis

from core_backend.app.config import LITELLM_MODEL_CHAT
from core_backend.app.llm_call.llm_prompts import IdentifiedLanguage
from core_backend.app.llm_call.llm_rag import get_llm_rag_answer_with_chat_history
from core_backend.app.llm_call.utils import (
    _ask_llm_async,
    _truncate_chat_history,
    append_content_to_chat_history,
    init_chat_history,
    remove_json_markdown,
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
    user_query = await init_user_query_and_chat_histories(
        redis_client=redis_client,
        reset_chat_history=reset_chat_history,
        user_query=QueryBase(query_text=query_text),
    )
    chat_query_params = user_query.chat_query_params
    assert isinstance(chat_query_params, dict) and chat_query_params

    chat_history = chat_query_params["chat_history"]
    search_query = chat_query_params["search_query"]
    session_id = chat_query_params["session_id"]

    assert isinstance(chat_history, list) and len(chat_history) == 1
    assert isinstance(session_id, str)
    assert user_query.generate_llm_response is True
    assert user_query.query_text == query_text
    assert chat_query_params["chat_cache_key"] == f"chatCache:{session_id}"
    assert chat_query_params["message_type"] == "NEW"
    assert search_query and search_query != query_text


async def test_get_llm_rag_answer_with_chat_history() -> None:
    """Test correct chat history for NEW message type."""

    session_id = "70284693"
    chat_history: list[dict[str, str | None]] = [
        {
            "content": "You are a helpful assistant.",
            "name": session_id,
            "role": "system",
        }
    ]
    chat_params = {
        "max_tokens": 8192,
        "max_input_tokens": 2097152,
        "max_output_tokens": 8192,
        "litellm_provider": "vertex_ai-language-models",
        "mode": "chat",
        "model": "vertex_ai/gemini-1.5-pro",
    }
    context = "0. Heartburn in pregnancy\n*Ways to manage heartburn in pregnancy*\r\n\r\nIndigestion (heartburn) ❤️\u200d🔥 is common in pregnancy. Heartburn happens due to hormones and the growing baby pressing on your stomach. You may feel gassy and bloated, bring up food, experience nausea or a pain in the chest. \r\n\r\n*What to do*\r\n- Drink peppermint tea ☕ (pour boiled water over fresh or dried mint leaves) to manage indigestion. \r\n- Wear loose-fitting clothes 👚 to feel more comfortable. \r\n\r\n*Prevent indigestion*\r\n- Rather than 3 large meals daily, eat small meals more often.                                                                                                        \r\n- Sit up straight when you eat and eat slowly. \r\n- Don't lie down directly after eating.\r\n- Avoid acidic, sugary, spicy 🌶️ or fatty foods and caffeine. \r\n- Don't smoke or drink alcohol 🍷 (these can cause indigestion and harm your baby).\n\n1. Backache in pregnancy\n*Ways to manage back pain during pregnancy*\r\n\r\nPain or aching 💢 in the back is common during pregnancy. Throughout your pregnancy the hormone relaxin is released. This hormone relaxes the tissue that holds your bones in place in the pelvic area. This allows your baby to pass through you birth canal easier during delivery. These changes together with the added weight of your womb can cause discomfort 😓 during the third trimester. \r\n\r\n*What to do*\r\n- Place a hot water bottle 🌡️ or ice pack 🧊 on the painful area. \r\n- When you sit, use a chair with good back support 🪑, and sit with both feet on the floor. \r\n- Get regular exercise🚶🏽\u200d♀️and stretch afterwards. \r\n- Wear low-heeled 👢(but not flat ) shoes with good arch support. \r\n- To sleep better 😴, lie on your side and place a pillow between your legs, with the top leg on the pillow. \r\n\r\nIf the pain doesn't go away or you have other symptoms, visit the clinic.\r\n\r\nTap the link below for:\r\n*More info about Relaxin:\r\nhttps://www.yourhormones.info/hormones/relaxin/\n\n2. Danger signs in pregnancy\n*Danger signs to visit the clinic right away*\r\n\r\nPlease go to the clinic straight away if you experience any of these symptoms: \r\n\r\n*Pain*\r\n- Pain in your stomach, swelling of your legs🦵🏽or feet 🦶🏽 that does not go down overnight, \r\n-  fever, or vomiting along with pain and fever 🤒,\r\n- pain when you urinate 🚽, \r\n- a headache 🤕 and you can't see properly (blurred vision), \r\n- lower back pain 💢 especially if it's a new feeling,\r\n- lower back pain or 6 contractions❗within 1 hour before 37 weeks (even if not sore).\r\n\r\n*Movement*\r\n- A noticeable change in movement or your baby stops moving after five months. \r\n\r\n*Body changes*\r\n- Vomiting and a sudden swelling of your face, hands or feet, \r\n- A change in vaginal discharge – becoming watery, mucous-like or bloody,\r\n- Bleeding or spotting.\r\n\r\n*Injury and illness*\r\n- An abdominal injury like a fall or a car accident,\r\n- COVID-19 exposure or symptoms 😷,\r\n- Any health problem that gets worse, even if not directly related to pregnancy (like asthma).\n\n3. Piles (sore anus) in pregnancy\n*Fresh food helps to avoid piles*\r\n\r\nPiles (or haemorrhoids) are swollen veins in your bottom (anus). They are common during pregnancy. Pressure from your growing belly 🤰🏽 and increased blood flow to the pelvic area are the cause. Piles can be itchy, stick out or even bleed. You may be able to feel them as small, soft lumps inside or around the edge or ring of your bottom. You may see blood 🩸 after you pass a stool. Constipation can make piles worse. \r\n\r\n*What to do*\r\n- Eat lots of fruit 🍎 and vegetables 🥦 and drink lots of water to prevent constipation,\r\n- Eat food that is high in fibre – like brown bread 🍞, long grain rice and oats,\r\n- Ask a nurse/midwife about safe topical treatment creams 🧴 to relieve the pain, \r\n\r\n*Reasons to go to the clinic* 🏥\r\n- If the pain or bleeding continues."  # noqa: E501
    message_type = "NEW"
    original_language = IdentifiedLanguage.ENGLISH
    question = "i have a stomachache."
    _, new_chat_history = await get_llm_rag_answer_with_chat_history(
        chat_history=chat_history,
        chat_params=chat_params,
        context=context,
        message_type=message_type,
        original_language=original_language,
        question=question,
        session_id=session_id,
    )
    assert len(new_chat_history) == 3
    assert new_chat_history[0]["role"] == "system"
    assert new_chat_history[1]["role"] == "user"
    assert new_chat_history[2]["role"] == "assistant"
    assert new_chat_history[0]["content"] != "You are a helpful assistant."
    assert new_chat_history[1]["content"] == question


async def test__ask_llm_async() -> None:
    """Test expected operation for the `_ask_llm_async` function."""

    chat_history: list[dict[str, str | None]] = [
        {
            "content": "You are a helpful assistant.",
            "name": "123",
            "role": "system",
        },
        {
            "content": "What is the meaning of life?",
            "name": "123",
            "role": "user",
        },
    ]
    content = await _ask_llm_async(messages=chat_history)
    assert isinstance(content, str) and content

    content = await _ask_llm_async(
        user_message="What is the meaning of life?",
        system_message="You are a helpful assistant.",
    )
    assert isinstance(content, str) and content

    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "name": "123",
            "role": "system",
        },
        {
            "content": 'What is the meaning of life? Respond with a JSON dictionary with the key "answer".',  # noqa: E501
            "name": "123",
            "role": "user",
        },
    ]
    content = await _ask_llm_async(json_=True, messages=chat_history)
    content_dict = json.loads(remove_json_markdown(content))
    assert isinstance(content_dict, dict) and "answer" in content_dict


async def test__ask_llm_async_assertion_error() -> None:
    """Test expected operation for the `_ask_llm_async` function when neither
    messages nor system message and user message is supplied.
    """

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
    assert len(chat_history) == 0

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


def test_append_content_to_chat_history() -> None:
    """Test appending messages to chat histories."""

    chat_history: list[dict[str, str | None]] = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    append_content_to_chat_history(
        chat_history=chat_history,
        content="What is the meaning of life?",
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
    )

    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    append_content_to_chat_history(
        chat_history=chat_history,
        content="What is the meaning of life?",
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

    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    append_content_to_chat_history(
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

    chat_history = [
        {
            "content": "You are a helpful assistant.",
            "role": "system",
        }
    ]
    with pytest.raises(AssertionError):
        append_content_to_chat_history(
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

    # First initialization.
    session_id = "12345"
    (chat_cache_key, chat_params_cache_key, chat_history, old_chat_params) = (
        await init_chat_history(
            redis_client=redis_client, reset=False, session_id=session_id
        )
    )
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
        x in old_chat_params for x in ["max_input_tokens", "max_output_tokens", "model"]
    )

    altered_chat_history = chat_history + [
        {"content": "What is the meaning of life?", "name": session_id, "role": "user"}
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
