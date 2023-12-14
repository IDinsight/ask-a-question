import pytest

from core_backend.app.configs.llm_prompts import SafetyClassification
from core_backend.app.llm_call.parse_input import classify_safety

pytestmark = pytest.mark.rails


PROMPT_INJECTION_FILE = "tests/rails/data/prompt_injection_data.txt"
SAFE_MESSAGES_FILE = "tests/rails/data/safe_data.txt"
INAPPROPRIATE_LANGUAGE_FILE = "tests/rails/data/inappropriate_lang.txt"


def read_test_data(file: str) -> list[str]:
    """Reads test data from file and returns a list of strings"""
    with open(file) as f:
        return f.read().splitlines()


@pytest.mark.parametrize("prompt_injection", read_test_data(PROMPT_INJECTION_FILE))
def test_prompt_injection_found(prompt_injection: pytest.FixtureRequest) -> None:
    """Tests that prompt injection is found"""
    assert classify_safety(prompt_injection) == SafetyClassification.PROMPT_INJECTION


@pytest.mark.parametrize("safe_text", read_test_data(SAFE_MESSAGES_FILE))
def test_safe_message(safe_text: pytest.FixtureRequest) -> None:
    """Tests that safe messages are classified as safe"""
    assert classify_safety(safe_text) == SafetyClassification.SAFE


@pytest.mark.parametrize(
    "inappropriate_text", read_test_data(INAPPROPRIATE_LANGUAGE_FILE)
)
def test_inappropriate_language(inappropriate_text: pytest.FixtureRequest) -> None:
    """Tests that inappropriate language is found"""
    assert (
        classify_safety(inappropriate_text) == SafetyClassification.INAPPROPRIATE_LANGUAGE
    )
