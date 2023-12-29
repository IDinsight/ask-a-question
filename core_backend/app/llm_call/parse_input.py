"""
These are functions that can be used to parse the input questions.
"""

from functools import wraps
from typing import Any, Callable, Tuple

from ..configs.llm_prompts import (
    PARAPHRASE_INPUT,
    TRANSLATE_INPUT,
    IdentifiedLanguage,
    SafetyClassification,
)
from ..schemas import ResultState, UserQueryRefined, UserQueryResponse
from .utils import _ask_llm


def classify_safety(func: Callable) -> Callable:
    """
    Decorator to classify the safety of the question.
    """

    @wraps(func)
    async def wrapper(
        question: UserQueryRefined,
        response: UserQueryResponse,
        *args: Any,
        **kwargs: Any,
    ) -> UserQueryResponse:
        """
        Wrapper function to classify the safety of the question.
        """
        question, response = _classify_safety(question, response)
        response = await func(question, response, *args, **kwargs)
        return response

    return wrapper


def _classify_safety(
    question: UserQueryRefined, response: UserQueryResponse
) -> Tuple[UserQueryRefined, UserQueryResponse]:
    """
    Classifies the safety of the question.
    """
    if response.state != ResultState.ERROR:
        safety_classification = getattr(
            SafetyClassification,
            _ask_llm(question.query_text, SafetyClassification.get_prompt()),
        )
        if safety_classification != SafetyClassification.SAFE:
            response.llm_response = (
                "Sorry, we are unable to answer your question."
                "Please rephrase your question and try again."
            )
            response.state = ResultState.ERROR
        response.debug_info["safety_classification"] = safety_classification.value

    return question, response


def identify_language(func: Callable) -> Callable:
    """
    Decorator to identify the language of the question.
    """

    @wraps(func)
    async def wrapper(
        question: UserQueryRefined,
        response: UserQueryResponse,
        *args: Any,
        **kwargs: Any,
    ) -> UserQueryResponse:
        """
        Wrapper function to identify the language of the question.
        """
        question, response = _identify_language(question, response)
        response = await func(question, response, *args, **kwargs)
        return response

    return wrapper


def _identify_language(
    question: UserQueryRefined, response: UserQueryResponse
) -> Tuple[UserQueryRefined, UserQueryResponse]:
    """
    Identifies the language of the question.
    """
    if response.state != ResultState.ERROR:
        question.original_language = getattr(
            IdentifiedLanguage,
            _ask_llm(question.query_text, IdentifiedLanguage.get_prompt()),
        )
        if question.original_language is not None:
            response.debug_info["original_language"] = question.original_language.value

    return question, response


def translate_question(func: Callable) -> Callable:
    """
    Decorator to translate the question.
    """

    @wraps(func)
    async def wrapper(
        question: UserQueryRefined,
        response: UserQueryResponse,
        *args: Any,
        **kwargs: Any,
    ) -> UserQueryResponse:
        """
        Wrapper function to translate the question.
        """
        question, response = _identify_language(question, response)
        question, response = _translate_question(question, response)
        response = await func(question, response, *args, **kwargs)
        response.debug_info["translated_question"] = question.query_text

        return response

    return wrapper


def _translate_question(
    question: UserQueryRefined, response: UserQueryResponse
) -> Tuple[UserQueryRefined, UserQueryResponse]:
    """
    Translates the question to English.
    """

    if (
        question.original_language == IdentifiedLanguage.ENGLISH
        or response.state == ResultState.ERROR
    ):
        return question, response

    if question.original_language is None:
        response.state = ResultState.ERROR
        raise ValueError(
            (
                "Language hasn't been identified. "
                "Identify language before running translation"
            )
        )

    if question.original_language == IdentifiedLanguage.UNKNOWN:
        response.llm_response = (
            "Sorry, we are unable to understand your question. "
            "Please rephrase your question and try again."
        )
        response.state = ResultState.ERROR
    else:
        question.query_text = _ask_llm(
            question.query_text, TRANSLATE_INPUT + question.original_language.value
        )

    return question, response


def paraphrase_question(func: Callable) -> Callable:
    """
    Decorator to paraphrase the question.
    """

    @wraps(func)
    async def wrapper(
        question: UserQueryRefined,
        response: UserQueryResponse,
        *args: Any,
        **kwargs: Any,
    ) -> UserQueryResponse:
        """
        Wrapper function to paraphrase the question.
        """
        question, response = _paraphrase_question(question, response)
        response = await func(question, response, *args, **kwargs)

        return response

    return wrapper


def _paraphrase_question(
    question: UserQueryRefined, response: UserQueryResponse
) -> Tuple[UserQueryRefined, UserQueryResponse]:
    """
    Paraphrases the question.
    """

    if response.state == ResultState.ERROR:
        return question, response

    question.query_text = _ask_llm(question.query_text, PARAPHRASE_INPUT)

    return question, response
