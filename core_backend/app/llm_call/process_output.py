"""This module contains functions for checking LLM responses."""

from functools import wraps
from typing import Any, Callable, Optional, TypedDict

from pydantic import ValidationError

from ..config import (
    ALIGN_SCORE_THRESHOLD,
    CUSTOM_TTS_ENDPOINT,
    GCS_SPEECH_BUCKET,
    LITELLM_MODEL_ALIGNSCORE,
)
from ..question_answer.schemas import (
    ErrorType,
    QueryAudioResponse,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
)
from ..question_answer.speech_components.external_voice_components import (
    synthesize_speech,
)
from ..question_answer.speech_components.utils import post_to_internal_tts
from ..question_answer.utils import get_context_string_from_search_results
from ..utils import (
    create_langfuse_metadata,
    generate_public_url,
    generate_random_filename,
    get_file_extension_from_mime_type,
    setup_logger,
    upload_file_to_gcs,
)
from .llm_prompts import RAG_FAILURE_MESSAGE, AlignmentScore
from .llm_rag import get_llm_rag_answer, get_llm_rag_answer_with_chat_history
from .utils import _ask_llm_async, remove_json_markdown

logger = setup_logger(name="OUTPUT RAILS")


class AlignScoreData(TypedDict):
    """Payload for the AlignScore API."""

    claim: str
    evidence: str


async def generate_llm_query_response(
    *,
    metadata: Optional[dict] = None,
    query_refined: QueryRefined,
    response: QueryResponse,
) -> tuple[QueryResponse | QueryResponseError, list[Any]]:
    """Generate the LLM response. If `chat_query_params` is provided, then the response
    is generated based on the chat history.

    Only runs if the `generate_llm_response` flag is set to `True`.

    Requires "search_results" and "original_language" in the response.

    Parameters
    ----------
    metadata
        Additional metadata to provide to the LLM model.
    query_refined
        The refined query object.
    response
        The query response object.

    Returns
    -------
    tuple[QueryResponse | QueryResponseError, list[Any]]
        The updated response object and the chat history.
    """

    chat_query_params = query_refined.chat_query_params or {}
    chat_history = chat_query_params.get("chat_history", [])
    if isinstance(response, QueryResponseError):
        logger.warning("LLM generation skipped due to QueryResponseError.")
        return response, chat_history
    if response.search_results is None:
        logger.warning("No search_results found in the response.")
        return response, chat_history
    if query_refined.original_language is None:
        logger.warning("No original_language found in the query.")
        return response, chat_history

    context = get_context_string_from_search_results(
        search_results=response.search_results
    )
    if chat_query_params:
        message_type = chat_query_params["message_type"]
        response.message_type = message_type
        rag_response, chat_history = await get_llm_rag_answer_with_chat_history(
            chat_history=chat_history,
            chat_params=chat_query_params["chat_params"],
            context=context,
            message_type=message_type,
            metadata=metadata,
            original_language=query_refined.original_language,
            question=query_refined.query_text_original,
            session_id=chat_query_params["session_id"],
        )
    else:
        rag_response = await get_llm_rag_answer(
            context=context,
            metadata=metadata,
            original_language=query_refined.original_language,
            question=query_refined.query_text_original,  # Use the original query text
        )

    if rag_response.answer != RAG_FAILURE_MESSAGE:
        response.debug_info["extracted_info"] = rag_response.extracted_info
        response.llm_response = rag_response.answer
    else:
        response = QueryResponseError(
            debug_info=response.debug_info,
            error_message="LLM failed to generate an answer.",
            error_type=ErrorType.UNABLE_TO_GENERATE_RESPONSE,
            feedback_secret_key=response.feedback_secret_key,
            llm_response=None,
            query_id=response.query_id,
            search_results=response.search_results,
            session_id=response.session_id,
        )
        response.debug_info["extracted_info"] = rag_response.extracted_info
        response.llm_response = None

    return response, chat_history


def check_align_score__after(func: Callable) -> Callable:
    """Decorator to check the alignment score.

    Only runs if the `generate_llm_response` flag is set to `True`.

    Requires "llm_response" and "search_results" in the response.

    Parameters
    ----------
    func
        The function to wrap.

    Returns
    -------
    Callable
        The wrapped function.
    """

    @wraps(func)
    async def wrapper(
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """Check the alignment score.

        Parameters
        ----------
        query_refined
            The refined query object.
        response
            The query response object.
        args
            Additional positional arguments.
        kwargs
            Additional keyword arguments.

        Returns
        -------
        QueryResponse | QueryResponseError
            The updated response object.
        """

        response = await func(query_refined, response, *args, **kwargs)

        if not query_refined.generate_llm_response:
            return response

        metadata = create_langfuse_metadata(
            workspace_id=query_refined.workspace_id, session_id=query_refined.session_id
        )
        response = await _check_align_score(metadata=metadata, response=response)
        return response

    return wrapper


async def _check_align_score(
    *, metadata: Optional[dict] = None, response: QueryResponse
) -> QueryResponse:
    """Check the alignment score.

    Only runs if the `generate_llm_response` flag is set to `True`.

    Requires "llm_response" and "search_results" in the response.

    Parameters
    ----------
    metadata
        The metadata to be used.
    response
        The query response object.

    Returns
    -------
    QueryResponse
        The updated response object.
    """

    if isinstance(response, QueryResponseError):
        logger.warning("Alignment score check skipped due to QueryResponseError.")
        return response

    if response.search_results is not None:
        evidence = get_context_string_from_search_results(
            search_results=response.search_results
        )
    else:
        logger.warning("No search_results found in the response.")
        return response

    if response.llm_response is not None:
        claim = response.llm_response
    else:
        logger.warning(
            "No llm_response found in the response "
            "(should have been caught with QueryResponseError)."
        )
        return response

    align_score_data = AlignScoreData(claim=claim, evidence=evidence)
    align_score = await _get_llm_align_score(
        align_score_data=align_score_data, metadata=metadata
    )

    factual_consistency = {
        "score": align_score.score,
        "reason": align_score.reason,
        "claim": claim,
    }

    if align_score.score < float(ALIGN_SCORE_THRESHOLD):
        logger.info(
            (
                f"Alignment score {align_score.score} is below the threshold "
                f"{ALIGN_SCORE_THRESHOLD}.\n"
                f"Reason: {align_score.reason}\n"
                f"Claim: {claim}\n"
                f"Evidence: {evidence}\n"
            )
        )
        response = QueryResponseError(
            debug_info=response.debug_info,
            error_message="Alignment score of LLM response was too low",
            error_type=ErrorType.ALIGNMENT_TOO_LOW,
            feedback_secret_key=response.feedback_secret_key,
            llm_response=None,
            query_id=response.query_id,
            search_results=response.search_results,
            session_id=response.session_id,
        )

    response.debug_info["factual_consistency"] = factual_consistency.copy()

    return response


async def _get_llm_align_score(
    *, align_score_data: AlignScoreData, metadata: Optional[dict] = None
) -> AlignmentScore:
    """Get the alignment score from the LLM.

    Parameters
    ----------
    align_score_data
        The data to be used for the alignment score.
    metadata
        The metadata to be used.

    Returns
    -------
    AlignmentScore
        The alignment score object.

    Raises
    ------
    RuntimeError
        If the LLM alignment score response is not valid JSON.
    """

    prompt = AlignmentScore.prompt.format(context=align_score_data["evidence"])
    result = await _ask_llm_async(
        json_=True,
        litellm_model=LITELLM_MODEL_ALIGNSCORE,
        metadata=metadata,
        system_message=prompt,
        user_message=align_score_data["claim"],
    )

    try:
        result = remove_json_markdown(text=result)
        alignment_score = AlignmentScore.model_validate_json(result)
    except ValidationError as e:
        logger.error(f"LLM alignment score response is not valid json: {e}")
        raise RuntimeError("LLM alignment score response is not valid json") from e

    logger.info(f"LLM Alignment result: {alignment_score.model_dump_json()}")

    return alignment_score


def generate_tts__after(func: Callable) -> Callable:
    """Decorator to generate the TTS response.

    Only runs if the `generate_tts` flag is set to `True`.

    Requires "llm_response" and alignment score is present in the response.

    Parameters
    ----------
    func
        The function to wrap.

    Returns
    -------
    Callable
        The wrapped function.
    """

    @wraps(func)
    async def wrapper(
        query_refined: QueryRefined,
        response: QueryAudioResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryAudioResponse | QueryResponseError:
        """Wrapper function to check conditions before generating TTS.

        Parameters
        ----------
        query_refined
            The refined query object.
        response
            The query response object.
        args
            Additional positional arguments.
        kwargs
            Additional keyword arguments.

        Returns
        -------
        QueryAudioResponse | QueryResponseError
            The updated response object.
        """

        response = await func(query_refined, response, *args, **kwargs)

        if not query_refined.generate_tts:
            return response

        if isinstance(response, QueryResponseError):
            logger.warning("TTS generation skipped due to QueryResponseError.")
            return response

        if isinstance(response, QueryResponse):
            logger.info("Converting response type QueryResponse to AudioResponse.")
            response = QueryAudioResponse(
                debug_info=response.debug_info,
                feedback_secret_key=response.feedback_secret_key,
                llm_response=response.llm_response,
                query_id=response.query_id,
                search_results=response.search_results,
                session_id=response.session_id,
                tts_filepath=None,
            )

        response = await _generate_tts_response(
            query_refined=query_refined, response=response
        )

        return response

    return wrapper


async def _generate_tts_response(
    *, query_refined: QueryRefined, response: QueryAudioResponse
) -> QueryAudioResponse | QueryResponseError:
    """Generate the TTS response.

    Requires valid `llm_response` and alignment score in the response.

    Parameters
    ----------
    query_refined
        The refined query object.
    response
        The query response object.

    Returns
    -------
    QueryAudioResponse | QueryResponseError
        The updated response object.

    Raises
    ------
    ValueError
        If the language is not provided.
    """

    if response.llm_response is None:
        logger.warning(
            "TTS generation skipped due to missing LLM response "
            "(should have been caught with QueryResponseError)."
        )
        return response

    try:
        if query_refined.original_language is None:
            error_msg = "Language must be provided to generate speech."
            logger.error(error_msg)
            raise ValueError(error_msg)

        if CUSTOM_TTS_ENDPOINT is not None:
            tts_file = await post_to_internal_tts(
                endpoint_url=CUSTOM_TTS_ENDPOINT,
                language=query_refined.original_language,
                text=response.llm_response,
            )

        else:
            tts_file = await synthesize_speech(
                language=query_refined.original_language, text=response.llm_response
            )

        content_type = "audio/wav"
        file_extension = get_file_extension_from_mime_type(mime_type=content_type)
        unique_filename = generate_random_filename(extension=file_extension)
        destination_blob_name = f"tts-voice-notes/{unique_filename}"

        await upload_file_to_gcs(
            bucket_name=GCS_SPEECH_BUCKET,
            content_type=content_type,
            destination_blob_name=destination_blob_name,
            file_stream=tts_file,
        )

        tts_file_path = await generate_public_url(
            blob_name=destination_blob_name, bucket_name=GCS_SPEECH_BUCKET
        )

        response.tts_filepath = tts_file_path
    except ValueError as e:
        logger.error(f"Error generating TTS for query_id {response.query_id}: {e}")
        return QueryResponseError(
            debug_info=response.debug_info,
            error_message="There was an issue generating the speech response.",
            error_type=ErrorType.TTS_ERROR,
            feedback_secret_key=response.feedback_secret_key,
            llm_response=response.llm_response,
            query_id=response.query_id,
            search_results=response.search_results,
            session_id=response.session_id,
        )

    return response
