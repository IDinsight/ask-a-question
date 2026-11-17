"""Unit tests for `app.dashboard.service`.

No database, Redis, LLM or real topic model is touched: every repository function,
external client and heavy library is replaced, as imported in the service module,
with a fake.
"""

import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest
from bokeh.palettes import Turbo256
from dateutil.relativedelta import relativedelta

from app.core.config import (
    LITELLM_MODEL_DASHBOARD_SUMMARY,
    LITELLM_MODEL_TOPIC_MODEL,
    MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY,
    MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT,
    TOPIC_MODELING_CONTEXT,
)
from app.core.exceptions import BadRequestError, InternalServerError, NotFoundError
from app.dashboard import service
from app.dashboard.schemas import (
    AIFeedbackSummary,
    BokehContentItem,
    DashboardOverview,
    DashboardPerformance,
    TimeFrequency,
    TopicsData,
    UserQuery,
)

SVC = "app.dashboard.service"
WORKSPACE = SimpleNamespace(workspace_id=7, workspace_name="ws_dashboard")
START = datetime(2025, 1, 1, tzinfo=timezone.utc)
END = datetime(2025, 1, 31, tzinfo=timezone.utc)


@pytest.fixture
def workspace_lookup(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Fake the workspace lookup every endpoint-orchestration function starts with.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    AsyncMock
        The fake, returning `WORKSPACE`.
    """

    lookup = AsyncMock(return_value=WORKSPACE)
    monkeypatch.setattr(f"{SVC}.get_workspace_by_workspace_name", lookup)
    return lookup


@pytest.fixture
def llm(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Fake `ask_llm_async` and force the dashboard LLM on.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    AsyncMock
        The fake LLM call.
    """

    fake = AsyncMock(return_value="llm output")
    monkeypatch.setattr(f"{SVC}.ask_llm_async", fake)
    monkeypatch.setattr(f"{SVC}.DISABLE_DASHBOARD_LLM", False)
    return fake


def make_queries(n: int) -> list[UserQuery]:
    """Build `n` user queries.

    Parameters
    ----------
    n
        Number of queries.

    Returns
    -------
    list[UserQuery]
        The queries.
    """

    return [
        UserQuery(query_datetime_utc=START, query_id=i, query_text=f"query {i}")
        for i in range(n)
    ]


def make_contents(n: int) -> list[BokehContentItem]:
    """Build `n` content items.

    Parameters
    ----------
    n
        Number of contents.

    Returns
    -------
    list[BokehContentItem]
        The content items.
    """

    return [
        BokehContentItem(
            content_id=i, content_text=f"content {i}", content_title=f"title {i}"
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
class TestPrompts:
    """Tests for the prompt builders."""

    def test_topic_labelling_prompt_contains_context(self) -> None:
        """The labelling prompt embeds the context and the JSON response spec."""

        prompt = service.TopicModelLabelling(context="malaria").get_prompt()

        assert "specific to malaria" in prompt
        assert prompt.endswith("}")
        assert "topic_title: str" in prompt

    @pytest.mark.parametrize(
        "json_str",
        [
            '{"topic_title": "T", "topic_summary": "S"}',
            '```json\n{"topic_title": "T", "topic_summary": "S"}\n```',
        ],
        ids=["plain", "markdown-fenced"],
    )
    def test_parse_json_valid(self, json_str: str) -> None:
        """Valid output is parsed, with or without a markdown fence.

        Parameters
        ----------
        json_str
            The LLM output to parse.
        """

        assert service.TopicModelLabelling.parse_json(json_str=json_str) == {
            "topic_summary": "S",
            "topic_title": "T",
        }

    @pytest.mark.parametrize("json_str", ["not json", '{"topic_title": "T"}'])
    def test_parse_json_invalid(self, json_str: str) -> None:
        """Malformed or incomplete output raises `ValueError`.

        Parameters
        ----------
        json_str
            The LLM output to parse.
        """

        with pytest.raises(ValueError, match="Error validating the output"):
            service.TopicModelLabelling.parse_json(json_str=json_str)

    def test_feedback_summary_prompt(self) -> None:
        """The feedback prompt wraps the content title and text in tags."""

        prompt = service.get_feedback_summary_prompt(
            content="Drink water.", content_title="Hydration"
        )

        assert "<CONTENT_TITLE>\nHydration\n</CONTENT_TITLE>" in prompt
        assert "<CONTENT>\nDrink water.\n</CONTENT>" in prompt


# ---------------------------------------------------------------------------
# Time-window helpers
# ---------------------------------------------------------------------------
class TestGetFreqStartEndDate:
    """Tests for `get_freq_start_end_date`."""

    @pytest.mark.parametrize(
        "timeframe, expected_freq, span",
        [
            ("day", TimeFrequency.Hour, relativedelta(days=1)),
            ("week", TimeFrequency.Day, relativedelta(weeks=1)),
            ("month", TimeFrequency.Day, relativedelta(months=1)),
            ("year", TimeFrequency.Month, relativedelta(years=1)),
        ],
    )
    def test_predefined_timeframes(
        self, timeframe: Any, expected_freq: TimeFrequency, span: relativedelta
    ) -> None:
        """Predefined timeframes end now and ignore any frequency passed in.

        Parameters
        ----------
        timeframe
            The dashboard timeframe.
        expected_freq
            The default frequency for that timeframe.
        span
            The expected window length.
        """

        before = datetime.now(timezone.utc)
        freq, start_dt, end_dt = service.get_freq_start_end_date(
            frequency=TimeFrequency.Week, timeframe=timeframe
        )

        assert freq == expected_freq
        assert before <= end_dt <= datetime.now(timezone.utc)
        assert end_dt - span == start_dt

    def test_custom_timeframe(self) -> None:
        """A custom timeframe returns the given frequency and UTC-midnight dates."""

        freq, start_dt, end_dt = service.get_freq_start_end_date(
            end_date_str="2025-01-31",
            frequency=TimeFrequency.Week,
            start_date_str="2025-01-01",
            timeframe="custom",
        )

        assert (freq, start_dt, end_dt) == (TimeFrequency.Week, START, END)

    @pytest.mark.parametrize(
        "start, end, frequency, message",
        [
            (None, "2025-01-31", TimeFrequency.Day, "are required"),
            ("2025-01-01", None, TimeFrequency.Day, "are required"),
            ("2025-01-01", "2025-01-31", None, "`frequency` is required"),
            ("01/01/2025", "2025-01-31", TimeFrequency.Day, "Invalid date format"),
            ("2025-01-31", "2025-01-01", TimeFrequency.Day, "must be >="),
        ],
        ids=["no-start", "no-end", "no-frequency", "bad-format", "end-before-start"],
    )
    def test_custom_timeframe_errors(
        self,
        start: str | None,
        end: str | None,
        frequency: TimeFrequency | None,
        message: str,
    ) -> None:
        """Invalid custom windows raise `BadRequestError` with a helpful message.

        Parameters
        ----------
        start
            The start date string.
        end
            The end date string.
        frequency
            The frequency.
        message
            A fragment of the expected error detail.
        """

        with pytest.raises(BadRequestError) as exc_info:
            service.get_freq_start_end_date(
                end_date_str=end,
                frequency=frequency,
                start_date_str=start,
                timeframe="custom",
            )
        assert message in exc_info.value.detail

    def test_unknown_timeframe(self) -> None:
        """A timeframe outside `DashboardTimeFilter` raises `ValueError`."""

        with pytest.raises(ValueError, match="Invalid time frequency"):
            service.get_freq_start_end_date(timeframe="decade")  # type: ignore[arg-type]


def test_create_session_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """The session ID is `<prefix>-<start>-<end>-<zero-padded random suffix>`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    monkeypatch.setattr(f"{SVC}.random.randint", lambda a, b: 7)

    assert (
        service.create_session_id("topics", START, END)
        == "topics-20250101_000000-20250131_000000-0007"
    )


# ---------------------------------------------------------------------------
# Endpoint orchestration
# ---------------------------------------------------------------------------
async def test_get_content_details_for_timeframe(
    monkeypatch: pytest.MonkeyPatch, workspace_lookup: AsyncMock
) -> None:
    """The workspace and window are resolved, then the repository is queried.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    workspace_lookup
        The faked workspace lookup.
    """

    details = object()
    repo = AsyncMock(return_value=details)
    monkeypatch.setattr(f"{SVC}.get_content_details", repo)
    asession = AsyncMock()

    result = await service.get_content_details_for_timeframe(
        asession=asession,
        content_id=3,
        end_date=None,
        start_date=None,
        timeframe="week",
        workspace_name="ws_dashboard",
    )

    assert result is details
    workspace_lookup.assert_awaited_once_with(
        asession=asession, workspace_name="ws_dashboard"
    )
    assert repo.await_args is not None
    kwargs = repo.await_args.kwargs
    assert kwargs["end_date"] - kwargs["start_date"] == timedelta(weeks=1)
    assert kwargs["frequency"] == TimeFrequency.Day
    assert kwargs["max_feedback_records"] == int(MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT)
    assert (kwargs["content_id"], kwargs["workspace_id"]) == (3, 7)


@pytest.mark.xfail(
    raises=BadRequestError,
    strict=True,
    reason=(
        "App bug: get_content_details_for_timeframe does not pass a frequency to "
        "get_freq_start_end_date, so every custom timeframe is rejected."
    ),
)
async def test_get_content_details_for_custom_timeframe(
    monkeypatch: pytest.MonkeyPatch, workspace_lookup: AsyncMock
) -> None:
    """A custom window should be accepted for the content details drawer.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    workspace_lookup
        The faked workspace lookup.
    """

    monkeypatch.setattr(f"{SVC}.get_content_details", AsyncMock())

    await service.get_content_details_for_timeframe(
        asession=AsyncMock(),
        content_id=3,
        end_date="2025-01-31",
        start_date="2025-01-01",
        timeframe="custom",
        workspace_name="ws_dashboard",
    )


class TestGetAIAnswerSummary:
    """Tests for `get_ai_answer_summary`."""

    @pytest.fixture
    def repo(self, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
        """Fake the two repository reads and the summary generator.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.

        Returns
        -------
        SimpleNamespace
            The fakes, as `feedback`, `content` and `summarize`.
        """

        fakes = SimpleNamespace(
            feedback=AsyncMock(return_value=["too long", "unclear"]),
            content=AsyncMock(
                return_value=SimpleNamespace(content_text="Text", content_title="T")
            ),
            summarize=AsyncMock(return_value="People found it unclear."),
        )
        monkeypatch.setattr(f"{SVC}.DISABLE_DASHBOARD_LLM", False)
        monkeypatch.setattr(f"{SVC}.get_content_feedback_texts", fakes.feedback)
        monkeypatch.setattr(f"{SVC}.get_content_title_and_text", fakes.content)
        monkeypatch.setattr(f"{SVC}.generate_ai_summary", fakes.summarize)
        return fakes

    async def call(self) -> str | None:
        """Call `get_ai_answer_summary` with fixed arguments.

        Returns
        -------
        str | None
            The summary.
        """

        return await service.get_ai_answer_summary(
            asession=AsyncMock(),
            content_id=3,
            end_date=END,
            max_feedback_records=10,
            start_date=START,
            workspace_id=WORKSPACE.workspace_id,
        )

    async def test_summarizes_feedback(self, repo: SimpleNamespace) -> None:
        """Feedback is passed to the LLM summary along with the content.

        Parameters
        ----------
        repo
            The faked dependencies.
        """

        assert await self.call() == "People found it unclear."
        repo.summarize.assert_awaited_once_with(
            content_text="Text",
            content_title="T",
            feedback=["too long", "unclear"],
            workspace_id=WORKSPACE.workspace_id,
        )

    async def test_no_feedback(self, repo: SimpleNamespace) -> None:
        """Without feedback the LLM is skipped.

        Parameters
        ----------
        repo
            The faked dependencies.
        """

        repo.feedback.return_value = []

        assert await self.call() == "No feedback to summarize."
        repo.summarize.assert_not_awaited()

    async def test_missing_content(self, repo: SimpleNamespace) -> None:
        """A content outside the workspace raises `ValueError`.

        Parameters
        ----------
        repo
            The faked dependencies.
        """

        repo.content.return_value = None

        with pytest.raises(ValueError, match="Content with ID '3'"):
            await self.call()

    async def test_llm_disabled(
        self, repo: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With the dashboard LLM disabled nothing is read and `None` is returned.

        Parameters
        ----------
        repo
            The faked dependencies.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        monkeypatch.setattr(f"{SVC}.DISABLE_DASHBOARD_LLM", True)

        assert await self.call() is None
        repo.feedback.assert_not_awaited()


async def test_get_content_ai_summary_for_timeframe(
    monkeypatch: pytest.MonkeyPatch, workspace_lookup: AsyncMock
) -> None:
    """The summary is wrapped in `AIFeedbackSummary` and the Langfuse trace tagged.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    workspace_lookup
        The faked workspace lookup.
    """

    summarize = AsyncMock(return_value="summary")
    langfuse = MagicMock()
    monkeypatch.setattr(f"{SVC}.get_ai_answer_summary", summarize)
    monkeypatch.setattr(f"{SVC}.langfuse_context", langfuse)

    result = await service.get_content_ai_summary_for_timeframe(
        asession=AsyncMock(),
        content_id=3,
        end_date="2025-01-31",
        start_date="2025-01-01",
        timeframe="custom",
        workspace_name="ws_dashboard",
    )

    assert result == AIFeedbackSummary(ai_summary="summary")
    assert summarize.await_args is not None
    kwargs = summarize.await_args.kwargs
    assert kwargs["max_feedback_records"] == int(MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY)
    assert (kwargs["start_date"], kwargs["end_date"]) == (START, END)
    trace = langfuse.update_current_trace.call_args.kwargs
    assert trace["name"] == "content_feedback_summary"
    assert trace["session_id"].startswith("content_3_feedback-20250101_000000-")
    assert trace["metadata"] == {"content_id": 3, "workspace_id": 7}


async def test_retrieve_performance(monkeypatch: pytest.MonkeyPatch) -> None:
    """The repository timeseries is wrapped in `DashboardPerformance`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    repo = AsyncMock(return_value=[])
    monkeypatch.setattr(f"{SVC}.get_timeseries_top_content", repo)
    asession = AsyncMock()

    result = await service.retrieve_performance(
        asession=asession,
        end_date=END,
        frequency=TimeFrequency.Week,
        start_date=START,
        top_n=5,
        workspace_id=7,
    )

    assert result == DashboardPerformance(content_time_series=[])
    repo.assert_awaited_once_with(
        asession=asession,
        end_date=END,
        frequency=TimeFrequency.Week,
        start_date=START,
        top_n=5,
        workspace_id=7,
    )


async def test_get_performance_for_timeframe(
    monkeypatch: pytest.MonkeyPatch, workspace_lookup: AsyncMock
) -> None:
    """A predefined timeframe uses its default frequency (`day` -> hourly).

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    workspace_lookup
        The faked workspace lookup.
    """

    retrieve = AsyncMock(return_value=DashboardPerformance(content_time_series=[]))
    monkeypatch.setattr(f"{SVC}.retrieve_performance", retrieve)

    await service.get_performance_for_timeframe(
        asession=AsyncMock(),
        end_date=None,
        start_date=None,
        timeframe="day",
        top_n=2,
        workspace_name="ws_dashboard",
    )

    assert retrieve.await_args is not None
    kwargs = retrieve.await_args.kwargs
    assert kwargs["frequency"] == TimeFrequency.Hour
    assert (kwargs["top_n"], kwargs["workspace_id"]) == (2, 7)


async def test_retrieve_overview(
    monkeypatch: pytest.MonkeyPatch, empty_overview: DashboardOverview
) -> None:
    """The four overview repository reads are combined into `DashboardOverview`.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    empty_overview
        A valid overview whose parts the fakes return.
    """

    fakes = {
        "get_stats_cards": AsyncMock(return_value=empty_overview.stats_cards),
        "get_heatmap": AsyncMock(return_value=empty_overview.heatmap),
        "get_overview_timeseries": AsyncMock(return_value=empty_overview.time_series),
        "get_top_content": AsyncMock(return_value=[]),
    }
    for name, fake in fakes.items():
        monkeypatch.setattr(f"{SVC}.{name}", fake)

    result = await service.retrieve_overview(
        asession=AsyncMock(),
        end_date=END,
        frequency=TimeFrequency.Day,
        start_date=START,
        workspace_id=7,
    )

    assert result == empty_overview
    assert fakes["get_overview_timeseries"].await_args is not None
    assert fakes["get_overview_timeseries"].await_args.kwargs["frequency"] == (
        TimeFrequency.Day
    )
    # Default `top_n` for the overview cards.
    assert fakes["get_top_content"].await_args is not None
    assert fakes["get_top_content"].await_args.kwargs["top_n"] == 4


async def test_get_overview_for_timeframe(
    monkeypatch: pytest.MonkeyPatch,
    workspace_lookup: AsyncMock,
    empty_overview: DashboardOverview,
) -> None:
    """A custom timeframe forwards the caller's frequency and dates.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    workspace_lookup
        The faked workspace lookup.
    empty_overview
        The overview the fake returns.
    """

    retrieve = AsyncMock(return_value=empty_overview)
    monkeypatch.setattr(f"{SVC}.retrieve_overview", retrieve)

    result = await service.get_overview_for_timeframe(
        asession=AsyncMock(),
        end_date="2025-01-31",
        frequency=TimeFrequency.Week,
        start_date="2025-01-01",
        timeframe="custom",
        workspace_name="ws_dashboard",
    )

    assert result is empty_overview
    assert retrieve.await_args is not None
    kwargs = retrieve.await_args.kwargs
    assert (kwargs["frequency"], kwargs["start_date"], kwargs["end_date"]) == (
        TimeFrequency.Week,
        START,
        END,
    )


async def test_get_insights_refresh_window(workspace_lookup: AsyncMock) -> None:
    """The refresh window resolves to the workspace plus the custom dates.

    Parameters
    ----------
    workspace_lookup
        The faked workspace lookup.
    """

    assert await service.get_insights_refresh_window(
        asession=AsyncMock(),
        end_date="2025-01-31",
        start_date="2025-01-01",
        timeframe="custom",
        workspace_name="ws_dashboard",
    ) == (WORKSPACE, START, END)


class TestRefreshInsights:
    """Tests for the `refresh_insights` background task."""

    RESULTS_KEY = "ws_dashboard_insights_week_results"

    @pytest.fixture
    def pipeline(self, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
        """Fake the session, the repository reads and the topic model.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.

        Returns
        -------
        SimpleNamespace
            The fakes, as `queries`, `contents`, `model` and `topics`.
        """

        topics = TopicsData(data=[], refreshTimeStamp="now", status="completed")
        fakes = SimpleNamespace(
            queries=AsyncMock(return_value=make_queries(1)),
            contents=AsyncMock(return_value=make_contents(1)),
            model=AsyncMock(return_value=(topics, pd.DataFrame({"x": [1.0]}))),
            topics=topics,
        )
        # MagicMock supports `async with`, standing in for the task's own session.
        monkeypatch.setattr(f"{SVC}.AsyncSession", MagicMock())
        monkeypatch.setattr(f"{SVC}.get_sqlalchemy_async_engine", MagicMock())
        monkeypatch.setattr(f"{SVC}.langfuse_context", MagicMock())
        monkeypatch.setattr(f"{SVC}.get_raw_queries", fakes.queries)
        monkeypatch.setattr(f"{SVC}.get_raw_contents", fakes.contents)
        monkeypatch.setattr(f"{SVC}.topic_model_queries", fakes.model)
        return fakes

    async def run(self, redis: AsyncMock) -> None:
        """Run `refresh_insights` for the week timeframe.

        Parameters
        ----------
        redis
            The fake Redis client.
        """

        await service.refresh_insights(
            end_date=END,
            redis=redis,
            start_date=START,
            timeframe="week",
            workspace_db=WORKSPACE,  # type: ignore[arg-type]
        )

    async def test_success(self, pipeline: SimpleNamespace) -> None:
        """Progress, embeddings and final topics are written to Redis in order.

        Parameters
        ----------
        pipeline
            The faked dependencies.
        """

        redis = AsyncMock()

        await self.run(redis)

        keys = [c.args[0] for c in redis.set.await_args_list]
        assert keys == [
            self.RESULTS_KEY,
            "ws_dashboard_embeddings_week",
            self.RESULTS_KEY,
        ]
        first = TopicsData.model_validate_json(redis.set.await_args_list[0].args[1])
        assert first.status == "in_progress"
        assert redis.set.await_args_list[-1].args[1] == (
            pipeline.topics.model_dump_json()
        )
        pipeline.model.assert_awaited_once_with(
            content_data=pipeline.contents.return_value,
            query_data=pipeline.queries.return_value,
            workspace_id=WORKSPACE.workspace_id,
        )

    @pytest.mark.parametrize(
        "failing, step",
        [
            ("queries", "Retrieve queries"),
            ("contents", "Retrieve contents"),
            # `step` is not advanced before topic modelling, so its failures are
            # still reported against the contents step.
            ("model", "Retrieve contents"),
        ],
    )
    async def test_failure_is_reported(
        self, pipeline: SimpleNamespace, failing: str, step: str
    ) -> None:
        """A failure is caught and written to Redis with the step that failed.

        Parameters
        ----------
        pipeline
            The faked dependencies.
        failing
            Which fake raises.
        step
            The expected `failure_step`.
        """

        getattr(pipeline, failing).side_effect = RuntimeError("boom")
        redis = AsyncMock()

        await self.run(redis)

        result = TopicsData.model_validate_json(redis.set.await_args_list[-1].args[1])
        assert (result.status, result.failure_step, result.error_message) == (
            "error",
            step,
            "boom",
        )

    async def test_redis_write_failure(self, pipeline: SimpleNamespace) -> None:
        """A failed Redis write is reported as the `Write to Redis` step.

        Parameters
        ----------
        pipeline
            The faked dependencies.
        """

        # Progress write succeeds, embeddings write fails, error write succeeds.
        redis = AsyncMock()
        redis.set.side_effect = [None, ConnectionError("redis down"), None]

        await self.run(redis)

        result = TopicsData.model_validate_json(redis.set.await_args_list[-1].args[1])
        assert result.failure_step == "Write to Redis"


class TestGetInsights:
    """Tests for `get_insights`."""

    async def test_cached(self, workspace_lookup: AsyncMock) -> None:
        """Cached insights are parsed from Redis.

        Parameters
        ----------
        workspace_lookup
            The faked workspace lookup.
        """

        cached = TopicsData(data=[], refreshTimeStamp="t", status="completed")
        redis = AsyncMock()
        redis.exists.return_value = 1
        redis.get.return_value = cached.model_dump_json()

        result = await service.get_insights(
            asession=AsyncMock(), redis=redis, timeframe="week", workspace_name="ws"
        )

        assert result == cached
        redis.get.assert_awaited_once_with("ws_dashboard_insights_week_results")

    async def test_not_started(self, workspace_lookup: AsyncMock) -> None:
        """Without a cached result an empty `not_started` payload is returned.

        Parameters
        ----------
        workspace_lookup
            The faked workspace lookup.
        """

        redis = AsyncMock()
        redis.exists.return_value = 0

        result = await service.get_insights(
            asession=AsyncMock(), redis=redis, timeframe="week", workspace_name="ws"
        )

        assert result.status == "not_started"
        redis.get.assert_not_awaited()


class TestCreateTopicPlot:
    """Tests for `create_topic_plot`."""

    async def test_missing_embeddings(self, workspace_lookup: AsyncMock) -> None:
        """No cached embeddings raises `NotFoundError`.

        Parameters
        ----------
        workspace_lookup
            The faked workspace lookup.
        """

        redis = AsyncMock()
        redis.get.return_value = None

        with pytest.raises(NotFoundError):
            await service.create_topic_plot(
                asession=AsyncMock(), redis=redis, timeframe="week", workspace_name="ws"
            )

    async def test_plots_cached_embeddings(
        self, workspace_lookup: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cached embeddings are decoded into a DataFrame and plotted.

        Parameters
        ----------
        workspace_lookup
            The faked workspace lookup.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        df = pd.DataFrame({"x": [0.5], "text": ["hi"]})
        redis = AsyncMock()
        redis.get.return_value = df.to_json(orient="split").encode("utf-8")
        plot = MagicMock(return_value={"target_id": "myplot"})
        monkeypatch.setattr(f"{SVC}.produce_bokeh_plot", plot)

        result = await service.create_topic_plot(
            asession=AsyncMock(), redis=redis, timeframe="week", workspace_name="ws"
        )

        assert result == {"target_id": "myplot"}
        redis.get.assert_awaited_once_with("ws_dashboard_embeddings_week")
        pd.testing.assert_frame_equal(plot.call_args.kwargs["embeddings_df"], df)


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------
async def test_generate_ai_summary(llm: AsyncMock) -> None:
    """Feedback is sent as newline-separated user message to the summary model.

    Parameters
    ----------
    llm
        The faked LLM call.
    """

    result = await service.generate_ai_summary(
        content_text="Text", content_title="T", feedback=["a", "b"], workspace_id=7
    )

    assert result == "llm output"
    assert llm.await_args is not None
    kwargs = llm.await_args.kwargs
    assert kwargs["litellm_model"] == LITELLM_MODEL_DASHBOARD_SUMMARY
    assert kwargs["user_message"] == "a\nb"
    assert "<CONTENT_TITLE>\nT\n" in kwargs["system_message"]


class TestGenerateTopicLabel:
    """Tests for `generate_topic_label`."""

    async def label(self, topic_id: int = 1, topic_model: Any = None) -> dict:
        """Call `generate_topic_label` with fixed sample texts.

        Parameters
        ----------
        topic_id
            The topic ID.
        topic_model
            The (fake) topic model.

        Returns
        -------
        dict
            The topic label.
        """

        return await service.generate_topic_label(
            context="health",
            sample_texts=["q1", "q2"],
            topic_id=topic_id,
            topic_model=topic_model,
            workspace_id=7,
        )

    async def test_noise_topic(self, llm: AsyncMock) -> None:
        """Topic -1 is always `Unclassified` and never sent to the LLM.

        Parameters
        ----------
        llm
            The faked LLM call.
        """

        assert (await self.label(topic_id=-1))["topic_title"] == "Unclassified"
        llm.assert_not_awaited()

    async def test_llm_label(self, llm: AsyncMock) -> None:
        """The LLM is asked for JSON with numbered sample texts.

        Parameters
        ----------
        llm
            The faked LLM call.
        """

        llm.return_value = '{"topic_title": "Fever", "topic_summary": "About fever"}'

        assert await self.label() == {
            "topic_summary": "About fever",
            "topic_title": "Fever",
        }
        assert llm.await_args is not None
        kwargs = llm.await_args.kwargs
        assert kwargs["json_"] is True
        assert kwargs["litellm_model"] == LITELLM_MODEL_TOPIC_MODEL
        assert kwargs["user_message"] == "1. q1\n2. q2"

    async def test_llm_invalid_json(self, llm: AsyncMock) -> None:
        """Unparseable LLM output falls back to `Unknown`.

        Parameters
        ----------
        llm
            The faked LLM call.
        """

        llm.return_value = "not json"

        assert (await self.label())["topic_title"] == "Unknown"

    @pytest.mark.parametrize(
        "topic_info, title",
        [
            ([("fever", 0.5), ("cough", 0.4), ("rash", 0.3), ("pain", 0.2)], None),
            (False, "Unknown"),
        ],
        ids=["keywords", "no-topic-info"],
    )
    async def test_llm_disabled_uses_keywords(
        self,
        llm: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
        topic_info: Any,
        title: str | None,
    ) -> None:
        """With the LLM disabled the label is built from the topic's keywords.

        Parameters
        ----------
        llm
            The faked LLM call.
        monkeypatch
            Pytest monkeypatch fixture.
        topic_info
            What `BERTopic.get_topic` returns.
        title
            The expected title, or `None` for the keyword-based title.
        """

        monkeypatch.setattr(f"{SVC}.DISABLE_DASHBOARD_LLM", True)
        topic_model = MagicMock()
        topic_model.get_topic.return_value = topic_info

        label = await self.label(topic_id=4, topic_model=topic_model)

        llm.assert_not_awaited()
        topic_model.get_topic.assert_called_once_with(4)
        if title is None:
            assert label["topic_title"] == "fever, cough, rash"
            assert label["topic_summary"].startswith("fever cough rash pain")
        else:
            assert label["topic_title"] == title


# ---------------------------------------------------------------------------
# Topic modelling
# ---------------------------------------------------------------------------
def test_add_reduced_embeddings() -> None:
    """The 2D UMAP embedding becomes the `x`/`y` columns."""

    df = pd.DataFrame({"text": ["a", "b"]})
    topic_model = SimpleNamespace(
        umap_model=SimpleNamespace(embedding_=np.array([[1.0, 2.0], [3.0, 4.0]]))
    )

    service.add_reduced_embeddings(results_df=df, topic_model=topic_model)  # type: ignore[arg-type]

    assert df["x"].tolist() == [1.0, 3.0]
    assert df["y"].tolist() == [2.0, 4.0]


def test_fit_topic_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """BERTopic is built from the UMAP and HDBSCAN models and fitted.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    fakes = {name: MagicMock() for name in ("UMAP", "HDBSCAN", "BERTopic")}
    # The service imports these lazily, so fake the modules themselves. This also
    # avoids importing the real (slow) libraries.
    for module, name in (
        ("umap", "UMAP"),
        ("hdbscan", "HDBSCAN"),
        ("bertopic", "BERTopic"),
    ):
        monkeypatch.setitem(sys.modules, module, SimpleNamespace(**{name: fakes[name]}))
    embeddings = np.zeros((2, 3))

    model = service.fit_topic_model(embeddings=embeddings, texts=["a", "b"])

    assert model is fakes["BERTopic"].return_value
    kwargs = fakes["BERTopic"].call_args.kwargs
    assert kwargs["umap_model"] is fakes["UMAP"].return_value
    assert kwargs["hdbscan_model"] is fakes["HDBSCAN"].return_value
    model.fit.assert_called_once_with(["a", "b"], embeddings)


def test_generate_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Texts are encoded with the MiniLM sentence transformer.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    transformer = MagicMock()
    transformer.return_value.encode.return_value = np.ones((2, 3))
    # Lazily imported by the service: fake the module instead of loading torch.
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=transformer),
    )

    result = service.generate_embeddings(texts=["a", "b"])

    assert result.shape == (2, 3)
    transformer.assert_called_once_with("all-MiniLM-L6-v2")
    assert transformer.return_value.encode.call_args.args[0] == ["a", "b"]


class TestGenerateTopicLabelsAsync:
    """Tests for `generate_topic_labels_async`."""

    @pytest.fixture
    def label(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        """Fake `generate_topic_label`, titling each topic `T<id>`.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.

        Returns
        -------
        AsyncMock
            The fake.
        """

        fake = AsyncMock(
            side_effect=lambda **kw: {
                "topic_summary": "",
                "topic_title": f"T{kw['topic_id']}",
            }
        )
        monkeypatch.setattr(f"{SVC}.generate_topic_label", fake)
        return fake

    async def test_labels_each_topic(self, label: AsyncMock) -> None:
        """Every non-noise topic is labelled from at most 5 of its queries.

        Parameters
        ----------
        label
            The faked label generator.
        """

        # String topic IDs check the cast to int; topic 0 has 6 queries + 1 content.
        df = pd.DataFrame(
            {
                "text": [f"q{i}" for i in range(6)] + ["c0", "q6", "noise"],
                "topic_id": ["0"] * 7 + ["1", "-1"],
                "type": ["query"] * 6 + ["content", "query", "query"],
            }
        )

        labels = await service.generate_topic_labels_async(
            results_df=df, topic_model=MagicMock(), workspace_id=7
        )

        assert labels == {
            0: {"topic_summary": "", "topic_title": "T0"},
            1: {"topic_summary": "", "topic_title": "T1"},
        }
        first_call = label.await_args_list[0].kwargs
        assert first_call["sample_texts"] == ["q0", "q1", "q2", "q3", "q4"]
        assert first_call["context"] == TOPIC_MODELING_CONTEXT

    async def test_only_noise(self, label: AsyncMock) -> None:
        """A DataFrame with only noise produces no labels.

        Parameters
        ----------
        label
            The faked label generator.
        """

        df = pd.DataFrame({"text": ["x"], "topic_id": [-1], "type": ["query"]})

        assert (
            await service.generate_topic_labels_async(
                results_df=df, topic_model=MagicMock(), workspace_id=7
            )
            == {}
        )
        label.assert_not_awaited()


@pytest.mark.parametrize(
    "topic_id, row_type, expected",
    [
        (-1, "query", "Unclassified"),
        (0, "content", "Content"),
        (0, "query", "Fever"),
        (9, "query", "Unknown Topic"),
    ],
)
def test_get_topic_title(topic_id: int, row_type: str, expected: str) -> None:
    """Rows are titled by noise, content or their topic's label.

    Parameters
    ----------
    topic_id
        The row's topic.
    row_type
        `query` or `content`.
    expected
        The expected title.
    """

    row = pd.Series({"topic_id": topic_id, "type": row_type})
    labels = {0: {"topic_title": "Fever", "topic_summary": ""}}

    assert service.get_topic_title(row=row, topic_labels=labels) == expected


def test_prepare_dataframes() -> None:
    """Queries come first, then contents, with blank datetimes for contents."""

    df = service.prepare_dataframes(
        content_data=make_contents(1), query_data=make_queries(2)
    )

    assert df["text"].tolist() == ["query 0", "query 1", "content 0"]
    assert df["type"].tolist() == ["query", "query", "content"]
    assert df["datetime"].tolist() == [str(START), str(START), ""]


def test_prepare_topics_data() -> None:
    """Topics are sorted by query count, capped at 20 samples, noise dropped."""

    n_big = 25
    df = pd.DataFrame(
        {
            "text": ["noise", "small"] + [f"big {i}" for i in range(n_big)] + ["c"],
            "datetime": ["d"] * (n_big + 3),
            "topic_id": [-1, 1] + [2] * n_big + [2],
            "type": ["query"] * (n_big + 2) + ["content"],
        }
    )
    # Topic 1 has no label, so it falls back to `Unknown`.
    labels = {2: {"topic_title": "Big", "topic_summary": "Lots"}}

    result = service.prepare_topics_data(results_df=df, topic_labels=labels)

    assert result.status == "completed"
    assert [t.topic_id for t in result.data] == [2, 1]
    big, small = result.data
    assert (big.topic_name, big.topic_popularity, len(big.topic_samples)) == (
        "Big",
        n_big,
        20,
    )
    assert big.topic_samples[0] == {"query_text": "big 0", "query_datetime_utc": "d"}
    assert (small.topic_name, small.topic_summary) == ("Unknown", "")


class TestTopicModelQueries:
    """Tests for `topic_model_queries`."""

    @pytest.mark.parametrize(
        "n_queries, n_contents, message",
        [
            (0, 1, "No queries to cluster"),
            (1, 0, "No content data to cluster"),
            (498, 1, "Not enough data to cluster"),
        ],
    )
    async def test_guard_clauses(
        self, n_queries: int, n_contents: int, message: str
    ) -> None:
        """Too little data returns an error payload and an empty DataFrame.

        Parameters
        ----------
        n_queries
            Number of queries.
        n_contents
            Number of contents.
        message
            The expected error message prefix.
        """

        topics, df = await service.topic_model_queries(
            content_data=make_contents(n_contents),
            query_data=make_queries(n_queries),
            workspace_id=7,
        )

        assert topics.status == "error"
        assert topics.failure_step == "Run topic modeling"
        assert topics.error_message is not None
        assert topics.error_message.startswith(message)
        assert df.empty

    async def test_full_pipeline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Embedding, fitting and labelling are chained into topics + embeddings.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.
        """

        # 499 queries + 1 content is exactly the 500-item minimum.
        n = 500
        topic_ids = [0] * 300 + [1] * 150 + [-1] * 50
        model = MagicMock()
        model.transform.return_value = (topic_ids, None)
        model.umap_model.embedding_ = np.zeros((n, 2))
        labels = {
            0: {"topic_title": "Zero", "topic_summary": "s0"},
            1: {"topic_title": "One", "topic_summary": "s1"},
        }
        monkeypatch.setattr(
            f"{SVC}.generate_embeddings", MagicMock(return_value=np.zeros((n, 4)))
        )
        monkeypatch.setattr(f"{SVC}.fit_topic_model", MagicMock(return_value=model))
        monkeypatch.setattr(
            f"{SVC}.generate_topic_labels_async", AsyncMock(return_value=labels)
        )

        topics, df = await service.topic_model_queries(
            content_data=make_contents(1),
            query_data=make_queries(n - 1),
            workspace_id=7,
        )

        assert topics.status == "completed"
        assert [(t.topic_name, t.topic_popularity) for t in topics.data] == [
            ("Zero", 300),
            ("One", 150),
        ]
        assert {"x", "y", "topic_id", "topic_title"} <= set(df.columns)
        # The single content row is last and sits in the noise topic.
        assert df["topic_title"].iloc[-1] == "Unclassified"


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def make_embeddings_df(n_topics: int) -> pd.DataFrame:
    """Build a small embeddings DataFrame for plotting.

    Parameters
    ----------
    n_topics
        Number of distinct known topics (one query each).

    Returns
    -------
    pd.DataFrame
        Queries for each topic, plus one `Unknown` query and one content row.
    """

    n = n_topics + 2
    return pd.DataFrame(
        {
            "x": np.arange(n, dtype=float),
            "y": np.arange(n, dtype=float),
            "text": [f"text {i}" for i in range(n)],
            "type": ["query"] * (n - 1) + ["content"],
            "topic_title": [f"Topic {i}" for i in range(n_topics)]
            + ["Unknown", "whatever"],
            "topic_id": list(range(n_topics)) + [n_topics, 0],
        }
    )


class TestProduceBokehPlot:
    """Tests for `produce_bokeh_plot`."""

    def test_missing_columns(self) -> None:
        """A DataFrame without the plot columns raises `InternalServerError`."""

        with pytest.raises(InternalServerError):
            service.produce_bokeh_plot(embeddings_df=pd.DataFrame({"x": [1.0]}))

    # More topics than palette colours exercises the colour-cycling branch.
    @pytest.mark.parametrize("n_topics", [2, len(Turbo256) + 1])
    def test_plot(self, n_topics: int) -> None:
        """The plot is returned as Bokeh JSON and special topics are normalised.

        Parameters
        ----------
        n_topics
            Number of distinct known topics.
        """

        df = make_embeddings_df(n_topics)

        result = service.produce_bokeh_plot(embeddings_df=df)

        assert result["target_id"] == "myplot"
        assert "doc" in result
        # The DataFrame is updated in place: content and `Unknown` rows are recoded.
        content = df[df["type"] == "Content"].iloc[0]
        unknown = df[df["text"] == f"text {n_topics}"].iloc[0]
        assert (content["topic_id"], content["topic_title"]) == (-2, "Content")
        assert (unknown["topic_id"], unknown["topic_title"]) == (-1, "Unclassified")
        assert content["color"] == "gray"
