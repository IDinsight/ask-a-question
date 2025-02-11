"""This module contains tests for the paraphrasing functionality."""

from pathlib import Path

import pytest
import yaml

from core_backend.app.llm_call.process_input import _paraphrase_question
from core_backend.app.question_answer.schemas import (
    QueryRefined,
    QueryResponse,
    QueryResponseError,
)

pytestmark = pytest.mark.rails


PARAPHRASE_FILE = "data/paraphrasing_data.txt"


def read_test_data(file: str) -> list[dict]:
    """Reads test data from file and returns a list of strings."""

    file_path = Path(__file__).parent / file

    with open(file_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)
        return content


@pytest.mark.parametrize("test_data", read_test_data(PARAPHRASE_FILE))
async def test_paraphrasing(test_data: dict) -> None:
    """Test paraphrasing texts."""

    message = test_data["message"]
    succeeds = test_data["succeeds"]
    contains = test_data.get("contains", [])
    missing = test_data.get("missing", [])

    question = QueryRefined(
        generate_llm_response=False,
        generate_tts=False,
        query_text=message,
        query_text_original=message,
        workspace_id=124,
    )
    response = QueryResponse(
        feedback_secret_key="feedback-string",
        llm_response="Dummy response",
        query_id=1,
        search_results=None,
        session_id=None,
    )

    paraphrased_question, paraphrased_response = await _paraphrase_question(
        query_refined=question, response=response
    )
    if succeeds:
        for text in contains:
            assert text in paraphrased_question.query_text.lower()
        for text in missing:
            assert text not in paraphrased_question.query_text.lower()
    if not succeeds:
        assert isinstance(paraphrased_response, QueryResponseError)
