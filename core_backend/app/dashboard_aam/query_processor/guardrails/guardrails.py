import json
from enum import Enum

from core_backend.app.config import LITELLM_MODEL_DASHBOARD

from ....llm_call.utils import _ask_llm_async
from .guardrails_prompts import (
    create_relevance_prompt,
    create_safety_prompt,
)


class GuardRailsStatus(Enum):
    """Status of the guard rails."""

    DID_NOT_RUN = "Did not run"
    PASSED = "Passed"
    IRRELEVANT = "Query Irrelevant"
    UNSAFE = "Query unsafe"


class LLMGuardRails:
    """Provides Functionality to
    run guard rails on query processing
    pipeline."""

    def __init__(
        self,
        sys_message: str,
        gurdrails_llm: str = LITELLM_MODEL_DASHBOARD,
    ) -> None:
        """Initialize the GuardRails class."""
        self.cost = 0.0
        self.guardrails_llm = gurdrails_llm
        self.system_message = sys_message
        self.temperature = 0.0
        self.guardrails_status = {
            "relevance": GuardRailsStatus.DID_NOT_RUN,
            "safety": GuardRailsStatus.DID_NOT_RUN,
        }

        self.safety_response = ""
        self.relevance_response = ""

    async def check_safety(self, query: str, language: str, script: str) -> dict:
        """
        Handle the PII in the query.
        """
        prompt = create_safety_prompt(query, language, script)
        response = await _ask_llm_async(
            question=prompt,
            prompt=self.system_message,
            litellm_model=self.guardrails_llm,
            temperature=self.temperature,
            json=True,
        )
        safety_response = json.loads(response)
        self.safe = safety_response["safe"] == "True"
        if self.safe is False:
            self.safety_response = safety_response["response"]
            self.guardrails_status["safety"] = GuardRailsStatus.UNSAFE
        else:
            self.guardrails_status["safety"] = GuardRailsStatus.PASSED

        return safety_response

    async def check_relevance(
        self, query: str, language: str, script: str, table_description: str
    ) -> dict:
        """
        Handle the relevance of the query.
        """
        prompt = create_relevance_prompt(
            query, language, script, table_description=table_description
        )
        response = await _ask_llm_async(
            question=prompt,
            prompt=self.system_message,
            litellm_model=self.guardrails_llm,
            temperature=self.temperature,
            json=True,
        )
        relevance_response = json.loads(response)
        self.relevant = relevance_response["relevant"] == "True"
        if self.relevant is False:
            self.relevance_response = relevance_response["response"]
            self.guardrails_status["relevance"] = GuardRailsStatus.IRRELEVANT
        else:
            self.guardrails_status["relevance"] = GuardRailsStatus.PASSED

        return relevance_response
