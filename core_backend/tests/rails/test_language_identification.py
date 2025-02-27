"""This module contains tests for language identification."""

from pathlib import Path

import pytest
import yaml

from core_backend.app.llm_call.llm_prompts import IdentifiedLanguage
from core_backend.app.llm_call.process_input import _identify_language
from core_backend.app.question_answer.schemas import QueryRefined, QueryResponse

pytestmark = pytest.mark.rails


LANGUAGE_FILE = "data/language_identification.yaml"


@pytest.fixture(scope="module")
def available_languages() -> list[str]:
    """Returns a list of available languages."""

    return list(IdentifiedLanguage)


def read_test_data(file: str) -> list[tuple[str, str]]:
    """Reads test data from file and returns a list of strings."""

    file_path = Path(__file__).parent / file

    with open(file_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)
        return [(key, value) for key, values in content.items() for value in values]


@pytest.mark.parametrize("expected_label, content", read_test_data(LANGUAGE_FILE))
async def test_language_identification(
    available_languages: list[str], expected_label: str, content: str
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
    if expected_label not in available_languages:
        expected_label = "UNSUPPORTED"
    _, response = await _identify_language(query_refined=question, response=response)

    assert response.debug_info["original_language"] == expected_label
