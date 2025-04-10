"""This module contains functions that can be used to parse input questions."""

from functools import wraps
from typing import Any, Callable, Optional

from pydantic import ValidationError

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
from ..utils import setup_logger
from .llm_prompts import (
    LANGUAGE_ID_PROMPT,
    PARAPHRASE_FAILED_MESSAGE,
    PARAPHRASE_PROMPT,
    TRANSLATE_FAILED_MESSAGE,
    TRANSLATE_PROMPT,
    IdentifiedLanguage,
    IdentifiedScript,
    LanguageIdentificationResponse,
    SafetyClassification,
)
from .utils import _ask_llm_async, remove_json_markdown

logger = setup_logger(name="INPUT RAILS")


def identify_language__before(func: Callable) -> Callable:
    """Decorator to identify the language of the question.

    Parameters
    ----------
    func
        The function to be decorated.

    Returns
    -------
    Callable
        The decorated function.
    """

    @wraps(func)
    async def wrapper(
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """Wrapper function to identify the language of the question.

        Parameters
        ----------
        query_refined
            The refined query object.
        response
            The response object.
        args
            Additional positional arguments.
        kwargs
            Additional keyword arguments.

        Returns
        -------
        QueryResponse | QueryResponseError
            The appropriate response object.
        """

        query_refined, response = await _identify_language(
            query_refined=query_refined, response=response
        )
        response = await func(query_refined, response, *args, **kwargs)
        return response

    return wrapper


async def _identify_language(
    *,
    metadata: Optional[dict] = None,
    query_refined: QueryRefined,
    response: QueryResponse | QueryResponseError,
) -> tuple[QueryRefined, QueryResponse | QueryResponseError]:
    """Identify the language and script of the question.

    Parameters
    ----------
    metadata
        The metadata to be used.
    query_refined
        The refined query object.
    response
        The response object.

    Returns
    -------
    tuple[QueryRefined, QueryResponse | QueryResponseError]
        The refined query object and the appropriate response object.
    """

    if isinstance(response, QueryResponseError):
        return query_refined, response

    json_str = await _ask_llm_async(
        json_=True,
        litellm_model=LITELLM_MODEL_LANGUAGE_DETECT,
        metadata=metadata,
        system_message=LANGUAGE_ID_PROMPT,
        user_message=query_refined.query_text,
    )

    cleaned_json_str = remove_json_markdown(text=json_str)
    try:
        lang_info = LanguageIdentificationResponse.model_validate_json(cleaned_json_str)
        identified_lang = IdentifiedLanguage(lang_info.language.upper())
        identified_script = IdentifiedScript(lang_info.script.upper())
    except ValidationError:
        identified_lang = IdentifiedLanguage.UNSUPPORTED
        identified_script = IdentifiedScript.LATIN

    query_refined.original_language = identified_lang
    query_refined.original_script = identified_script

    response.debug_info["original_query"] = query_refined.query_text_original
    response.debug_info["original_language"] = identified_lang
    response.debug_info["original_script"] = identified_script

    processed_response = _process_identified_language_response(
        identified_language=identified_lang,
        identified_script=identified_script,
        response=response,
    )

    return query_refined, processed_response


def _process_identified_language_response(
    *,
    identified_language: IdentifiedLanguage,
    identified_script: IdentifiedScript,
    response: QueryResponse,
) -> QueryResponse | QueryResponseError:
    """Process the identified language and return the response.

    Parameters
    ----------
    identified_language
        The identified language.
    identified_script
        The identified script.
    response
        The response object.

    Returns
    -------
    QueryResponse | QueryResponseError
        The appropriate response object.
    """

    supported_languages_list = IdentifiedLanguage.get_supported_languages()
    supported_scripts_list = IdentifiedScript.get_supported_scripts()

    if (
        identified_language in supported_languages_list
        and identified_script in supported_scripts_list
    ):
        return response

    supported_languages = ", ".join(supported_languages_list)
    supported_scripts = ", ".join(supported_scripts_list)

    if identified_language == IdentifiedLanguage.UNINTELLIGIBLE:
        error_message = (
            "Unintelligible input. "
            + f"The following languages are supported: {supported_languages}."
        )
        error_type: ErrorType = ErrorType.UNINTELLIGIBLE_INPUT
    else:
        # TODO: create types for language x script combos
        if identified_script == IdentifiedScript.UNKNOWN:
            error_message = (
                "Unsupported script. "
                + f"Only the following scripts are supported: {supported_scripts}"
            )
            error_type = ErrorType.UNSUPPORTED_SCRIPT
        else:
            error_message = (
                "Unsupported language. Only the following languages "
                + f"are supported: {supported_languages}."
            )
            error_type = ErrorType.UNSUPPORTED_LANGUAGE

    error_response = QueryResponseError(
        debug_info=response.debug_info,
        feedback_secret_key=response.feedback_secret_key,
        error_message=error_message,
        error_type=error_type,
        llm_response=response.llm_response,
        query_id=response.query_id,
        search_results=response.search_results,
        session_id=response.session_id,
    )
    error_response.debug_info.update(response.debug_info)

    logger.info(
        f"LANGUAGE IDENTIFICATION FAILED due to {error_message} "
        f"language on query id: {str(response.query_id)}"
    )

    return error_response


def translate_question__before(func: Callable) -> Callable:
    """Decorator to translate the question.

    Parameters
    ----------
    func
        The function to be decorated.

    Returns
    -------
    Callable
        The decorated function.
    """

    @wraps(func)
    async def wrapper(
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """Wrapper function to translate the question.

        Parameters
        ----------
        query_refined
            The refined query object.
        response
            The response object.
        args
            Additional positional arguments.
        kwargs
            Additional keyword arguments.

        Returns
        -------
        QueryResponse | QueryResponseError
            The appropriate response object.
        """

        query_refined, response = await _translate_question(
            query_refined=query_refined, response=response
        )
        response = await func(query_refined, response, *args, **kwargs)

        return response

    return wrapper


async def _translate_question(
    *,
    metadata: Optional[dict] = None,
    query_refined: QueryRefined,
    response: QueryResponse | QueryResponseError,
) -> tuple[QueryRefined, QueryResponse | QueryResponseError]:
    """Translate the question to English.

    Parameters
    ----------
    metadata
        The metadata to be used.
    query_refined
        The refined query object.
    response
        The response object.

    Returns
    -------
    tuple[QueryRefined, QueryResponse | QueryResponseError]
        The refined query object and the appropriate response object.

    Raises
    ------
    ValueError
        If the language hasn't been identified.
    """

    # Skip if error or already in English.
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

    metadata = metadata or {}
    translation_response = await _ask_llm_async(
        litellm_model=LITELLM_MODEL_TRANSLATE,
        metadata=metadata,
        system_message=TRANSLATE_PROMPT.format(
            language=query_refined.original_language.value
        ),
        user_message=query_refined.query_text,
    )
    if translation_response != TRANSLATE_FAILED_MESSAGE:
        query_refined.query_text = translation_response  # Update text with translation
        response.debug_info["translated_question"] = translation_response
        return query_refined, response

    error_response = QueryResponseError(
        debug_info=response.debug_info,
        error_message="Unable to translate",
        error_type=ErrorType.UNABLE_TO_TRANSLATE,
        feedback_secret_key=response.feedback_secret_key,
        llm_response=response.llm_response,
        query_id=response.query_id,
        search_results=response.search_results,
        session_id=response.session_id,
    )
    error_response.debug_info.update(response.debug_info)
    logger.info("TRANSLATION FAILED on query id: " + str(response.query_id))

    return query_refined, error_response


def classify_safety__before(func: Callable) -> Callable:
    """Decorator to classify the safety of the question.

    Parameters
    ----------
    func
        The function to be decorated.

    Returns
    -------
    Callable
        The decorated function.
    """

    @wraps(func)
    async def wrapper(
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """Wrapper function to classify the safety of the question.

        Parameters
        ----------
        query_refined
            The refined query object.
        response
            The response object.
        args
            Additional positional arguments.
        kwargs
            Additional keyword arguments.

        Returns
        -------
        QueryResponse | QueryResponseError
            The appropriate response object.
        """

        query_refined, response = await _classify_safety(
            query_refined=query_refined, response=response
        )
        response = await func(query_refined, response, *args, **kwargs)
        return response

    return wrapper


async def _classify_safety(
    *,
    metadata: Optional[dict] = None,
    query_refined: QueryRefined,
    response: QueryResponse | QueryResponseError,
) -> tuple[QueryRefined, QueryResponse | QueryResponseError]:
    """Classify the safety of the question.

    Parameters
    ----------
    metadata
        The metadata to be used.
    query_refined
        The refined query object.
    response
        The response object.

    Returns
    -------
    tuple[QueryRefined, QueryResponse | QueryResponseError]
        The refined query object and the appropriate response object.
    """

    if isinstance(response, QueryResponseError):
        return query_refined, response

    metadata = metadata or {}
    llm_classified_safety = await _ask_llm_async(
        litellm_model=LITELLM_MODEL_SAFETY,
        metadata=metadata,
        system_message=SafetyClassification.get_prompt(),
        user_message=query_refined.query_text,
    )
    safety_classification = getattr(SafetyClassification, llm_classified_safety)
    if safety_classification == SafetyClassification.SAFE:
        response.debug_info["safety_classification"] = safety_classification.value
        return query_refined, response

    error_response = QueryResponseError(
        debug_info=response.debug_info,
        error_message=f"{safety_classification.value.lower()} found.",
        error_type=ErrorType.QUERY_UNSAFE,
        feedback_secret_key=response.feedback_secret_key,
        llm_response=response.llm_response,
        query_id=response.query_id,
        search_results=response.search_results,
        session_id=response.session_id,
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
    """Decorator to paraphrase the question.

    NB: There is no need to paraphrase the search query for the search response if chat
    is being used since the chat endpoint first constructs the search query using the
    latest user message and the conversation history from the user assistant chat.

    Parameters
    ----------
    func
        The function to be decorated.

    Returns
    -------
    Callable
        The decorated function.
    """

    @wraps(func)
    async def wrapper(
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """Wrapper function to paraphrase the question.

        Parameters
        ----------
        query_refined
            The refined query object.
        response
            The response object.
        args
            Additional positional arguments.
        kwargs
            Additional keyword arguments.

        Returns
        -------
        QueryResponse | QueryResponseError
            The appropriate response object.
        """

        query_refined, response = await _paraphrase_question(
            query_refined=query_refined, response=response
        )
        response = await func(query_refined, response, *args, **kwargs)

        return response

    return wrapper


async def _paraphrase_question(
    *,
    metadata: Optional[dict] = None,
    query_refined: QueryRefined,
    response: QueryResponse | QueryResponseError,
) -> tuple[QueryRefined, QueryResponse | QueryResponseError]:
    """Paraphrase the question. If it is unable to identify the question, it will
    return the original sentence.

    Parameters
    ----------
    metadata
        The metadata to be used.
    query_refined
        The refined query object.
    response
        The response object.

    Returns
    -------
    tuple[QueryRefined, QueryResponse | QueryResponseError]
        The refined query object and the appropriate response object.
    """

    if isinstance(response, QueryResponseError):
        return query_refined, response

    metadata = metadata or {}
    paraphrase_response = await _ask_llm_async(
        litellm_model=LITELLM_MODEL_PARAPHRASE,
        metadata=metadata,
        system_message=PARAPHRASE_PROMPT,
        user_message=query_refined.query_text,
    )
    if paraphrase_response != PARAPHRASE_FAILED_MESSAGE:
        query_refined.query_text = paraphrase_response  # Update text with paraphrase
        response.debug_info["paraphrased_question"] = paraphrase_response
        return query_refined, response

    error_response = QueryResponseError(
        debug_info=response.debug_info,
        error_message="Unable to paraphrase the query.",
        error_type=ErrorType.UNABLE_TO_PARAPHRASE,
        feedback_secret_key=response.feedback_secret_key,
        llm_response=response.llm_response,
        query_id=response.query_id,
        search_results=response.search_results,
        session_id=response.session_id,
    )
    logger.info(
        (
            f"PARAPHRASE FAILED on query id:  {str(response.query_id)} "
            f"for query text: {query_refined.query_text}"
        )
    )
    return query_refined, error_response
