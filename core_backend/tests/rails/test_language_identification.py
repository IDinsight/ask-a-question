"""This module contains tests for language identification."""

from pathlib import Path

import pytest
import yaml

from core_backend.app.llm_call.llm_prompts import IdentifiedLanguage, IdentifiedScript
from core_backend.app.llm_call.process_input import _identify_language
from core_backend.app.question_answer.schemas import QueryRefined, QueryResponse

pytestmark = pytest.mark.rails


LANGUAGE_FILE = "data/language_identification.yaml"


@pytest.fixture(scope="module")
def available_languages() -> list[str]:
    """Returns a list of available languages."""

    return list(IdentifiedLanguage)


@pytest.fixture(scope="module")
def available_scripts() -> list[str]:
    """Returns a list of available languages."""

    return list(IdentifiedScript)


def read_test_data(file: str) -> list[tuple[str, str, str]]:
    """Reads test data from file and returns a list of strings."""

    file_path = Path(__file__).parent / file

    with open(file_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)
        data = [
            (language, script, text)
            for language, script_dict in content.items()
            for script, texts in script_dict.items()
            for text in texts
        ]
        return data


@pytest.mark.parametrize(
    "expected_language,expected_script,content", read_test_data(LANGUAGE_FILE)
)
async def test_language_identification(
    available_languages: list[str],
    available_scripts: list[str],
    expected_language: str,
    expected_script: str,
    content: str,
) -> None:
    """Test language identification."""

    question = QueryRefined(
        generate_llm_response=False,
        generate_tts=False,
        query_text=content,
        query_text_original=content,
        workspace_id=124,
    )

    response = QueryResponse(
        feedback_secret_key="feedback-string",
        query_id=1,
        llm_response="Dummy response",
        search_results=None,
        session_id=None,
    )

    if expected_language not in available_languages:
        expected_language = "UNSUPPORTED"

    if expected_script not in available_scripts:
        expected_script = "UNKNOWN"

    _, response = await _identify_language(query_refined=question, response=response)

    assert response.debug_info["original_language"] == expected_language
    if expected_language not in ("UNINTELLIGIBLE", "UNSUPPORTED"):
        assert response.debug_info["original_script"] == expected_script
