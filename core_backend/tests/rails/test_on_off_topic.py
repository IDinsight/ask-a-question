from pathlib import Path
from typing import List, Tuple

import pytest
import yaml

from core_backend.app.llm_call.process_input import _classify_on_off_topic
from core_backend.app.question_answer.schemas import QueryRefined, QueryResponse

pytestmark = pytest.mark.rails


ON_OFF_TOPIC_FILE = "data/on_off_topic.yaml"


def read_test_data(file: str) -> List[Tuple[str, str]]:
    """Reads test data from file and returns a list of strings"""

    file_path = Path(__file__).parent / file

    with open(file_path, "r") as f:
        content = yaml.safe_load(f)
        return [(key, value) for key, values in content.items() for value in values]


@pytest.mark.parametrize("expected_label, content", read_test_data(ON_OFF_TOPIC_FILE))
async def test_on_off_topic(expected_label: str, content: str) -> None:
    """Test on- vs. off-topic classification"""
    question = QueryRefined(
        query_text=content,
        user_id=124,
        query_text_original=content,
    )
    response = QueryResponse(
        query_id=1,
        search_results=None,
        llm_response="Dummy response",
        feedback_secret_key="feedback-string",
    )

    _, response = await _classify_on_off_topic(question, response)

    assert response.debug_info["on_off_topic"] == expected_label
