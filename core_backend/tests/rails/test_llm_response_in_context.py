"""
These tests check LLM response content validation functions.
LLM response content validation functions are rails that check if the responses
are based on the given context or not.
"""
from typing import Dict, List, Literal

import pytest
import yaml

pytestmark = pytest.mark.rails

CONTEXT_RESPONSE_FILE = "tests/rails/data/llm_response_in_context.yaml"
TestDataKeys = Literal["context", "statement", "expected", "reason"]


def read_test_data(file: str) -> List[Dict[TestDataKeys, str]]:
    """Reads test data from file and returns a list of strings"""

    with open(file, "r") as f:
        content = yaml.safe_load(f)
        return [dict(context=c["context"], **t) for c in content for t in c["tests"]]


def test_alignScore(llm_sentence: str, context: str, expected_answer: bool) -> None:
    """
    This checks if alignScore returns the correct answer
    """
    pass


def test_llm_rag_validation(
    llm_sentence: str, context: str, expected_answer: bool
) -> None:
    """
    This checks if base LLM validation returns the correct answer
    """
    pass
