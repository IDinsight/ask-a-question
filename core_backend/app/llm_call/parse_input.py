"""
These are functions that can be used to parse the input questions.
"""

from ..configs.llm_prompts import (
    CHECK_INPUT_SAFETY,
    IDENTIFY_LANG_INPUT,
    PARAPHRASE_INPUT,
    TRANSLATE_INPUT,
    IdentifiedLanguage,
    SafetyClassification,
)
from ..schemas import UserQueryRefined
from .utils import _ask_llm


def input_is_safe(question: UserQueryRefined) -> bool:
    """
    Checks for prompt injection in the question.
    """
    if (
        getattr(
            SafetyClassification,
            _ask_llm(question.query_text, CHECK_INPUT_SAFETY),
        )
        == SafetyClassification.SAFE
    ):
        return True
    return False


def identify_language(question: UserQueryRefined) -> UserQueryRefined:
    """
    Identifies the language of the question.
    """

    question.original_language = getattr(
        IdentifiedLanguage, _ask_llm(question.query_text, IDENTIFY_LANG_INPUT)
    )

    return question


def translate_question(question: UserQueryRefined) -> UserQueryRefined:
    """
    Translates the question to English.
    """

    if (
        question.original_language
        in [
            IdentifiedLanguage.ENGLISH,
            IdentifiedLanguage.UNKNOWN,
        ]
        or question.original_language is None
    ):
        return question
    else:
        question.query_text = _ask_llm(
            question.query_text, TRANSLATE_INPUT + question.original_language.value
        )
        return question


def paraphrase_question(question: UserQueryRefined) -> UserQueryRefined:
    """
    Paraphrases the question.
    """

    question.query_text = _ask_llm(question.query_text, PARAPHRASE_INPUT)

    return question
