"""Unit tests for `app.data_api.service`.

The repository functions are faked (as imported in the service module) and return
plain objects shaped like the ORM records, so no database is needed.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.data_api import service

SVC = "app.data_api.service"
NOW = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)


def fake_repo(monkeypatch: pytest.MonkeyPatch, name: str, rows: list) -> AsyncMock:
    """Replace a repository function imported in the service with an `AsyncMock`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    name
        The repository function's name in `app.data_api.service`.
    rows
        The records the fake returns.

    Returns
    -------
    AsyncMock
        The fake.
    """

    fake = AsyncMock(return_value=rows)
    monkeypatch.setattr(f"{SVC}.{name}", fake)
    return fake


async def test_get_workspace_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contents are converted with their tags flattened to tag names.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    content = SimpleNamespace(
        content_id=1,
        content_metadata={"source": "faq"},
        content_tags=[SimpleNamespace(tag_name="A"), SimpleNamespace(tag_name="B")],
        content_text="Text",
        content_title="Title",
        created_datetime_utc=NOW,
        display_number=3,
        is_archived=False,
        negative_votes=1,
        positive_votes=2,
        updated_datetime_utc=NOW,
        workspace_id=9,
    )
    repo = fake_repo(monkeypatch, "get_contents_with_tags", [content])
    asession = AsyncMock()

    [result] = await service.get_workspace_contents(asession=asession, workspace_id=9)

    repo.assert_awaited_once_with(asession=asession, workspace_id=9)
    assert result.content_tags == ["A", "B"]
    assert (result.content_id, result.display_number, result.workspace_id) == (
        1,
        3,
        9,
    )


async def test_get_workspace_urgency_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Urgency rule records are validated into `UrgencyRuleRetrieve`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    rule = SimpleNamespace(
        created_datetime_utc=NOW,
        updated_datetime_utc=NOW,
        urgency_rule_id=4,
        urgency_rule_metadata={},
        urgency_rule_text="Bleeding",
        workspace_id=9,
    )
    fake_repo(monkeypatch, "get_urgency_rules_for_workspace", [rule])

    [result] = await service.get_workspace_urgency_rules(
        asession=AsyncMock(), workspace_id=9
    )

    assert (result.urgency_rule_id, result.urgency_rule_text) == (4, "Bleeding")


# A naive datetime and one with a non-UTC offset: both keep their wall-clock time
# and are relabelled as UTC (the API documents its datetimes as UTC).
DATE_INPUTS = pytest.mark.parametrize(
    "tzinfo", [None, timezone(timedelta(hours=3))], ids=["naive", "utc+3"]
)


@DATE_INPUTS
async def test_get_workspace_queries(
    monkeypatch: pytest.MonkeyPatch, tzinfo: timezone | None
) -> None:
    """Dates are pinned to UTC and queries converted with their child records.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    tzinfo
        The timezone of the input dates.
    """

    query = SimpleNamespace(
        content_feedback=[
            SimpleNamespace(
                content_id=1,
                feedback_datetime_utc=NOW,
                feedback_id=5,
                feedback_sentiment="positive",
                feedback_text=None,
            )
        ],
        query_datetime_utc=NOW,
        query_id=2,
        query_metadata={},
        query_text="Hello?",
        response=[
            SimpleNamespace(
                llm_response="Hi",
                response_datetime_utc=NOW,
                response_id=6,
                search_results={},
            )
        ],
        response_feedback=[],
        workspace_id=9,
    )
    repo = fake_repo(monkeypatch, "get_queries_with_children", [query])
    start = datetime(2025, 1, 1, 8, 0, tzinfo=tzinfo)
    end = datetime(2025, 1, 31, 8, 0, tzinfo=tzinfo)

    [result] = await service.get_workspace_queries(
        asession=AsyncMock(), end_date=end, start_date=start, workspace_id=9
    )

    assert repo.await_args is not None
    kwargs = repo.await_args.kwargs
    assert kwargs["start_date"] == datetime(2025, 1, 1, 8, 0, tzinfo=timezone.utc)
    assert kwargs["end_date"] == datetime(2025, 1, 31, 8, 0, tzinfo=timezone.utc)
    assert result.content_feedback[0].feedback_id == 5
    assert result.response[0].llm_response == "Hi"
    assert result.response_feedback == []


@DATE_INPUTS
async def test_get_workspace_urgency_queries(
    monkeypatch: pytest.MonkeyPatch, tzinfo: timezone | None
) -> None:
    """Dates are pinned to UTC; queries with and without a response are converted.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    tzinfo
        The timezone of the input dates.
    """

    response = SimpleNamespace(
        details={},
        is_urgent=True,
        matched_rules=["Bleeding"],
        response_datetime_utc=NOW,
        urgency_response_id=8,
    )
    queries = [
        SimpleNamespace(
            message_datetime_utc=NOW,
            message_text=text,
            response=resp,
            urgency_query_id=i,
            workspace_id=9,
        )
        for i, (text, resp) in enumerate([("urgent", response), ("pending", None)])
    ]
    repo = fake_repo(monkeypatch, "get_urgency_queries_with_response", queries)
    start = datetime(2025, 1, 1, tzinfo=tzinfo)

    results = await service.get_workspace_urgency_queries(
        asession=AsyncMock(), end_date=start, start_date=start, workspace_id=9
    )

    assert repo.await_args is not None
    assert repo.await_args.kwargs["start_date"].tzinfo is timezone.utc
    assert results[0].response is not None
    assert results[0].response.matched_rules == ["Bleeding"]
    assert results[1].response is None
