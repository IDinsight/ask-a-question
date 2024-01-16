"""
These are functions to check the LLM response
"""
from functools import wraps
from typing import Any, Callable, TypedDict

from pydantic import ValidationError

from ..configs.app_config import (
    ALIGN_SCORE_API,
    ALIGN_SCORE_METHOD,
    ALIGN_SCORE_THRESHOLD,
)
from ..configs.llm_prompts import AlignmentScore
from ..schemas import ResultState, UserQueryRefined, UserQueryResponse
from ..utils import get_http_client, setup_logger
from .utils import _ask_llm_async

logger = setup_logger("OUTPUT RAILS")

STANDARD_FAILURE_MESSAGE = (
    "Sorry, I am unable to find an answer to your question in my knowledge base."
    "Please rephrase your question and ask a different one."
)


class Payload(TypedDict):
    """
    Payload for the AlignScore API
    """

    evidence: str
    claim: str


def check_align_score(func: Callable) -> Callable:
    """
    Check the alignment score
    """

    @wraps(func)
    async def wrapper(
        question: UserQueryRefined,
        response: UserQueryResponse,
        *args: Any,
        **kwargs: Any,
    ) -> UserQueryResponse:
        """
        Check the alignment score
        """

        llm_response = await func(question, response, *args, **kwargs)
        if (
            llm_response.state != ResultState.ERROR
            and llm_response.llm_response is not None
        ):
            llm_response = await _check_align_score(llm_response)
        return llm_response

    return wrapper


async def _check_align_score(llm_response: UserQueryResponse) -> UserQueryResponse:
    """
    Check the alignment score
    """
    evidence = _build_evidence(llm_response)
    claim = llm_response.llm_response
    if claim is not None:
        payload = Payload(evidence=evidence, claim=claim)

        if ALIGN_SCORE_METHOD is None:
            logger.warning(
                "No alignment score method specified but `check_align_score` was called"
            )
            return llm_response

        elif ALIGN_SCORE_METHOD == "AlignScore":
            align_score = await _get_alignScore_score(ALIGN_SCORE_API, payload)
        elif ALIGN_SCORE_METHOD == "LLM":
            align_score = await _get_llm_align_score(payload)
        else:
            raise NotImplementedError(f"Unknown method {ALIGN_SCORE_METHOD}")

        if align_score.score < float(ALIGN_SCORE_THRESHOLD):
            llm_response.llm_response = STANDARD_FAILURE_MESSAGE
            llm_response.state = ResultState.ERROR

        llm_response.debug_info["factual_consistency"] = {
            "method": ALIGN_SCORE_METHOD,
            "score": align_score.score,
            "reason": align_score.reason,
        }
    else:
        logger.warning(
            (
                "No LLM response found in the LLM response but "
                "`check_align_score` was called"
            )
        )
    return llm_response


async def _get_alignScore_score(api_url: str, payload: Payload) -> AlignmentScore:
    """
    Get the alignment score from the AlignScore API
    """
    async with get_http_client().post(api_url, json=payload) as resp:
        if resp.status != 200:
            logger.error(f"AlignScore API request failed with status {resp.status}")
            raise RuntimeError(
                f"AlignScore API request failed with status {resp.status}"
            )

        result = await resp.json()
    logger.info(f"AlignScore result: {result}")
    alignment_score = AlignmentScore(score=result["alignscore"], reason="N/A")

    return alignment_score


async def _get_llm_align_score(payload: Payload) -> AlignmentScore:
    """
    Get the alignment score from the LLM
    """
    prompt = AlignmentScore.prompt.format(context=payload["evidence"])
    result = await _ask_llm_async(prompt, payload["claim"])

    try:
        alignment_score = AlignmentScore.model_validate_json(result)
    except ValidationError as e:
        logger.error(f"LLM alignment score respone is not valid json: {e}")

    logger.info(f"LLM Alignment result: {alignment_score.model_dump_json()}")

    return alignment_score


def _build_evidence(llm_response: UserQueryResponse) -> str:
    """
    Build the evidence used by the LLM response
    """
    evidence = ""
    if llm_response.content_response is not None:
        for _, result in llm_response.content_response.items():
            evidence += result.response_text + "\n"
    return evidence
