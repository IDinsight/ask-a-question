"""
These tests check LLM response content validation functions.
LLM response content validation functions are rails that check if the responses
are based on the given context or not.
"""
from pathlib import Path
from typing import List, Literal, Tuple

import pytest
import yaml

from core_backend.app.configs.app_config import ALIGN_SCORE_API, ALIGN_SCORE_THRESHOLD
from core_backend.app.llm_call.check_output import _get_alignScore_score

pytestmark = pytest.mark.rails

CONTEXT_RESPONSE_FILE = "data/llm_response_in_context.yaml"
TestDataKeys = Literal["context", "statement", "expected", "reason"]


def read_test_data(file: str) -> List[Tuple]:
    """Reads test data from file and returns a list of strings"""

    file_path = Path(__file__).parent / file

    with open(file_path, "r") as f:
        content = yaml.safe_load(f)
        return [(c["context"], *t.values()) for c in content for t in c["tests"]]


@pytest.mark.asyncio(scope="module")
@pytest.mark.parametrize(
    "context, statement, expected, reason", read_test_data(CONTEXT_RESPONSE_FILE)
)
async def test_alignScore(
    context: str, statement: str, expected: bool, reason: str
) -> None:
    """
    This checks if alignScore returns the correct answer
    """
    score = await _get_alignScore_score(
        ALIGN_SCORE_API, {"evidence": context, "claim": statement}
    )
    assert (score > float(ALIGN_SCORE_THRESHOLD)) == expected, reason + f" {score}"


def test_llm_rag_validation(
    llm_sentence: str, context: str, expected_answer: bool
) -> None:
    """
    This checks if base LLM validation returns the correct answer
    """
    pass
