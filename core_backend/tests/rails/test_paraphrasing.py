from pathlib import Path
from typing import Dict, List

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


def read_test_data(file: str) -> List[Dict]:
    """Reads test data from file and returns a list of strings"""

    file_path = Path(__file__).parent / file

    with open(file_path, "r") as f:
        content = yaml.safe_load(f)
        return content


@pytest.mark.parametrize("test_data", read_test_data(PARAPHRASE_FILE))
async def test_paraphrasing(test_data: Dict) -> None:
    """Test paraphrasing texts"""
    message = test_data["message"]
    succeeds = test_data["succeeds"]
    contains = test_data.get("contains", [])
    missing = test_data.get("missing", [])

    question = QueryRefined(
        query_text=message,
        user_id=124,
        query_text_original=message,
    )
    response = QueryResponse(
        query_id=1,
        search_results=None,
        llm_response="Dummy response",
        feedback_secret_key="feedback-string",
    )

    paraphrased_question, paraphrased_response = await _paraphrase_question(
        question, response
    )
    if succeeds:
        for text in contains:
            assert text in paraphrased_question.query_text.lower()
        for text in missing:
            assert text not in paraphrased_question.query_text.lower()
    if not succeeds:
        assert isinstance(paraphrased_response, QueryResponseError)
