"""
These are functions that can be used to parse the input questions.
"""

from functools import wraps
from typing import Any, Callable, Tuple

from ..configs.llm_prompts import (
    PARAPHRASE_FAILED_MESSAGE,
    PARAPHRASE_INPUT,
    TRANSLATE_FAILED_MESSAGE,
    TRANSLATE_INPUT,
    IdentifiedLanguage,
    SafetyClassification,
)
from ..schemas import ResultState, UserQueryRefined, UserQueryResponse
from ..utils import setup_logger
from .utils import _ask_llm

logger = setup_logger("INPUT RAILS")

STANDARD_FAILURE_MESSAGE = (
    "Sorry, I am unable to understand your question. "
    "Please rephrase your question and try again."
)


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
            response.llm_response = STANDARD_FAILURE_MESSAGE
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
        supported_languages = ", ".join(IdentifiedLanguage.get_supported_languages())

        response.llm_response = (
            STANDARD_FAILURE_MESSAGE
            + f"Only the following languages are supported: {supported_languages}. "
        )

        response.state = ResultState.ERROR
        logger.info(
            "TRANSLATION FAILED due to UNKNOWN language on question: "
            + question.query_text
        )
    else:
        translation_response = _ask_llm(
            question.query_text, TRANSLATE_INPUT + question.original_language.value
        )
        if translation_response != TRANSLATE_FAILED_MESSAGE:
            question.query_text = translation_response
            response.debug_info["translated_question"] = translation_response
        else:
            response.llm_response = STANDARD_FAILURE_MESSAGE
            response.state = ResultState.ERROR
            logger.info("TRANSLATION FAILED on question: " + question.query_text)

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
    Paraphrases the question. If it is unable to identify the question,
    it will return the original sentence.
    """

    if response.state == ResultState.ERROR:
        return question, response

    paraphrase_response = _ask_llm(question.query_text, PARAPHRASE_INPUT)
    if paraphrase_response != PARAPHRASE_FAILED_MESSAGE:
        question.query_text = paraphrase_response
        response.debug_info["paraphrased_question"] = paraphrase_response
    else:
        response.state = ResultState.ERROR
        logger.info("PARAPHRASE FAILED on question: " + question.query_text)

    return question, response
