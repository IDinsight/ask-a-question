"""Unit tests for the urgency detection service layer.

No database or LLM is touched: repository functions, `ask_llm_async` and Langfuse
are replaced with mocks as imported in `app.urgency_detection.service`.
"""

import json
from typing import Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.urgency_detection.models import UrgencyQueryDB
from app.urgency_detection.schemas import (
    UrgencyDetectionEntailmentResult,
    UrgencyQuery,
    UrgencyResponse,
)
from app.urgency_detection.service import (
    ALL_URGENCY_CLASSIFIERS,
    UrgencyDetectionEntailment,
    classify_urgency,
    cosine_distance_classifier,
    # `detect_urgency` is replaced session-wide by `patch_llm_call`. Importing it
    # here (at collection time, before the patch) keeps a handle on the real one.
    detect_urgency,
    llm_entailment_classifier,
    urgency_classifier,
)
from app.urgency_rules.models import UrgencyRuleDB
from app.urgency_rules.schemas import UrgencyRuleCosineDistance

SERVICE = "app.urgency_detection.service"
RULES = ["has trouble breathing", "has a fever"]
QUERY = UrgencyQuery(message_text="My baby has a fever and is not eating.")


def _llm_json(
    *, rule: str = "has a fever", probability: float = 0.8, reason: str = "r"
) -> str:
    """Build the JSON string an LLM would return for the entailment prompt.

    Parameters
    ----------
    rule
        The best matching rule.
    probability
        The match probability.
    reason
        The reason for the probability.

    Returns
    -------
    str
        The JSON string.
    """

    return json.dumps(
        {"best_matching_rule": rule, "probability": probability, "reason": reason}
    )


@pytest.fixture
def mock_langfuse(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the Langfuse context so traces are not tagged.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    MagicMock
        The mocked `langfuse_context`.
    """

    langfuse = MagicMock()
    monkeypatch.setattr(f"{SERVICE}.langfuse_context", langfuse)
    return langfuse


class TestUrgencyDetectionEntailment:
    """Tests for the LLM entailment prompt builder and output parser."""

    def test_get_prompt_numbers_rules(self) -> None:
        """The prompt lists every rule, numbered from 1."""

        prompt = UrgencyDetectionEntailment(urgency_rules=RULES).get_prompt()

        assert prompt.startswith("You are a highly sensitive urgency detector.")
        assert "1. has trouble breathing\n2. has a fever" in prompt

    @pytest.mark.parametrize(
        "json_str",
        [
            _llm_json(),
            # Markdown fences are stripped before parsing.
            f"```json\n{_llm_json()}\n```",
            # The LLM sometimes echoes the rule number from the prompt.
            _llm_json(rule="2. has a fever"),
        ],
        ids=["plain", "markdown", "numbered_rule"],
    )
    def test_parse_json_valid(self, json_str: str) -> None:
        """Valid LLM output is parsed into a plain dict.

        Parameters
        ----------
        json_str
            The LLM output.
        """

        parsed = UrgencyDetectionEntailment(urgency_rules=RULES).parse_json(
            json_str=json_str
        )

        assert parsed == {
            "best_matching_rule": "has a fever",
            "probability": 0.8,
            "reason": "r",
        }

    @pytest.mark.parametrize(
        "json_str, error",
        [
            (_llm_json(rule="not a rule"), ValueError),
            (_llm_json(probability=1.5), ValidationError),
            ("not json", ValidationError),
        ],
        ids=["unknown_rule", "probability_out_of_range", "malformed"],
    )
    def test_parse_json_invalid(self, json_str: str, error: type[Exception]) -> None:
        """Invalid LLM output raises.

        Parameters
        ----------
        json_str
            The LLM output.
        error
            The expected exception type.
        """

        with pytest.raises(error):
            UrgencyDetectionEntailment(urgency_rules=RULES).parse_json(
                json_str=json_str
            )


class TestDetectUrgency:
    """Tests for the real `detect_urgency` LLM call wrapper."""

    async def test_returns_parsed_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A valid LLM response is returned as an entailment result.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.
        """

        ask_llm = AsyncMock(return_value=_llm_json())
        monkeypatch.setattr(f"{SERVICE}.ask_llm_async", ask_llm)

        result = await detect_urgency(
            message=QUERY.message_text, metadata={"k": "v"}, urgency_rules=RULES
        )

        assert result == UrgencyDetectionEntailmentResult(
            best_matching_rule="has a fever", probability=0.8, reason="r"
        )
        assert ask_llm.await_args is not None
        kwargs = ask_llm.await_args.kwargs
        assert kwargs["json_"] is True
        assert kwargs["metadata"] == {"k": "v"}
        assert kwargs["user_message"] == QUERY.message_text
        assert "2. has a fever" in kwargs["system_message"]

    @pytest.mark.parametrize(
        "llm_output", [_llm_json(rule="not a rule"), "{broken"], ids=["rule", "json"]
    )
    async def test_falls_back_to_default_on_bad_output(
        self, llm_output: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unparseable LLM output falls back to a zero-probability result.

        Parameters
        ----------
        llm_output
            The LLM output.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        monkeypatch.setattr(
            f"{SERVICE}.ask_llm_async", AsyncMock(return_value=llm_output)
        )

        result: UrgencyDetectionEntailmentResult = await detect_urgency(
            message=QUERY.message_text, metadata=None, urgency_rules=RULES
        )

        assert result.model_dump() == UrgencyDetectionEntailment.default_json


class TestUrgencyClassifiers:
    """Tests for the urgency classifiers."""

    def test_urgency_classifier_registers_function(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The decorator registers a classifier by name and returns it unchanged.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.
        """

        registry: dict[str, Callable] = {}
        monkeypatch.setattr(f"{SERVICE}.ALL_URGENCY_CLASSIFIERS", registry)

        async def my_classifier() -> None:
            """Dummy classifier."""

        assert urgency_classifier(my_classifier) is my_classifier
        assert registry == {"my_classifier": my_classifier}

    @pytest.mark.parametrize("classifier", ALL_URGENCY_CLASSIFIERS.values())
    async def test_classifier(
        self, classifier: Callable, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every registered classifier returns an `UrgencyResponse`.

        Parameters
        ----------
        classifier
            Urgency classifier.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        monkeypatch.setattr(
            f"{SERVICE}.get_cosine_distances_from_rules", AsyncMock(return_value={})
        )
        monkeypatch.setattr(
            f"{SERVICE}.get_urgency_rules_from_db", AsyncMock(return_value=[])
        )

        classifier_response = await classifier(
            asession=AsyncMock(), urgency_query=QUERY, workspace_id=1
        )

        assert isinstance(classifier_response, UrgencyResponse)

    @pytest.mark.parametrize(
        "distances, expected_matches",
        [
            ({}, []),
            ([0.9, 0.7], []),
            ([0.1, 0.7], ["rule 0"]),
            ([0.1, 0.49], ["rule 0", "rule 1"]),
        ],
        ids=["no_rules", "none_close", "one_close", "all_close"],
    )
    async def test_cosine_distance_classifier(
        self,
        distances: list[float],
        expected_matches: list[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Rules closer than the max distance are matched.

        Parameters
        ----------
        distances
            Cosine distances returned by the repository, one per rule.
        expected_matches
            The rules expected to match.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        cosine_distances = {
            i: UrgencyRuleCosineDistance(distance=d, urgency_rule=f"rule {i}")
            for i, d in enumerate(distances)
        }
        get_distances = AsyncMock(return_value=cosine_distances)
        monkeypatch.setattr(f"{SERVICE}.get_cosine_distances_from_rules", get_distances)
        monkeypatch.setattr(f"{SERVICE}.URGENCY_DETECTION_MAX_DISTANCE", 0.5)
        asession = AsyncMock()

        response = await cosine_distance_classifier(
            asession=asession, urgency_query=QUERY, workspace_id=3
        )

        assert response.matched_rules == expected_matches
        assert response.is_urgent is bool(expected_matches)
        assert response.details == cosine_distances
        get_distances.assert_awaited_once_with(
            asession=asession, message_text=QUERY.message_text, workspace_id=3
        )

    async def test_llm_entailment_classifier_no_rules(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no rules in the workspace the LLM is not called.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.
        """

        monkeypatch.setattr(
            f"{SERVICE}.get_urgency_rules_from_db", AsyncMock(return_value=[])
        )
        detect = AsyncMock()
        monkeypatch.setattr(f"{SERVICE}.detect_urgency", detect)

        response = await llm_entailment_classifier(
            asession=AsyncMock(), urgency_query=QUERY, workspace_id=3
        )

        assert response == UrgencyResponse(
            details={}, is_urgent=False, matched_rules=[]
        )
        detect.assert_not_awaited()

    @pytest.mark.parametrize(
        "probability, is_urgent", [(0.9, True), (0.5, False), (0.1, False)]
    )
    async def test_llm_entailment_classifier(
        self, probability: float, is_urgent: bool, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A message is urgent only when the LLM probability exceeds the minimum.

        Parameters
        ----------
        probability
            The probability returned by the LLM.
        is_urgent
            Whether the message is expected to be urgent.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        monkeypatch.setattr(
            f"{SERVICE}.get_urgency_rules_from_db",
            AsyncMock(
                return_value=[UrgencyRuleDB(urgency_rule_text=rule) for rule in RULES]
            ),
        )
        result = UrgencyDetectionEntailmentResult(
            best_matching_rule="has a fever", probability=probability, reason="r"
        )
        detect = AsyncMock(return_value=result)
        monkeypatch.setattr(f"{SERVICE}.detect_urgency", detect)
        monkeypatch.setattr(f"{SERVICE}.URGENCY_DETECTION_MIN_PROBABILITY", 0.5)

        response = await llm_entailment_classifier(
            asession=AsyncMock(), urgency_query=QUERY, workspace_id=3
        )

        assert response.is_urgent is is_urgent
        assert response.matched_rules == (["has a fever"] if is_urgent else [])
        assert response.details == result
        detect.assert_awaited_once_with(
            message=QUERY.message_text,
            metadata={"trace_workspace_id": "workspace_id-3"},
            urgency_rules=RULES,
        )


class TestClassifyUrgency:
    """Tests for `classify_urgency`, which saves, classifies and saves again."""

    @pytest.fixture
    def save_query(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        """Mock saving the query; the returned row has a fixed ID.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.

        Returns
        -------
        AsyncMock
            The mocked `save_urgency_query_to_db`.
        """

        mock = AsyncMock(
            return_value=UrgencyQueryDB(urgency_query_id=11, workspace_id=3)
        )
        monkeypatch.setattr(f"{SERVICE}.save_urgency_query_to_db", mock)
        monkeypatch.setattr(f"{SERVICE}.generate_secret_key", lambda: "secret")
        return mock

    @pytest.fixture
    def save_response(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        """Mock saving the response.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.

        Returns
        -------
        AsyncMock
            The mocked `save_urgency_response_to_db`.
        """

        mock = AsyncMock()
        monkeypatch.setattr(f"{SERVICE}.save_urgency_response_to_db", mock)
        return mock

    async def test_classifies_and_saves(
        self,
        mock_langfuse: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        save_query: AsyncMock,
        save_response: AsyncMock,
    ) -> None:
        """The configured classifier runs and both query and response are saved.

        Parameters
        ----------
        mock_langfuse
            The mocked Langfuse context.
        monkeypatch
            Pytest monkeypatch fixture.
        save_query
            The mocked query save.
        save_response
            The mocked response save.
        """

        expected = UrgencyResponse(details={}, is_urgent=False, matched_rules=[])
        fake_classifier = AsyncMock(return_value=expected)
        # Register a fake classifier and select it via the config value.
        monkeypatch.setitem(ALL_URGENCY_CLASSIFIERS, "fake_classifier", fake_classifier)
        monkeypatch.setattr(f"{SERVICE}.URGENCY_CLASSIFIER", "fake_classifier")
        asession = AsyncMock()

        response = await classify_urgency(
            asession=asession, urgency_query=QUERY, workspace_id=3
        )

        assert response is expected
        save_query.assert_awaited_once_with(
            asession=asession,
            feedback_secret_key="secret",
            urgency_query=QUERY,
            workspace_id=3,
        )
        fake_classifier.assert_awaited_once_with(
            asession=asession, urgency_query=QUERY, workspace_id=3
        )
        save_response.assert_awaited_once_with(
            asession=asession,
            response=expected,
            urgency_query_db=save_query.return_value,
        )
        mock_langfuse.update_current_trace.assert_called_once_with(
            name="urgency_detection",
            metadata={"urgency_query_id": 11, "workspace_id": 3},
        )

    async def test_invalid_classifier_raises_after_saving_query(
        self,
        mock_langfuse: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        save_query: AsyncMock,
        save_response: AsyncMock,
    ) -> None:
        """An unknown classifier raises, but the query is still recorded.

        Parameters
        ----------
        mock_langfuse
            The mocked Langfuse context.
        monkeypatch
            Pytest monkeypatch fixture.
        save_query
            The mocked query save.
        save_response
            The mocked response save.
        """

        monkeypatch.setattr(f"{SERVICE}.URGENCY_CLASSIFIER", "no_such_classifier")

        with pytest.raises(ValueError, match="no_such_classifier"):
            await classify_urgency(
                asession=AsyncMock(), urgency_query=QUERY, workspace_id=3
            )

        save_query.assert_awaited_once()
        save_response.assert_not_awaited()
        mock_langfuse.update_current_trace.assert_not_called()
