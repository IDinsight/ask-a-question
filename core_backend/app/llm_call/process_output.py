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
    QueryRefined,
    QueryResponse,
    QueryResponseError,
    ResultState,
)
from ..utils import create_langfuse_metadata, get_http_client, setup_logger
from .llm_prompts import AlignmentScore
from .utils import _ask_llm_async, remove_json_markdown

logger = setup_logger("OUTPUT RAILS")


class AlignScoreData(TypedDict):
    """
    Payload for the AlignScore API
    """

    evidence: str
    claim: str


def check_align_score__after(func: Callable) -> Callable:
    """
    Check the alignment score
    """

    @wraps(func)
    async def wrapper(
        question: QueryRefined,
        response: QueryResponse | QueryResponseError,
        *args: Any,
        **kwargs: Any,
    ) -> QueryResponse | QueryResponseError:
        """
        Check the alignment score
        """

        llm_response = await func(question, response, *args, **kwargs)

        if (
            isinstance(llm_response, QueryResponseError)
            or llm_response.state == ResultState.ERROR
        ):
            return llm_response

        if llm_response.llm_response is None:
            logger.warning(
                (
                    "No LLM response found in the response but "
                    "`check_align_score` was called"
                )
            )
            return llm_response
        return await _check_align_score(llm_response)

    return wrapper


async def _check_align_score(
    llm_response: QueryResponse,
) -> QueryResponse:
    """
    Check the alignment score
    """

    evidence = _build_evidence(llm_response)
    claim = llm_response.llm_response
    assert claim is not None, "LLM response is None"
    align_score_data = AlignScoreData(evidence=evidence, claim=claim)

    if ALIGN_SCORE_METHOD is None:
        logger.warning(
            "No alignment score method specified but `check_align_score` was called"
        )
        return llm_response

    if ALIGN_SCORE_METHOD == "AlignScore":
        if ALIGN_SCORE_API is not None:
            align_score = await _get_alignScore_score(ALIGN_SCORE_API, align_score_data)
        else:
            raise ValueError("Method is AlignScore but ALIGN_SCORE_API is not set.")
    elif ALIGN_SCORE_METHOD == "LLM":
        metadata = create_langfuse_metadata(query_id=llm_response.query_id)
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
        llm_response.llm_response = None
        llm_response.state = ResultState.ERROR
        llm_response.debug_info["reason"] = "Align score failed"
    llm_response.debug_info["factual_consistency"] = factual_consistency.copy()

    return llm_response


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
        question=align_score_data["claim"],
        prompt=prompt,
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


def _build_evidence(llm_response: QueryResponse) -> str:
    """
    Build the evidence used by the LLM response
    """
    evidence = ""
    if llm_response.search_results is not None:
        for _, result in llm_response.search_results.items():
            evidence += result.text + "\n"
    return evidence
