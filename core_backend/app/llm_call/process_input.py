"""
These are functions that can be used to parse the input questions.
"""

from functools import wraps
from typing import Any, Callable, Optional, Tuple

from ..config import (
    LITELLM_MODEL_LANGUAGE_DETECT,
    LITELLM_MODEL_PARAPHRASE,
    LITELLM_MODEL_SAFETY,
    LITELLM_MODEL_TRANSLATE,
)
from ..question_answer.schemas import (
    ErrorType,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
)
from ..utils import create_langfuse_metadata, setup_logger
from .llm_prompts import (
    PARAPHRASE_FAILED_MESSAGE,
    PARAPHRASE_PROMPT,
    TRANSLATE_FAILED_MESSAGE,
    TRANSLATE_PROMPT,
    IdentifiedLanguage,
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
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """
        Wrapper function to identify the language of the question.
        """
        metadata = create_langfuse_metadata(
            query_id=response.query_id, user_id=query_refined.user_id
        )

        query_refined, response = await _identify_language(
            query_refined, response, metadata=metadata
        )
        response = await func(query_refined, response, *args, **kwargs)
        return response

    return wrapper


async def _identify_language(
    query_refined: QueryRefined,
    response: QueryResponse | QueryResponseError,
    metadata: Optional[dict] = None,
) -> Tuple[QueryRefined, QueryResponse | QueryResponseError]:
    """
    Identifies the language of the question.
    """
    if isinstance(response, QueryResponseError):
        return query_refined, response

    llm_identified_lang = await _ask_llm_async(
        user_message=query_refined.query_text,
        system_message=IdentifiedLanguage.get_prompt(),
        litellm_model=LITELLM_MODEL_LANGUAGE_DETECT,
        metadata=metadata,
    )

    identified_lang = getattr(
        IdentifiedLanguage, llm_identified_lang, IdentifiedLanguage.UNSUPPORTED
    )
    query_refined.original_language = identified_lang
    response.debug_info["original_query"] = query_refined.query_text_original
    response.debug_info["original_language"] = identified_lang

    processed_response = _process_identified_language_response(
        identified_lang,
        response,
    )

    return query_refined, processed_response


def _process_identified_language_response(
    identified_language: IdentifiedLanguage,
    response: QueryResponse,
) -> QueryResponse | QueryResponseError:
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

        error_response = QueryResponseError(
            query_id=response.query_id,
            feedback_secret_key=response.feedback_secret_key,
            llm_response=response.llm_response,
            tts_file=response.tts_file,
            search_results=response.search_results,
            debug_info=response.debug_info,
            error_message=error_message,
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
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """
        Wrapper function to translate the question.
        """
        metadata = create_langfuse_metadata(
            query_id=response.query_id, user_id=query_refined.user_id
        )

        query_refined, response = await _translate_question(
            query_refined, response, metadata=metadata
        )
        response = await func(query_refined, response, *args, **kwargs)

        return response

    return wrapper


async def _translate_question(
    query_refined: QueryRefined,
    response: QueryResponse | QueryResponseError,
    metadata: Optional[dict] = None,
) -> Tuple[QueryRefined, QueryResponse | QueryResponseError]:
    """
    Translates the question to English.
    """

    # skip if error or already in English
    if (
        isinstance(response, QueryResponseError)
        or query_refined.original_language == IdentifiedLanguage.ENGLISH
    ):
        return query_refined, response

    if query_refined.original_language is None:
        raise ValueError(
            (
                "Language hasn't been identified. "
                "Identify language before running translation"
            )
        )

    translation_response = await _ask_llm_async(
        user_message=query_refined.query_text,
        system_message=TRANSLATE_PROMPT.format(
            language=query_refined.original_language.value
        ),
        litellm_model=LITELLM_MODEL_TRANSLATE,
        metadata=metadata,
    )
    if translation_response != TRANSLATE_FAILED_MESSAGE:
        query_refined.query_text = translation_response  # update text with translation
        response.debug_info["translated_question"] = translation_response
        return query_refined, response
    else:
        error_response = QueryResponseError(
            query_id=response.query_id,
            feedback_secret_key=response.feedback_secret_key,
            llm_response=response.llm_response,
            tts_file=response.tts_file,
            search_results=response.search_results,
            debug_info=response.debug_info,
            error_message="Unable to translate",
            error_type=ErrorType.UNABLE_TO_TRANSLATE,
        )
        error_response.debug_info.update(response.debug_info)
        logger.info("TRANSLATION FAILED on query id: " + str(response.query_id))

        return query_refined, error_response


def classify_safety__before(func: Callable) -> Callable:
    """
    Decorator to classify the safety of the question.
    """

    @wraps(func)
    async def wrapper(
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """
        Wrapper function to classify the safety of the question.
        """
        metadata = create_langfuse_metadata(
            query_id=response.query_id, user_id=query_refined.user_id
        )

        query_refined, response = await _classify_safety(
            query_refined, response, metadata=metadata
        )
        response = await func(query_refined, response, *args, **kwargs)
        return response

    return wrapper


async def _classify_safety(
    query_refined: QueryRefined,
    response: QueryResponse | QueryResponseError,
    metadata: Optional[dict] = None,
) -> Tuple[QueryRefined, QueryResponse | QueryResponseError]:
    """
    Classifies the safety of the question.
    """

    if isinstance(response, QueryResponseError):
        return query_refined, response

    if metadata is None:
        metadata = {}

    llm_classified_safety = await _ask_llm_async(
        user_message=query_refined.query_text,
        system_message=SafetyClassification.get_prompt(),
        litellm_model=LITELLM_MODEL_SAFETY,
        metadata=metadata,
    )
    safety_classification = getattr(SafetyClassification, llm_classified_safety)
    if safety_classification == SafetyClassification.SAFE:
        response.debug_info["safety_classification"] = safety_classification.value
        return query_refined, response
    else:
        error_response = QueryResponseError(
            query_id=response.query_id,
            feedback_secret_key=response.feedback_secret_key,
            llm_response=response.llm_response,
            tts_file=response.tts_file,
            search_results=response.search_results,
            debug_info=response.debug_info,
            error_message=f"{safety_classification.value.lower()} found.",
            error_type=ErrorType.QUERY_UNSAFE,
        )
        error_response.debug_info.update(response.debug_info)
        error_response.debug_info["safety_classification"] = safety_classification.value
        error_response.debug_info["query_text"] = query_refined.query_text
        logger.info(
            (
                f"SAFETY CHECK failed on query id: {str(response.query_id)} "
                f"for query text: {query_refined.query_text}"
            )
        )
        return query_refined, error_response


def paraphrase_question__before(func: Callable) -> Callable:
    """
    Decorator to paraphrase the question.
    """

    @wraps(func)
    async def wrapper(
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """
        Wrapper function to paraphrase the question.
        """
        metadata = create_langfuse_metadata(
            query_id=response.query_id, user_id=query_refined.user_id
        )

        query_refined, response = await _paraphrase_question(
            query_refined, response, metadata=metadata
        )
        response = await func(query_refined, response, *args, **kwargs)

        return response

    return wrapper


async def _paraphrase_question(
    query_refined: QueryRefined,
    response: QueryResponse | QueryResponseError,
    metadata: Optional[dict] = None,
) -> Tuple[QueryRefined, QueryResponse | QueryResponseError]:
    """
    Paraphrases the question. If it is unable to identify the question,
    it will return the original sentence.
    """

    if isinstance(response, QueryResponseError):
        return query_refined, response

    if metadata is None:
        metadata = {}

    paraphrase_response = await _ask_llm_async(
        user_message=query_refined.query_text,
        system_message=PARAPHRASE_PROMPT,
        litellm_model=LITELLM_MODEL_PARAPHRASE,
        metadata=metadata,
    )
    if paraphrase_response != PARAPHRASE_FAILED_MESSAGE:
        query_refined.query_text = paraphrase_response  # update text with paraphrase
        response.debug_info["paraphrased_question"] = paraphrase_response
        return query_refined, response
    else:
        error_response = QueryResponseError(
            query_id=response.query_id,
            feedback_secret_key=response.feedback_secret_key,
            llm_response=response.llm_response,
            tts_file=response.tts_file,
            search_results=response.search_results,
            debug_info=response.debug_info,
            error_message="Unable to paraphrase the query.",
            error_type=ErrorType.UNABLE_TO_PARAPHRASE,
        )
        logger.info(
            (
                f"PARAPHRASE FAILED on query id:  {str(response.query_id)} "
                f"for query text: {query_refined.query_text}"
            )
        )
        return query_refined, error_response
