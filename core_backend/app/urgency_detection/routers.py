"""This module contains FastAPI routers for urgency detection endpoints."""

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
from ..users.models import WorkspaceDB
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
    workspace_db: WorkspaceDB = Depends(authenticate_key),
) -> UrgencyResponse:
    """Classify the urgency of a text message.

    Parameters
    ----------
    urgency_query
        The urgency query to classify.
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_db
        The authenticated workspace object.

    Returns
    -------
    UrgencyResponse
        The urgency response object.

    Raises
    ------
    ValueError
        If the urgency classifier is invalid.
    """

    feedback_secret_key = generate_secret_key()
    urgency_query_db = await save_urgency_query_to_db(
        asession=asession,
        feedback_secret_key=feedback_secret_key,
        urgency_query=urgency_query,
        workspace_id=workspace_db.workspace_id,
    )

    classifier = ALL_URGENCY_CLASSIFIERS.get(URGENCY_CLASSIFIER)
    if not classifier:
        raise ValueError(f"Invalid urgency classifier: {URGENCY_CLASSIFIER}")

    urgency_response = await classifier(
        asession=asession,
        urgency_query=urgency_query,
        workspace_id=workspace_db.workspace_id,
    )

    await save_urgency_response_to_db(
        asession=asession, response=urgency_response, urgency_query_db=urgency_query_db
    )

    return urgency_response


@urgency_classifier
async def cosine_distance_classifier(
    *, asession: AsyncSession, urgency_query: UrgencyQuery, workspace_id: int
) -> UrgencyResponse:
    """Classify the urgency of a text message using cosine distance.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    urgency_query
        The urgency query to classify.
    workspace_id
        The ID of the workspace to classify the urgency of the text message.

    Returns
    -------
    UrgencyResponse
        The urgency response object.
    """

    cosine_distances = await get_cosine_distances_from_rules(
        asession=asession,
        message_text=urgency_query.message_text,
        workspace_id=workspace_id,
    )
    matched_rules = []
    for rule in cosine_distances.values():
        if float(rule.distance) < float(URGENCY_DETECTION_MAX_DISTANCE):
            matched_rules.append(str(rule.urgency_rule))

    return UrgencyResponse(
        details=cosine_distances,
        is_urgent=len(matched_rules) > 0,
        matched_rules=matched_rules,
    )


@urgency_classifier
async def llm_entailment_classifier(
    *, asession: AsyncSession, urgency_query: UrgencyQuery, workspace_id: int
) -> UrgencyResponse:
    """Classify the urgency of a text message using LLM entailment.

    Parameters
    ----------
    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    urgency_query
        The urgency query to classify.
    workspace_id
        The ID of the workspace to classify the urgency of the text message.

    Returns
    -------
    UrgencyResponse
        The urgency response object.
    """

    rules = await get_urgency_rules_from_db(
        asession=asession, workspace_id=workspace_id
    )
    metadata = {"trace_workspace_id": "workspace_id-" + str(workspace_id)}
    urgency_rules = [rule.urgency_rule_text for rule in rules]

    if len(urgency_rules) == 0:
        return UrgencyResponse(details={}, is_urgent=False, matched_rules=[])

    result = await detect_urgency(
        message=urgency_query.message_text,
        metadata=metadata,
        urgency_rules=urgency_rules,
    )

    if result.probability > float(URGENCY_DETECTION_MIN_PROBABILITY):
        return UrgencyResponse(
            details=result, is_urgent=True, matched_rules=[result.best_matching_rule]
        )

    return UrgencyResponse(details=result, is_urgent=False, matched_rules=[])
