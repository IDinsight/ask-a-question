"""This module contains the FastAPI router for the urgency detection endpoints."""

from typing import Callable

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import authenticate_key, rate_limiter
from ..database import get_async_session
from ..llm_call.entailment import detect_urgency
from ..urgency_rules.models import (
    get_cosine_distances_from_rules,
    get_urgency_rules_from_db,
)
from ..users.models import UserDB
from ..utils import generate_secret_key, setup_logger
from .config import (
    URGENCY_CLASSIFIER,
    URGENCY_DETECTION_MAX_DISTANCE,
    URGENCY_DETECTION_MIN_PROBABILITY,
)
from .models import save_urgency_query_to_db, save_urgency_response_to_db
from .schemas import UrgencyQuery, UrgencyResponse

TAG_METADATA = {
    "name": "Urgency detection",
    "description": "_Requires API key._ Detect urgent messages according to "
    "urgency rules.",
}

logger = setup_logger()
router = APIRouter(
    dependencies=[Depends(authenticate_key), Depends(rate_limiter)],
    tags=[TAG_METADATA["name"]],
)

ALL_URGENCY_CLASSIFIERS = {}


def urgency_classifier(classifier_func: Callable) -> Callable:
    """Decorator to register classifier functions.

    Parameters
    ----------
    classifier_func
        The classifier function to register.

    Returns
    -------
    Callable
        The classifier function.
    """

    ALL_URGENCY_CLASSIFIERS[classifier_func.__name__] = classifier_func
    return classifier_func


@router.post("/urgency-detect", response_model=UrgencyResponse)
async def classify_text(
    urgency_query: UrgencyQuery,
    asession: AsyncSession = Depends(get_async_session),
    user_db: UserDB = Depends(authenticate_key),
) -> UrgencyResponse:
    """
    Classify the urgency of a text message
    """
    feedback_secret_key = generate_secret_key()
    urgency_query_db = await save_urgency_query_to_db(
        user_id=user_db.user_id,
        feedback_secret_key=feedback_secret_key,
        urgency_query=urgency_query,
        asession=asession,
    )

    classifier = ALL_URGENCY_CLASSIFIERS.get(URGENCY_CLASSIFIER)
    if not classifier:
        raise ValueError(f"Invalid urgency classifier: {URGENCY_CLASSIFIER}")

    urgency_response = await classifier(
        user_id=user_db.user_id, urgency_query=urgency_query, asession=asession
    )

    await save_urgency_response_to_db(
        urgency_query_db=urgency_query_db,
        response=urgency_response,
        asession=asession,
    )

    return urgency_response


@urgency_classifier
async def cosine_distance_classifier(
    user_id: int,
    urgency_query: UrgencyQuery,
    asession: AsyncSession,
) -> UrgencyResponse:
    """Classify the urgency of a text message using cosine distance.

    Parameters
    ----------
    user_id
        The ID of the user requesting to classify the urgency of the text message.
    urgency_query
        The urgency query to classify.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    UrgencyResponse
        The urgency response object.
    """

    cosine_distances = await get_cosine_distances_from_rules(
        user_id=user_id,
        message_text=urgency_query.message_text,
        asession=asession,
    )
    matched_rules = []
    for rule in cosine_distances.values():
        if float(rule.distance) < float(URGENCY_DETECTION_MAX_DISTANCE):
            matched_rules.append(str(rule.urgency_rule))

    return UrgencyResponse(
        is_urgent=len(matched_rules) > 0,
        matched_rules=matched_rules,
        details=cosine_distances,
    )


@urgency_classifier
async def llm_entailment_classifier(
    user_id: int,
    urgency_query: UrgencyQuery,
    asession: AsyncSession,
) -> UrgencyResponse:
    """Classify the urgency of a text message using LLM entailment.

    Parameters
    ----------
    user_id
        The ID of the user requesting to classify the urgency of the text message.
    urgency_query
        The urgency query to classify.
    asession
        `AsyncSession` object for database transactions.

    Returns
    -------
    UrgencyResponse
        The urgency response object.
    """

    rules = await get_urgency_rules_from_db(user_id=user_id, asession=asession)
    metadata = {"trace_user_id": "user_id-" + str(user_id)}
    urgency_rules = [rule.urgency_rule_text for rule in rules]

    if len(urgency_rules) == 0:
        return UrgencyResponse(is_urgent=False, matched_rules=[], details={})

    result = await detect_urgency(
        urgency_rules=urgency_rules,
        message=urgency_query.message_text,
        metadata=metadata,
    )

    if result.probability > float(URGENCY_DETECTION_MIN_PROBABILITY):
        return UrgencyResponse(
            is_urgent=True, matched_rules=[result.best_matching_rule], details=result
        )

    return UrgencyResponse(is_urgent=False, matched_rules=[], details=result)
