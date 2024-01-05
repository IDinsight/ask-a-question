from typing import List, Tuple

import pytest
import yaml

from core_backend.app.configs.llm_prompts import IdentifiedLanguage
from core_backend.app.llm_call.parse_input import identify_language
from core_backend.app.schemas import UserQueryRefined

pytestmark = pytest.mark.rails


LANGUAGE_FILE = "tests/rails/data/language_identification.yaml"


@pytest.fixture(scope="module")
def available_languages() -> list[str]:
    """Returns a list of available languages"""

    return [lang.value for lang in IdentifiedLanguage]


def read_test_data(file: str) -> List[Tuple[str, str]]:
    """Reads test data from file and returns a list of strings"""

    with open(file, "r") as f:
        content = yaml.safe_load(f)
        return [(key, value) for key, values in content.items() for value in values]


@pytest.mark.parametrize("language, content", read_test_data(LANGUAGE_FILE))
def test_language_identification(
    available_languages: pytest.FixtureRequest, language: str, content: str
) -> None:
    """Test language identification"""
    question = UserQueryRefined(query_text=content, query_text_original=content)
    if language not in available_languages:
        language = "UNKNOWN"
    identified_language = identify_language(question).original_language
    assert identified_language is not None
    assert identified_language.value == language
