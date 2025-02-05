"""This module contains tests that check LLM response content validation functions.
LLM response content validation functions are rails that check if the responses are
based on the given context or not.
"""

from pathlib import Path
from typing import Literal

import pytest
import yaml

from core_backend.app.config import ALIGN_SCORE_THRESHOLD
from core_backend.app.llm_call.process_output import (
    _get_llm_align_score,
)

pytestmark = pytest.mark.rails

CONTEXT_RESPONSE_FILE = "data/llm_response_in_context.yaml"
TestDataKeys = Literal["context", "statement", "expected", "reason"]


def read_test_data(file: str) -> list[tuple]:
    """Reads test data from file and returns a list of strings."""

    file_path = Path(__file__).parent / file

    with open(file_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)
        return [(c["context"], *t.values()) for c in content for t in c["tests"]]


@pytest.mark.asyncio(scope="module")
@pytest.mark.parametrize(
    "context, statement, expected, reason", read_test_data(CONTEXT_RESPONSE_FILE)
)
async def test_llm_alignment_score(
    context: str, statement: str, expected: bool, reason: str
) -> None:
    """This checks if LLM based alignment score returns the correct answer."""

    align_score = await _get_llm_align_score(
        align_score_data={"evidence": context, "claim": statement}
    )
    assert (align_score.score > float(ALIGN_SCORE_THRESHOLD)) == expected, (
        reason + f" {align_score.score}"
    )
