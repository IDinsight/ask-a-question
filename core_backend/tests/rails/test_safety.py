import pytest

from core_backend.app.configs.llm_prompts import SafetyClassification
from core_backend.app.llm_call.parse_input import _classify_safety
from core_backend.app.schemas import ResultState, UserQueryRefined, UserQueryResponse

pytestmark = pytest.mark.rails


PROMPT_INJECTION_FILE = "tests/rails/data/prompt_injection_data.txt"
SAFE_MESSAGES_FILE = "tests/rails/data/safe_data.txt"
INAPPROPRIATE_LANGUAGE_FILE = "tests/rails/data/inappropriate_lang.txt"


def read_test_data(file: str) -> list[str]:
    """Reads test data from file and returns a list of strings"""
    with open(file) as f:
        return f.read().splitlines()


@pytest.fixture
def response() -> UserQueryResponse:
    """Returns a dummy response"""
    return UserQueryResponse(
        query_id=1,
        content_response=None,
        llm_response="Dummy response",
        feedback_secret_key="feedback-string",
    )


@pytest.mark.parametrize("prompt_injection", read_test_data(PROMPT_INJECTION_FILE))
def test_prompt_injection_found(
    prompt_injection: pytest.FixtureRequest, response: pytest.FixtureRequest
) -> None:
    """Tests that prompt injection is found"""
    question = UserQueryRefined(
        query_text=prompt_injection, query_text_original=prompt_injection
    )
    _, response = _classify_safety(question, response)
    assert response.state == ResultState.ERROR
    assert (
        response.debug_info["safety_classification"]
        == SafetyClassification.PROMPT_INJECTION.value
    )


@pytest.mark.parametrize("safe_text", read_test_data(SAFE_MESSAGES_FILE))
def test_safe_message(
    safe_text: pytest.FixtureRequest, response: pytest.FixtureRequest
) -> None:
    """Tests that safe messages are classified as safe"""
    question = UserQueryRefined(query_text=safe_text, query_text_original=safe_text)
    _, response = _classify_safety(question, response)
    assert response.state != ResultState.ERROR
    assert (
        response.debug_info["safety_classification"] == SafetyClassification.SAFE.value
    )


@pytest.mark.parametrize(
    "inappropriate_text", read_test_data(INAPPROPRIATE_LANGUAGE_FILE)
)
def test_inappropriate_language(
    inappropriate_text: pytest.FixtureRequest, response: pytest.FixtureRequest
) -> None:
    """Tests that inappropriate language is found"""
    question = UserQueryRefined(
        query_text=inappropriate_text, query_text_original=inappropriate_text
    )
    _, response = _classify_safety(question, response)
    assert response.state == ResultState.ERROR
    assert (
        response.debug_info["safety_classification"]
        == SafetyClassification.INAPPROPRIATE_LANGUAGE.value
    )
