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
from ..schemas import (
    ErrorType,
    ResultState,
    UserQueryRefined,
    UserQueryResponse,
    UserQueryResponseError,
)
from ..utils import setup_logger
from .utils import _ask_llm_async

logger = setup_logger("INPUT RAILS")

STANDARD_FAILURE_MESSAGE = (
    "Sorry, I am unable to understand your question. "
    "Please rephrase your question and try again."
)


def classify_safety__before(func: Callable) -> Callable:
    """
    Decorator to classify the safety of the question.
    """

    @wraps(func)
    async def wrapper(
        question: UserQueryRefined,
        response: UserQueryResponse | UserQueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> UserQueryResponse | UserQueryResponseError:
        """
        Wrapper function to classify the safety of the question.
        """
        question, response = await _classify_safety(question, response)
        response = await func(question, response, *args, **kwargs)
        return response

    return wrapper


async def _classify_safety(
    question: UserQueryRefined, response: UserQueryResponse | UserQueryResponseError
) -> Tuple[UserQueryRefined, UserQueryResponse | UserQueryResponseError]:
    """
    Classifies the safety of the question.
    """
    if not isinstance(response, UserQueryResponseError):
        safety_classification = getattr(
            SafetyClassification,
            await _ask_llm_async(
                question.query_text, SafetyClassification.get_prompt()
            ),
        )
        if safety_classification != SafetyClassification.SAFE:
            error_response = UserQueryResponseError(
                error_message=STANDARD_FAILURE_MESSAGE,
                query_id=response.query_id,
                error_type=ErrorType.QUERY_UNSAFE,
            )
            error_response.debug_info.update(response.debug_info)
            error_response.debug_info[
                "safety_classification"
            ] = safety_classification.value
            error_response.debug_info["query_text"] = question.query_text
            logger.info(
                (
                    f"SAFETY CHECK failed on query id: {str(response.query_id)} "
                    f"for query text: {question.query_text}"
                )
            )
            return question, error_response
        else:
            response.debug_info["safety_classification"] = safety_classification.value

    return question, response


def identify_language__before(func: Callable) -> Callable:
    """
    Decorator to identify the language of the question.
    """

    @wraps(func)
    async def wrapper(
        question: UserQueryRefined,
        response: UserQueryResponse | UserQueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> UserQueryResponse | UserQueryResponseError:
        """
        Wrapper function to identify the language of the question.
        """
        question, response = await _identify_language(question, response)
        response = await func(question, response, *args, **kwargs)
        return response

    return wrapper


async def _identify_language(
    question: UserQueryRefined, response: UserQueryResponse | UserQueryResponseError
) -> Tuple[UserQueryRefined, UserQueryResponse | UserQueryResponseError]:
    """
    Identifies the language of the question.
    """
    if not isinstance(response, UserQueryResponseError):
        identified_lang = await _ask_llm_async(
            question.query_text, IdentifiedLanguage.get_prompt()
        )
        if identified_lang in IdentifiedLanguage.get_supported_languages():
            question.original_language = getattr(IdentifiedLanguage, identified_lang)
        else:
            question.original_language = IdentifiedLanguage.UNKNOWN

        if question.original_language is not None:
            response.debug_info["original_language"] = question.original_language.value

    return question, response


def translate_question__before(func: Callable) -> Callable:
    """
    Decorator to translate the question.
    """

    @wraps(func)
    async def wrapper(
        question: UserQueryRefined,
        response: UserQueryResponse | UserQueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> UserQueryResponse | UserQueryResponseError:
        """
        Wrapper function to translate the question.
        """
        question, response = await _translate_question(question, response)
        response = await func(question, response, *args, **kwargs)

        return response

    return wrapper


async def _translate_question(
    question: UserQueryRefined, response: UserQueryResponse | UserQueryResponseError
) -> Tuple[UserQueryRefined, UserQueryResponse | UserQueryResponseError]:
    """
    Translates the question to English.
    """

    if question.original_language == IdentifiedLanguage.ENGLISH or isinstance(
        response, UserQueryResponseError
    ):
        return question, response

    if question.original_language is None:
        raise ValueError(
            (
                "Language hasn't been identified. "
                "Identify language before running translation"
            )
        )

    if question.original_language == IdentifiedLanguage.UNKNOWN:
        supported_languages = ", ".join(IdentifiedLanguage.get_supported_languages())

        error_response = UserQueryResponseError(
            error_message=STANDARD_FAILURE_MESSAGE
            + f" Only the following languages are supported: {supported_languages}. ",
            query_id=response.query_id,
            error_type=ErrorType.UNKNOWN_LANGUAGE,
        )

        logger.info(
            "TRANSLATION FAILED due to UNKNOWN language on query id: "
            + str(response.query_id)
        )

        return question, error_response
    else:
        translation_response = await _ask_llm_async(
            question.query_text, TRANSLATE_INPUT + question.original_language.value
        )
        if translation_response != TRANSLATE_FAILED_MESSAGE:
            question.query_text = translation_response
            response.debug_info["translated_question"] = translation_response
        else:
            error_response = UserQueryResponseError(
                error_message=STANDARD_FAILURE_MESSAGE,
                query_id=response.query_id,
                error_type=ErrorType.UNABLE_TO_TRANSLATE,
            )
            error_response.debug_info.update(response.debug_info)
            logger.info("TRANSLATION FAILED on query id: " + str(response.query_id))

            return question, error_response
    return question, response


def paraphrase_question__before(func: Callable) -> Callable:
    """
    Decorator to paraphrase the question.
    """

    @wraps(func)
    async def wrapper(
        question: UserQueryRefined,
        response: UserQueryResponse | UserQueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> UserQueryResponse | UserQueryResponseError:
        """
        Wrapper function to paraphrase the question.
        """
        question, response = await _paraphrase_question(question, response)
        response = await func(question, response, *args, **kwargs)

        return response

    return wrapper


async def _paraphrase_question(
    question: UserQueryRefined, response: UserQueryResponse | UserQueryResponseError
) -> Tuple[UserQueryRefined, UserQueryResponse | UserQueryResponseError]:
    """
    Paraphrases the question. If it is unable to identify the question,
    it will return the original sentence.
    """

    if isinstance(response, UserQueryResponseError):
        return question, response

    paraphrase_response = await _ask_llm_async(question.query_text, PARAPHRASE_INPUT)
    if paraphrase_response != PARAPHRASE_FAILED_MESSAGE:
        question.query_text = paraphrase_response
        response.debug_info["paraphrased_question"] = paraphrase_response
        return question, response
    else:
        error_response = UserQueryResponseError(
            error_message=STANDARD_FAILURE_MESSAGE,
            query_id=response.query_id,
            error_type=ErrorType.UNABLE_TO_PARAPHRASE,
        )
        response.state = ResultState.ERROR
        logger.info(
            (
                f"PARAPHRASE FAILED on query id:  {str(response.query_id)} "
                f"for query text: {question.query_text}"
            )
        )
        return question, error_response
