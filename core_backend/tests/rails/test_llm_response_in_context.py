"""
These tests check LLM response content validation functions.
LLM response content validation functions are rails that check if the responses
are based on the given context or not.
"""
import pytest

pytestmark = pytest.mark.rails


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
