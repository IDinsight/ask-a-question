import asyncio
from typing import Callable

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import auth_bearer_token
from ..database import get_async_session
from ..llm_call.entailment import detect_urgency
from ..urgency_rules.models import (
    get_cosine_distances_from_rules,
    get_urgency_rules_from_db,
)
from ..utils import generate_secret_key
from .config import (
    URGENCY_CLASSIFIER,
    URGENCY_DETECTION_MAX_DISTANCE,
    URGENCY_DETECTION_MIN_PROBABILITY,
)
from .models import save_urgency_query_to_db, save_urgency_response_to_db
from .schemas import UrgencyQuery, UrgencyResponse

router = APIRouter(
    dependencies=[Depends(auth_bearer_token)], tags=["Urgency Detection"]
)

ALL_URGENCY_CLASSIFIERS = {}


def urgency_classifier(classifier_func: Callable) -> Callable:
    """
    Decorator to register classifier functions
    """
    ALL_URGENCY_CLASSIFIERS[classifier_func.__name__] = classifier_func
    return classifier_func


@router.post("/urgency-detect", response_model=UrgencyResponse)
async def classify_text(
    urgency_query: UrgencyQuery, asession: AsyncSession = Depends(get_async_session)
) -> UrgencyResponse:
    """
    Classify the urgency of a text message
    """
    feedback_secret_key = generate_secret_key()
    urgency_query_db = await save_urgency_query_to_db(
        feedback_secret_key, urgency_query, asession
    )

    classifier = ALL_URGENCY_CLASSIFIERS.get(URGENCY_CLASSIFIER)
    if not classifier:
        raise ValueError(f"Invalid urgency classifier: {URGENCY_CLASSIFIER}")

    urgency_response = await classifier(asession, urgency_query)

    await save_urgency_response_to_db(urgency_query_db, urgency_response, asession)

    return urgency_response


@urgency_classifier
async def cosine_distance_classifier(
    asession: AsyncSession, urgency_query: UrgencyQuery
) -> UrgencyResponse:
    """
    Classify the urgency of a text message using cosine distance
    """

    cosine_distances = await get_cosine_distances_from_rules(
        asession, urgency_query.message_text
    )
    failed_rules = []
    for _, rule in cosine_distances.items():
        if float(rule["distance"]) < float(URGENCY_DETECTION_MAX_DISTANCE):
            failed_rules.append(str(rule["urgency_rule"]))

    if failed_rules:
        return UrgencyResponse(
            is_urgent=True, failed_rules=failed_rules, details=cosine_distances
        )

    return UrgencyResponse(
        is_urgent=False,
        failed_rules=failed_rules,
        details=cosine_distances,
    )


@urgency_classifier
async def llm_entailment_classifier(
    asession: AsyncSession,
    urgency_query: UrgencyQuery,
) -> UrgencyResponse:
    """
    Classify the urgency of a text message using LLM entailment
    """

    rules = await get_urgency_rules_from_db(asession)
    tasks = []
    for rule in rules:
        tasks.append(detect_urgency(rule.urgency_rule_text, urgency_query.message_text))

    results = await asyncio.gather(*tasks)
    results_dict = {str(i): result for i, result in enumerate(results)}
    failed_rules = []
    for result in results:
        if float(result["probability"]) > float(URGENCY_DETECTION_MIN_PROBABILITY):
            failed_rules.append(str(result["statement"]))

    if failed_rules:
        return UrgencyResponse(
            is_urgent=True, failed_rules=failed_rules, details=results_dict
        )

    return UrgencyResponse(
        is_urgent=False, failed_rules=failed_rules, details=results_dict
    )
