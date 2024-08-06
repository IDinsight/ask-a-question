"""
These are functions to check the LLM response
"""

from functools import wraps
from typing import Any, Callable, Optional, TypedDict

import aiohttp
from pydantic import ValidationError

from ..config import (
    ALIGN_SCORE_API,
    ALIGN_SCORE_METHOD,
    ALIGN_SCORE_THRESHOLD,
    LITELLM_MODEL_ALIGNSCORE,
)
from ..question_answer.schemas import (
    ErrorType,
    QueryRefined,
    QueryResponse,
    QueryResponseError,
)
from ..question_answer.utils import get_context_string_from_search_results
from ..utils import create_langfuse_metadata, get_http_client, setup_logger
from .llm_prompts import RAG_FAILURE_MESSAGE, AlignmentScore
from .llm_rag import get_llm_rag_answer
from .utils import (
    _ask_llm_async,
    remove_json_markdown,
)

logger = setup_logger("OUTPUT RAILS")


class AlignScoreData(TypedDict):
    """
    Payload for the AlignScore API
    """

    evidence: str
    claim: str


def generate_llm_response__after(func: Callable) -> Callable:
    """
    Decorator to generate the LLM response.

    Only runs if the generate_llm_response flag is set to True.
    Requires "search_results" and "original_language" in the response.
    """

    @wraps(func)
    async def wrapper(
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """
        Generate the LLM response
        """
        response = await func(query_refined, response, *args, **kwargs)

        if not query_refined.generate_llm_response:
            return response

        metadata = create_langfuse_metadata(
            query_id=response.query_id, user_id=query_refined.user_id
        )
        response = await _generate_llm_response(query_refined, response, metadata)
        return response

    return wrapper


async def _generate_llm_response(
    query_refined: QueryRefined,
    response: QueryResponse,
    metadata: Optional[dict] = None,
) -> QueryResponse:
    """
    Generate the LLM response.

    Only runs if the generate_llm_response flag is set to True.
    Requires "search_results" and "original_language" in the response.
    """
    if isinstance(response, QueryResponseError):
        return response

    if response.search_results is None:
        logger.warning("No search_results found in the response.")
        return response
    if query_refined.original_language is None:
        logger.warning("No original_language found in the query.")
        return response

    context = get_context_string_from_search_results(response.search_results)
    rag_response = await get_llm_rag_answer(
        # use the original query text
        question=query_refined.query_text_original,
        context=context,
        original_language=query_refined.original_language,
        metadata=metadata,
    )

    if rag_response.answer != RAG_FAILURE_MESSAGE:
        response.debug_info["extracted_info"] = rag_response.extracted_info
        response.llm_response = rag_response.answer
    else:
        response = QueryResponseError(
            query_id=response.query_id,
            feedback_secret_key=response.feedback_secret_key,
            llm_response=None,
            search_results=response.search_results,
            debug_info=response.debug_info,
            error_type=ErrorType.UNABLE_TO_GENERATE_RESPONSE,
            error_message="LLM failed to generate an answer.",
        )
        response.debug_info["extracted_info"] = rag_response.extracted_info
        response.llm_response = None

    return response


def check_align_score__after(func: Callable) -> Callable:
    """
    Check the alignment score.

    Only runs if the generate_llm_response flag is set to True.
    Requires "llm_response" and "search_results" in the response.
    """

    @wraps(func)
    async def wrapper(
        query_refined: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """
        Check the alignment score
        """

        response = await func(query_refined, response, *args, **kwargs)

        if not kwargs.get("generate_llm_response", False):
            return response

        metadata = create_langfuse_metadata(
            query_id=response.query_id, user_id=query_refined.user_id
        )
        response = await _check_align_score(response, metadata)
        return response

    return wrapper


async def _check_align_score(
    response: QueryResponse,
    metadata: Optional[dict] = None,
) -> QueryResponse:
    """
    Check the alignment score

    Only runs if the generate_llm_response flag is set to True.
    Requires "llm_response" and "search_results" in the response.
    """
    if isinstance(response, QueryResponseError) or response.llm_response is None:
        return response

    if response.search_results is not None:
        evidence = get_context_string_from_search_results(response.search_results)
    else:
        logger.warning(("No search_results found in the response."))
        return response

    if response.llm_response is not None:
        claim = response.llm_response
    else:
        logger.warning(("No llm_response found in the response."))
        return response

    align_score_data = AlignScoreData(evidence=evidence, claim=claim)

    if ALIGN_SCORE_METHOD is None:
        logger.warning("No alignment score method specified.")
        return response
    elif ALIGN_SCORE_METHOD == "AlignScore":
        if ALIGN_SCORE_API is not None:
            align_score = await _get_alignScore_score(ALIGN_SCORE_API, align_score_data)
        else:
            raise ValueError("Method is AlignScore but ALIGN_SCORE_API is not set.")
    elif ALIGN_SCORE_METHOD == "LLM":
        align_score = await _get_llm_align_score(align_score_data, metadata=metadata)
    else:
        raise NotImplementedError(f"Unknown method {ALIGN_SCORE_METHOD}")

    factual_consistency = {
        "method": ALIGN_SCORE_METHOD,
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
            query_id=response.query_id,
            feedback_secret_key=response.feedback_secret_key,
            llm_response=None,
            search_results=response.search_results,
            debug_info=response.debug_info,
            error_type=ErrorType.ALIGNMENT_TOO_LOW,
            error_message="Alignment score of LLM response was too low",
        )

    response.debug_info["factual_consistency"] = factual_consistency.copy()

    return response


async def _get_alignScore_score(
    api_url: str, align_score_date: AlignScoreData
) -> AlignmentScore:
    """
    Get the alignment score from the AlignScore API
    """
    http_client = get_http_client()
    assert isinstance(http_client, aiohttp.ClientSession)
    async with http_client.post(api_url, json=align_score_date) as resp:
        if resp.status != 200:
            logger.error(f"AlignScore API request failed with status {resp.status}")
            raise RuntimeError(
                f"AlignScore API request failed with status {resp.status}"
            )

        result = await resp.json()
    logger.info(f"AlignScore result: {result}")
    alignment_score = AlignmentScore(score=result["alignscore"], reason="N/A")

    return alignment_score


async def _get_llm_align_score(
    align_score_data: AlignScoreData, metadata: Optional[dict] = None
) -> AlignmentScore:
    """
    Get the alignment score from the LLM
    """
    prompt = AlignmentScore.prompt.format(context=align_score_data["evidence"])
    result = await _ask_llm_async(
        user_message=align_score_data["claim"],
        system_message=prompt,
        litellm_model=LITELLM_MODEL_ALIGNSCORE,
        metadata=metadata,
        json=True,
    )

    try:
        result = remove_json_markdown(result)
        alignment_score = AlignmentScore.model_validate_json(result)
    except ValidationError as e:
        logger.error(f"LLM alignment score response is not valid json: {e}")
        raise RuntimeError("LLM alignment score response is not valid json") from e

    logger.info(f"LLM Alignment result: {alignment_score.model_dump_json()}")

    return alignment_score
