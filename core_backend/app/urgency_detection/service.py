"""Business logic for urgency detection.

Holds the classifier registry (`ALL_URGENCY_CLASSIFIERS`), the cosine-distance and
LLM-entailment classifiers, the LLM entailment prompt, and `classify_urgency`, which
runs the configured classifier and persists the query and its response.
"""

from __future__ import annotations

import re
import textwrap
from typing import Callable, Optional

from langfuse.decorators import langfuse_context  # type: ignore
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    LITELLM_MODEL_URGENCY_DETECT,
    URGENCY_CLASSIFIER,
    URGENCY_DETECTION_MAX_DISTANCE,
    URGENCY_DETECTION_MIN_PROBABILITY,
)
from app.core.observability import setup_logger
from app.core.security import generate_secret_key
from app.core.utils import ask_llm_async, remove_json_markdown
from app.urgency_detection.repository import (
    save_urgency_query_to_db,
    save_urgency_response_to_db,
)
from app.urgency_detection.schemas import (
    UrgencyDetectionEntailmentResult,
    UrgencyQuery,
    UrgencyResponse,
)
from app.urgency_rules.repository import (
    get_cosine_distances_from_rules,
    get_urgency_rules_from_db,
)

logger = setup_logger()

# Registry of classifier functions keyed by function name. `URGENCY_CLASSIFIER` in
# the config picks which one `classify_urgency` uses.
ALL_URGENCY_CLASSIFIERS = {}


# ---------------------------------------------------------------------------
# LLM entailment prompt and call
# ---------------------------------------------------------------------------
class UrgencyDetectionEntailment:
    """Urgency detection using entailment."""

    # The result model lives in `schemas.py` (it is part of `UrgencyResponse`); it is
    # re-exposed here so `UrgencyDetectionEntailment.UrgencyDetectionEntailmentResult`
    # keeps working.
    UrgencyDetectionEntailmentResult = UrgencyDetectionEntailmentResult

    _urgency_rules: list[str]
    _prompt_base: str = textwrap.dedent(
        """
        You are a highly sensitive urgency detector. Score if ANY part of the
        user message corresponds to any part of the urgency rules provided below.
        Ignore any part of the user message that does not correspond to the rules.
        Respond with (a) the rule that is most consistent with the user message,
        (b) the probability between 0 and 1 with increments of 0.1 that ANY part of
        the user message matches the rule, and (c) the reason for the probability.


        Respond in json string:

        {
           best_matching_rule: str
           probability: float
           reason: str
        }
        """
    ).strip()

    _prompt_rules: str = textwrap.dedent(
        """
        Urgency Rules:
        {urgency_rules}
        """
    ).strip()

    default_json: dict = {
        "best_matching_rule": "",
        "probability": 0.0,
        "reason": "",
    }

    def __init__(self, *, urgency_rules: list[str]) -> None:
        """Initialize the urgency detection entailment task with urgency rules.

        Parameters
        ----------
        urgency_rules
            The list of urgency rules.
        """

        self._urgency_rules = urgency_rules

    def parse_json(self, *, json_str: str) -> dict:
        """Validate the output of the urgency detection entailment task.

        Parameters
        ----------
        json_str
            The JSON string to validate.

        Returns
        -------
        dict
            The validated JSON response.

        Raises
        ------
        ValueError
            If the best matching rule is not in the urgency rules provided.
        """

        json_str = remove_json_markdown(text=json_str)

        # fmt: off
        ud_entailment_result = UrgencyDetectionEntailment.UrgencyDetectionEntailmentResult.model_validate_json(json_str)  # noqa: E501
        # fmt: on

        # TODO: This is a temporary fix to remove the number  # pylint: disable=W0511
        #  and the dot from the rule returned by the LLM.
        ud_entailment_result.best_matching_rule = re.sub(
            r"^\d+\.\s", "", ud_entailment_result.best_matching_rule
        )

        if ud_entailment_result.best_matching_rule not in self._urgency_rules:
            raise ValueError(
                (
                    f"Best_matching_rule {ud_entailment_result.best_matching_rule} is "
                    f"not in the urgency rules provided."
                )
            )

        return ud_entailment_result.model_dump()

    def get_prompt(self) -> str:
        """Return the prompt for the urgency detection entailment task.

        Returns
        -------
        str
            The prompt for the urgency detection entailment task.
        """

        urgency_rules_str = "\n".join(
            [f"{i+1}. {rule}" for i, rule in enumerate(self._urgency_rules)]
        )

        prompt = (
            self._prompt_base
            + "\n\n"
            + self._prompt_rules.format(urgency_rules=urgency_rules_str)
        )

        return prompt


async def detect_urgency(
    *, message: str, metadata: Optional[dict] = None, urgency_rules: list[str]
) -> UrgencyDetectionEntailmentResult:
    """Detects the urgency of a message based on a set of urgency rules.

    Parameters
    ----------
    message
        The message to detect the urgency of.
    metadata
        Additional metadata to pass to the LLM model.
    urgency_rules
        A list of urgency rules.

    Returns
    -------
    UrgencyDetectionEntailment.UrgencyDetectionEntailmentResult
        The urgency detection result.
    """

    ud_entailment = UrgencyDetectionEntailment(urgency_rules=urgency_rules)
    prompt = ud_entailment.get_prompt()

    json_str = await ask_llm_async(
        json_=True,
        litellm_model=LITELLM_MODEL_URGENCY_DETECT,
        metadata=metadata,
        system_message=prompt,
        user_message=message,
    )

    try:
        parsed_json = ud_entailment.parse_json(json_str=json_str)
    except (ValidationError, ValueError) as e:
        logger.warning(f"JSON Decode failed. json_str: {json_str}. Exception: {e}")
        parsed_json = ud_entailment.default_json

    return UrgencyDetectionEntailment.UrgencyDetectionEntailmentResult(**parsed_json)


# ---------------------------------------------------------------------------
# Classifiers
# ---------------------------------------------------------------------------
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
    # A rule matches when the message is closer to it than the configured threshold.
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

    # No rules means nothing can match, so skip the LLM call.
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


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
async def classify_urgency(
    *, asession: AsyncSession, urgency_query: UrgencyQuery, workspace_id: int
) -> UrgencyResponse:
    """Save an urgency query, classify it with the configured classifier, and save
    the response.

    Must run inside a Langfuse-observed call: it tags the current trace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    urgency_query
        The urgency query to classify.
    workspace_id
        The ID of the workspace the query belongs to.

    Returns
    -------
    UrgencyResponse
        The urgency response object.

    Raises
    ------
    ValueError
        If the urgency classifier is invalid.
    """

    # The query is saved before classification so it is recorded even if the
    # classifier is misconfigured or fails.
    feedback_secret_key = generate_secret_key()
    urgency_query_db = await save_urgency_query_to_db(
        asession=asession,
        feedback_secret_key=feedback_secret_key,
        urgency_query=urgency_query,
        workspace_id=workspace_id,
    )

    classifier = ALL_URGENCY_CLASSIFIERS.get(URGENCY_CLASSIFIER)
    if not classifier:
        raise ValueError(f"Invalid urgency classifier: {URGENCY_CLASSIFIER}")

    urgency_response = await classifier(
        asession=asession,
        urgency_query=urgency_query,
        workspace_id=workspace_id,
    )

    langfuse_context.update_current_trace(
        name="urgency_detection",
        metadata={
            "urgency_query_id": urgency_query_db.urgency_query_id,
            "workspace_id": workspace_id,
        },
    )

    await save_urgency_response_to_db(
        asession=asession, response=urgency_response, urgency_query_db=urgency_query_db
    )

    return urgency_response
