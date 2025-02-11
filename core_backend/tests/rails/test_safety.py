"""This module contains tests for the safety classification functionality."""

from pathlib import Path

import pytest

from core_backend.app.llm_call.llm_prompts import SafetyClassification
from core_backend.app.llm_call.process_input import _classify_safety
from core_backend.app.question_answer.schemas import (
    ErrorType,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
)

pytestmark = pytest.mark.rails


PROMPT_INJECTION_FILE = "data/prompt_injection_data.txt"
SAFE_MESSAGES_FILE = "data/safe_data.txt"
INAPPROPRIATE_LANGUAGE_FILE = "data/inappropriate_lang.txt"


def read_test_data(file: str) -> list[str]:
    """Reads test data from file and returns a list of strings."""

    file_path = Path(__file__).parent / file

    with open(file_path, encoding="utf-8") as f:
        return f.read().splitlines()


@pytest.fixture
def response() -> QueryResponse:
    """Returns a dummy response."""

    return QueryResponse(
        feedback_secret_key="feedback-string",
        llm_response="Dummy response",
        query_id=1,
        search_results=None,
        session_id=None,
    )


@pytest.mark.parametrize("prompt_injection", read_test_data(PROMPT_INJECTION_FILE))
async def test_prompt_injection_found(
    prompt_injection: str, response: QueryResponse
) -> None:
    """Tests that prompt injection is found."""

    question = QueryRefined(
        generate_llm_response=False,
        generate_tts=False,
        query_text=prompt_injection,
        query_text_original=prompt_injection,
        workspace_id=124,
    )
    _, response = await _classify_safety(query_refined=question, response=response)
    assert isinstance(response, QueryResponseError)
    assert response.error_type == ErrorType.QUERY_UNSAFE
    assert (
        response.debug_info["safety_classification"]
        == SafetyClassification.PROMPT_INJECTION.value
    )


@pytest.mark.parametrize("safe_text", read_test_data(SAFE_MESSAGES_FILE))
async def test_safe_message(safe_text: str, response: QueryResponse) -> None:
    """Tests that safe messages are classified as safe."""

    question = QueryRefined(
        generate_llm_response=False,
        generate_tts=False,
        query_text=safe_text,
        query_text_original=safe_text,
        workspace_id=124,
    )
    _, response = await _classify_safety(query_refined=question, response=response)

    assert isinstance(response, QueryResponse)
    assert (
        response.debug_info["safety_classification"] == SafetyClassification.SAFE.value
    )


@pytest.mark.parametrize(
    "inappropriate_text", read_test_data(INAPPROPRIATE_LANGUAGE_FILE)
)
async def test_inappropriate_language(
    inappropriate_text: str, response: QueryResponse
) -> None:
    """Tests that inappropriate language is found."""

    question = QueryRefined(
        generate_llm_response=False,
        generate_tts=False,
        query_text=inappropriate_text,
        query_text_original=inappropriate_text,
        workspace_id=124,
    )
    _, response = await _classify_safety(query_refined=question, response=response)

    assert isinstance(response, QueryResponseError)
    assert response.error_type == ErrorType.QUERY_UNSAFE
    assert (
        response.debug_info["safety_classification"]
        == SafetyClassification.INAPPROPRIATE_LANGUAGE.value
    )
