"""
These are functions that can be used to parse the input questions.
"""

from functools import wraps
from typing import Any, Callable, Tuple

from ..config import (
    LITELLM_MODEL_LANGUAGE_DETECT,
    LITELLM_MODEL_ON_OFF_TOPIC,
    LITELLM_MODEL_PARAPHRASE,
    LITELLM_MODEL_SAFETY,
    LITELLM_MODEL_TRANSLATE,
)
from ..question_answer.config import STANDARD_FAILURE_MESSAGE
from ..question_answer.schemas import (
    ErrorType,
    ResultState,
    UserQueryRefined,
    UserQueryResponse,
    UserQueryResponseError,
)
from ..utils import setup_logger
from .llm_prompts import (
    PARAPHRASE_FAILED_MESSAGE,
    PARAPHRASE_PROMPT,
    TRANSLATE_FAILED_MESSAGE,
    TRANSLATE_PROMPT,
    IdentifiedLanguage,
    OnOffTopicClassification,
    SafetyClassification,
)
from .utils import _ask_llm_async

logger = setup_logger("INPUT RAILS")


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
    if isinstance(response, UserQueryResponseError):
        return question, response

    llm_identified_lang = await _ask_llm_async(
        question=question.query_text,
        prompt=IdentifiedLanguage.get_prompt(),
        litellm_model=LITELLM_MODEL_LANGUAGE_DETECT,
    )

    identified_lang = getattr(
        IdentifiedLanguage, llm_identified_lang, IdentifiedLanguage.UNSUPPORTED
    )
    question.original_language = identified_lang
    response.debug_info["original_language"] = identified_lang

    processed_response = _process_identified_language_response(
        identified_lang,
        response,
    )

    return question, processed_response


def _process_identified_language_response(
    identified_language: IdentifiedLanguage,
    response: UserQueryResponse,
) -> UserQueryResponse | UserQueryResponseError:
    """Process the identified language and return the response."""

    supported_languages_list = IdentifiedLanguage.get_supported_languages()

    if identified_language in supported_languages_list:
        return response
    else:
        supported_languages = ", ".join(supported_languages_list)

        match identified_language:
            case IdentifiedLanguage.UNINTELLIGIBLE:
                error_message = (
                    "Unintelligible input. "
                    + f"The following languages are supported: {supported_languages}."
                )
                error_type = ErrorType.UNINTELLIGIBLE_INPUT
            case IdentifiedLanguage.UNSUPPORTED:
                error_message = (
                    "Unsupported language. Only the following languages "
                    + f"are supported: {supported_languages}."
                )
                error_type = ErrorType.UNSUPPORTED_LANGUAGE

        error_response = UserQueryResponseError(
            error_message=error_message,
            query_id=response.query_id,
            error_type=error_type,
        )
        error_response.debug_info.update(response.debug_info)

        logger.info(
            f"LANGUAGE IDENTIFICATION FAILED due to {identified_language.value} "
            f"language on query id: {str(response.query_id)}"
        )

        return error_response


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

    # skip if error or already in English
    if (
        isinstance(response, UserQueryResponseError)
        or question.original_language == IdentifiedLanguage.ENGLISH
    ):
        return question, response

    if question.original_language is None:
        raise ValueError(
            (
                "Language hasn't been identified. "
                "Identify language before running translation"
            )
        )

    translation_response = await _ask_llm_async(
        question=question.query_text,
        prompt=TRANSLATE_PROMPT.format(language=question.original_language.value),
        litellm_model=LITELLM_MODEL_TRANSLATE,
    )
    if translation_response != TRANSLATE_FAILED_MESSAGE:
        question.query_text = translation_response
        response.debug_info["translated_question"] = translation_response
        return question, response
    else:
        error_response = UserQueryResponseError(
            error_message=STANDARD_FAILURE_MESSAGE,
            query_id=response.query_id,
            error_type=ErrorType.UNABLE_TO_TRANSLATE,
        )
        error_response.debug_info.update(response.debug_info)
        logger.info("TRANSLATION FAILED on query id: " + str(response.query_id))

        return question, error_response


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

    if isinstance(response, UserQueryResponseError):
        return question, response

    llm_classified_safety = await _ask_llm_async(
        question.query_text,
        SafetyClassification.get_prompt(),
        litellm_model=LITELLM_MODEL_SAFETY,
    )
    safety_classification = getattr(SafetyClassification, llm_classified_safety)
    if safety_classification == SafetyClassification.SAFE:
        response.debug_info["safety_classification"] = safety_classification.value
        return question, response
    else:
        error_response = UserQueryResponseError(
            error_message=STANDARD_FAILURE_MESSAGE,
            query_id=response.query_id,
            error_type=ErrorType.QUERY_UNSAFE,
        )
        error_response.debug_info.update(response.debug_info)
        error_response.debug_info["safety_classification"] = safety_classification.value
        error_response.debug_info["query_text"] = question.query_text
        logger.info(
            (
                f"SAFETY CHECK failed on query id: {str(response.query_id)} "
                f"for query text: {question.query_text}"
            )
        )
        return question, error_response


def classify_on_off_topic__before(func: Callable) -> Callable:
    """
    Decorator to check if the question is on-topic or off-topic.
    """

    @wraps(func)
    async def wrapper(
        question: UserQueryRefined,
        response: UserQueryResponse | UserQueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> UserQueryResponse | UserQueryResponseError:
        """
        Wrapper function to check if the question is on-topic or off-topic.
        """
        question, response = await _classify_on_off_topic(question, response)
        response = await func(question, response, *args, **kwargs)
        return response

    return wrapper


async def _classify_on_off_topic(
    user_query: UserQueryRefined, response: UserQueryResponse | UserQueryResponseError
) -> Tuple[UserQueryRefined, UserQueryResponse | UserQueryResponseError]:
    """
    Checks if the user query is on-topic or off-topic.
    """
    if isinstance(response, UserQueryResponseError):
        return user_query, response

    label = await _ask_llm_async(
        question=user_query.query_text,
        prompt=OnOffTopicClassification.get_prompt(),
        litellm_model=LITELLM_MODEL_ON_OFF_TOPIC,
    )
    label_cleaned = label.replace(" ", "_").upper()
    on_off_topic_label = getattr(
        OnOffTopicClassification, label_cleaned, OnOffTopicClassification.UNKNOWN
    )

    response.debug_info["on_off_topic"] = on_off_topic_label.value

    if on_off_topic_label == OnOffTopicClassification.OFF_TOPIC:
        error_response = UserQueryResponseError(
            error_message="Off-topic query",
            query_id=response.query_id,
            error_type=ErrorType.OFF_TOPIC,
        )
        error_response.debug_info.update(response.debug_info)
        error_response.debug_info["query_text"] = user_query.query_text
        logger.info(
            f"OFF-TOPIC query found on query id: {response.query_id} "
            f"for query text {user_query.query_text}"
        )
        return user_query, error_response

    return user_query, response


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

    paraphrase_response = await _ask_llm_async(
        question=question.query_text,
        prompt=PARAPHRASE_PROMPT,
        litellm_model=LITELLM_MODEL_PARAPHRASE,
    )
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