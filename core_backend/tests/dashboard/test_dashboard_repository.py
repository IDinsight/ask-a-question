"""Tests for `app.dashboard.repository`, run against Postgres in a rolled-back
transaction (`rollback_asession`), so no clean-up is needed."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import numpy as np
import pytest
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.contents.models import ContentDB
from app.contents.schemas import QuerySearchResult
from app.core.config import PGVECTOR_VECTOR_SIZE
from app.dashboard.repository import (
    get_content_details,
    get_content_feedback_stats,
    get_content_feedback_texts,
    get_content_title_and_text,
    get_heatmap,
    get_overview_timeseries,
    get_query_count_stats,
    get_raw_contents,
    get_raw_queries,
    get_response_feedback_stats,
    get_stats_cards,
    get_time_labels_query,
    get_timeseries_query,
    get_timeseries_top_content,
    get_timeseries_urgency,
    get_top_content,
    get_urgency_stats,
)
from app.dashboard.schemas import OverviewTimeSeries, TimeFrequency
from app.question_answer.models import ContentFeedbackDB, QueryDB, ResponseFeedbackDB
from app.question_answer.repository import (
    save_content_feedback_to_db,
    save_content_for_query_to_db,
    save_response_feedback_to_db,
    save_user_query_to_db,
)
from app.question_answer.schemas import (
    ContentFeedback,
    FeedbackSentiment,
    QueryBase,
    ResponseFeedbackBase,
)
from app.urgency_detection.models import UrgencyQueryDB, UrgencyResponseDB
from app.urgency_detection.repository import (
    save_urgency_query_to_db,
    save_urgency_response_to_db,
)
from app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse
from app.workspaces.models import WorkspaceDB
from tests.conftest import MockDatetime


def get_previous_date_and_frequency(*, period: str) -> tuple[datetime, TimeFrequency]:
    """Get the previous date and frequency for the given period.

    Parameters
    ----------
    period
        The period to get the previous date and frequency for.

    Returns
    -------
    tuple[datetime, TimeFrequency]
        The previous date and frequency for the given period.

    Raises
    ------
    ValueError
        If the period is invalid.
    """

    if period == "last_day":
        previous_date = datetime.now(timezone.utc) - timedelta(days=1)
        frequency = TimeFrequency.Hour
    elif period == "last_week":
        previous_date = datetime.now(timezone.utc) - timedelta(weeks=1)
        frequency = TimeFrequency.Day
    elif period == "last_month":
        previous_date = datetime.now(timezone.utc) - timedelta(weeks=4)
        frequency = TimeFrequency.Day
    elif period == "last_year":
        previous_date = datetime.now(timezone.utc) - timedelta(weeks=52)
        frequency = TimeFrequency.Week
    else:
        raise ValueError("Invalid query period.")

    return previous_date, frequency


class TestUrgencyDetectionStats:
    """Tests for the urgency detection stats endpoint."""

    @pytest.fixture(scope="function", params=[(0, 0), (0, 1), (1, 0), (3, 5)])
    async def urgency_detection(
        self,
        rollback_asession: AsyncSession,
        request: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> AsyncGenerator[tuple[int, int], None]:
        """Create urgency detection data for testing in workspace 3.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        request
            The pytest request object.
        workspace_3_id
            The ID of workspace 3.

        Yields
        ------
        tuple[int, int]
            The number of urgent and not urgent queries.
        """

        n_urgent, n_not_urgent = request.param
        data = [(f"Test urgent query {i}", True) for i in range(n_urgent)]
        data += [(f"Test not urgent query {i}", False) for i in range(n_not_urgent)]

        for message_text, is_urgent in data:
            urgency_query = UrgencyQuery(message_text=message_text)
            urgency_query_db = await save_urgency_query_to_db(
                asession=rollback_asession,
                feedback_secret_key="test_secret_key",
                urgency_query=urgency_query,
                workspace_id=workspace_3_id,
            )

            urgency_response = UrgencyResponse(
                details={}, is_urgent=is_urgent, matched_rules=[]
            )
            await save_urgency_response_to_db(
                asession=rollback_asession,
                response=urgency_response,
                urgency_query_db=urgency_query_db,
            )

        yield n_urgent, n_not_urgent

    async def test_urgency_detection_stats(
        self,
        rollback_asession: AsyncSession,
        urgency_detection: tuple[int, int],
        workspace_3_id: int,
    ) -> None:
        """Test the urgency detection stats endpoint.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        urgency_detection
            The number of urgent and not urgent queries.
        workspace_3_id
            The ID of workspace 3.
        """

        n_urgent, _ = urgency_detection

        start_date = datetime.now(timezone.utc) - relativedelta(months=1)
        end_date = datetime.now(timezone.utc) + relativedelta(months=1)

        stats = await get_urgency_stats(
            asession=rollback_asession,
            end_date=end_date,
            start_date=start_date,
            workspace_id=workspace_3_id,
        )

        assert stats.n_urgent == n_urgent
        assert stats.percentage_increase == 0.0


class TestQueryStats:
    """Tests for the query stats endpoint."""

    @pytest.fixture(scope="function")
    async def queries_and_feedbacks(
        self,
        rollback_asession: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
        workspace_3_id: int,
    ) -> AsyncGenerator[None, None]:
        """Create query and feedback data for testing in workspace 3.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        monkeypatch
            The pytest monkeypatch object.
        workspace_3_id
            The ID of workspace 3.

        Yields
        ------
        None
        """

        # The content feedback needs a content row to point at.
        content = await add_content(rollback_asession, workspace_3_id)
        dates = [datetime.now(timezone.utc) - relativedelta(days=x) for x in range(16)]
        for i, date in enumerate(dates):
            monkeypatch.setattr(
                "app.question_answer.repository.datetime",
                MockDatetime(date=date),
            )
            query = QueryBase(generate_llm_response=False, query_text="Test query")
            query_db = await save_user_query_to_db(
                asession=rollback_asession,
                user_query=query,
                workspace_id=workspace_3_id,
            )

            sentiment = (
                FeedbackSentiment.POSITIVE if i % 2 == 0 else FeedbackSentiment.NEGATIVE
            )
            response_feedback = ResponseFeedbackBase(
                feedback_secret_key="test_secret_key",
                feedback_sentiment=sentiment,
                feedback_text=None,
                query_id=query_db.query_id,
                session_id=query_db.session_id,
            )
            await save_response_feedback_to_db(
                asession=rollback_asession, feedback=response_feedback
            )

            content_feedback = ContentFeedback(
                content_id=content.content_id,
                feedback_secret_key="test_secret_key",
                feedback_sentiment=sentiment,
                feedback_text=None,
                query_id=query_db.query_id,
                session_id=query_db.session_id,
            )
            await save_content_feedback_to_db(
                asession=rollback_asession, feedback=content_feedback
            )

        yield

    async def test_query_stats(
        self,
        rollback_asession: AsyncSession,
        queries_and_feedbacks: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> None:
        """Test the query stats endpoint.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        queries_and_feedbacks
            The pytest fixture request object.
        workspace_3_id
            The ID of workspace 3.
        """

        for _i, date in enumerate(
            [datetime.now(timezone.utc) - relativedelta(days=x) for x in range(16)]
        ):
            start_date = date
            end_date = datetime.now(timezone.utc)
            stats = await get_query_count_stats(
                asession=rollback_asession,
                end_date=end_date,
                start_date=start_date,
                workspace_id=workspace_3_id,
            )

            assert stats.n_questions == _i

            stats_response_feedback = await get_response_feedback_stats(
                asession=rollback_asession,
                end_date=end_date,
                start_date=start_date,
                workspace_id=workspace_3_id,
            )

            assert stats_response_feedback.n_positive == (_i + 1) // 2
            assert stats_response_feedback.n_negative == _i // 2

            await get_content_feedback_stats(
                asession=rollback_asession,
                end_date=end_date,
                start_date=start_date,
                workspace_id=workspace_3_id,
            )


class TestHeatmap:
    """Tests for the heatmap endpoint."""

    query_counts = {
        "last_day": {
            "00:00": 12,
            "02:00": 16,
            "04:00": 3,
            "06:00": 5,
            "08:00": 7,
            "10:00": 8,
            "12:00": 9,
            "14:00": 10,
            "16:00": 11,
            "18:00": 12,
            "20:00": 13,
            "22:00": 14,
        },
        "month": {
            "Mon": 13,
            "Tue": 12,
            "Wed": 11,
            "Thu": 10,
            "Fri": 9,
            "Sat": 8,
            "Sun": 7,
        },
        "week": {
            "Mon": 4,
            "Tue": 3,
            "Wed": 2,
            "Thu": 4,
            "Fri": 3,
            "Sat": 4,
            "Sun": 5,
        },
        "year": {
            "Mon": 53,
            "Tue": 52,
            "Wed": 51,
            "Thu": 50,
            "Fri": 49,
            "Sat": 48,
            "Sun": 47,
        },
    }
    weekdays = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}

    @pytest.fixture(scope="function")
    async def queries(
        self,
        rollback_asession: AsyncSession,
        request: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> AsyncGenerator[None, None]:
        """Create query data for testing.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        request
            The pytest request object.
        workspace_3_id
            The ID of workspace 3.

        Yields
        ------
        None

        Raises
        ------
        ValueError
            If the query period is invalid.
        """

        today = datetime.now(timezone.utc)
        today_weekday = today.weekday()
        query_period = request.param
        queries = self.query_counts[query_period]
        for day, count in queries.items():
            target_weekday = self.weekdays[day]
            if query_period == "week":
                multiplier = 0
            elif query_period == "month":
                multiplier = 3
            elif query_period == "year":
                multiplier = 16
            else:
                raise ValueError("Invalid query period.")

            days_difference = (today_weekday - target_weekday - 1) % 7 + 1
            previous_date = (
                today
                - timedelta(days=days_difference + 7 * multiplier)
                + relativedelta(minutes=1)
            )
            for i in range(count):
                query = QueryDB(
                    feedback_secret_key="abc123",
                    query_datetime_utc=previous_date,
                    query_generate_llm_response=False,
                    query_metadata={"day": day},
                    query_text=f"test_{day}_{i}",
                    workspace_id=workspace_3_id,
                )
                rollback_asession.add(query)

        await rollback_asession.commit()

        yield

    @pytest.fixture(scope="function")
    async def queries_hour(
        self, rollback_asession: AsyncSession, workspace_3_id: int
    ) -> AsyncGenerator[None, None]:
        """Create query data for testing.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        workspace_3_id
            The ID of workspace 3.

        Yields
        ------
        None
        """

        current_time = datetime.now(timezone.utc).time()
        today = datetime.now(timezone.utc)
        for hour, count in self.query_counts["last_day"].items():
            time_diff_from_daystart = timedelta(
                hours=current_time.hour,
                minutes=current_time.minute,
                seconds=current_time.second,
                microseconds=current_time.microsecond,
            )
            previous_date = (
                today - time_diff_from_daystart + timedelta(hours=int(hour[0:2]))
            )
            if previous_date > today:
                previous_date = previous_date - timedelta(days=1)
            for i in range(count):
                query = QueryDB(
                    feedback_secret_key="abc123",
                    query_datetime_utc=previous_date,
                    query_generate_llm_response=False,
                    query_metadata={"hour": hour},
                    query_text=f"test_{hour}_{i}",
                    workspace_id=workspace_3_id,
                )
                rollback_asession.add(query)

        await rollback_asession.commit()

        yield

    @pytest.mark.parametrize(
        "queries, period",
        [("week", "week"), ("month", "month"), ("year", "year")],
        indirect=["queries"],
    )
    async def test_heatmap_day(
        self,
        queries: pytest.FixtureRequest,
        period: str,
        rollback_asession: AsyncSession,
        workspace_3_id: int,
    ) -> None:
        """Test the heatmap day endpoint.

        Parameters
        ----------
        queries
            The query to test.
        period
            The period of the query to test.
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        workspace_3_id
            The ID of workspace 3.

        Raises
        ------

        ValueError
            If the query period is invalid.
        """

        today = datetime.now(timezone.utc)
        if period == "week":
            previous_date = today - timedelta(days=7)
        elif period == "month":
            previous_date = today + relativedelta(months=-1)
        elif period == "year":
            previous_date = today + relativedelta(years=-1)
        else:
            raise ValueError("Invalid query period.")

        heatmap = await get_heatmap(
            asession=rollback_asession,
            end_date=today,
            start_date=previous_date,
            workspace_id=workspace_3_id,
        )

        self.check_heatmap_day_totals(
            expected_counts=self.query_counts[period], heatmap=heatmap.model_dump()
        )

    async def test_heatmap_hour(
        self,
        rollback_asession: AsyncSession,
        queries_hour: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> None:
        """Test the heatmap hour endpoint.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        queries_hour
            The query to test.
        workspace_3_id
            The ID of workspace 3.
        """

        today = datetime.now(timezone.utc)
        previous_date = today - timedelta(days=1)
        heatmap = await get_heatmap(
            asession=rollback_asession,
            end_date=today,
            start_date=previous_date,
            workspace_id=workspace_3_id,
        )

        self.check_heatmap_hour_totals(
            expected_counts=self.query_counts["last_day"], heatmap=heatmap.model_dump()
        )

    @staticmethod
    def check_heatmap_day_totals(
        *, expected_counts: dict[str, int], heatmap: dict[str, dict]
    ) -> None:
        """Check the heatmap day totals.

        Parameters
        ----------
        expected_counts
            The expected counts for each day of the week.
        heatmap
            The heatmap to check.
        """

        total_daycount = {
            "Mon": 0,
            "Tue": 0,
            "Wed": 0,
            "Thu": 0,
            "Fri": 0,
            "Sat": 0,
            "Sun": 0,
        }
        for _hour, daycount in heatmap.items():
            for day, count in daycount.items():
                total_daycount[day] += count
        for day, count in total_daycount.items():
            assert count == expected_counts[day]

    @staticmethod
    def check_heatmap_hour_totals(
        *, heatmap: dict[str, dict], expected_counts: dict[str, int]
    ) -> None:
        """Check the heatmap hour totals.

        Parameters
        ----------
        expected_counts
            The expected counts for each hour of the day.
        heatmap
            The heatmap to check.
        """

        total_hourcount = {f"{i * 2:02}:00": 0 for i in range(12)}
        for _hour, daycount in heatmap.items():
            total_hourcount[_hour.replace("h", "").replace("_", ":")] += sum(
                list(daycount.values())
            )

        for hour, count in total_hourcount.items():
            assert count == expected_counts[hour]


class TestTimeSeries:
    """Tests for the time series endpoints."""

    N_NEUTRAL = 5
    data_to_create = {
        "last_2_years": {"urgent": 6, "positive": 10, "negative": 4},
        "last_day": {"urgent": 0, "positive": 3, "negative": 0},
        "last_month": {"urgent": 7, "positive": 10, "negative": 5},
        "last_week": {"urgent": 3, "positive": 5, "negative": 2},
        "last_year": {"urgent": 30, "positive": 50, "negative": 20},
    }

    @pytest.fixture(scope="function")
    async def create_data(
        self,
        rollback_asession: AsyncSession,
        request: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> AsyncGenerator[None, None]:
        """Create data for testing.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        request
            The pytest request object.
        workspace_3_id
            The ID of workspace 3.

        Yields
        ------
        None

        Raises
        ------
        ValueError
            If the period is invalid.
        """

        period = request.param
        data_to_create = self.data_to_create[period]
        urgent = data_to_create["urgent"]
        n_positive = data_to_create["positive"]
        n_negative = data_to_create["negative"]

        if period == "last_day":
            dt = datetime.now(timezone.utc) - timedelta(days=1)
        elif period == "last_week":
            dt = datetime.now(timezone.utc) - timedelta(weeks=1)
        elif period == "last_month":
            dt = datetime.now(timezone.utc) - timedelta(weeks=4)
        elif period == "last_year":
            dt = datetime.now(timezone.utc) - timedelta(weeks=52)
        else:
            raise ValueError("Invalid period.")

        dt_two_years = datetime.now(timezone.utc) - timedelta(weeks=104)
        urgent_two_years = self.data_to_create["last_2_years"]["urgent"]
        n_positive_two_years = self.data_to_create["last_2_years"]["positive"]
        n_negative_two_years = self.data_to_create["last_2_years"]["negative"]

        await self.create_urgency_query_and_response(
            asession=rollback_asession,
            created_datetime=dt,
            urgent=urgent,
            workspace_id=workspace_3_id,
        )
        await self.create_urgency_query_and_response(
            asession=rollback_asession,
            created_datetime=dt_two_years,
            urgent=urgent_two_years,
            workspace_id=workspace_3_id,
        )

        await self.create_query_and_feedback(
            asession=rollback_asession,
            created_datetime=dt,
            n_negative=n_negative,
            n_neutral=self.N_NEUTRAL,
            n_positive=n_positive,
            workspace_id=workspace_3_id,
        )
        await self.create_query_and_feedback(
            asession=rollback_asession,
            created_datetime=dt_two_years,
            n_negative=n_negative_two_years,
            n_neutral=self.N_NEUTRAL,
            n_positive=n_positive_two_years,
            workspace_id=workspace_3_id,
        )

        yield

    @staticmethod
    async def create_urgency_query_and_response(
        *,
        asession: AsyncSession,
        created_datetime: datetime,
        urgent: int,
        workspace_id: int,
    ) -> None:
        """Create urgency query and response data for testing.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        created_datetime
            The datetime to use for the created datetime of the urgency query and
            response.
        urgent
            The number of urgent queries to create.
        workspace_id
            The ID of the workspace to create the urgency query and response in.
        """

        # Insert in two batches (queries, then responses) to save round trips.
        urgency_queries = [
            UrgencyQueryDB(
                feedback_secret_key="abc123",
                message_datetime_utc=created_datetime,
                message_text="test message",
                workspace_id=workspace_id,
            )
            for _ in range(urgent * 2)
        ]
        asession.add_all(urgency_queries)
        await asession.flush()
        asession.add_all(
            UrgencyResponseDB(
                details={"details": "test details"},
                is_urgent=(i % 2 == 0),
                query_id=urgency_db.urgency_query_id,
                response_datetime_utc=created_datetime,
                workspace_id=workspace_id,
            )
            for i, urgency_db in enumerate(urgency_queries)
        )
        await asession.flush()

    @staticmethod
    async def create_query_and_feedback(
        *,
        asession: AsyncSession,
        created_datetime: datetime,
        n_negative: int,
        n_neutral: int,
        n_positive: int,
        workspace_id: int,
    ) -> None:
        """Create query and feedback data for testing.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        created_datetime
            The datetime to use for the created datetime of the query and feedback.
        n_negative
            The number of negative feedback to create.
        n_neutral
            The number of neutral feedback to create.
        n_positive
            The number of positive feedback to create.
        workspace_id
            The ID of the workspace to create the query and feedback in.
        """

        sentiments = (
            ["positive"] * n_positive
            + ["negative"] * n_negative
            + ["neutral"] * n_neutral
        )
        # Insert in two batches (queries, then feedback) to save round trips.
        queries = [
            QueryDB(
                feedback_secret_key="abc123",
                query_datetime_utc=created_datetime,
                query_generate_llm_response=False,
                query_metadata={"details": "test details"},
                query_text="test message",
                workspace_id=workspace_id,
            )
            for _ in sentiments
        ]
        asession.add_all(queries)
        await asession.flush()
        asession.add_all(
            ResponseFeedbackDB(
                feedback_datetime_utc=created_datetime,
                feedback_sentiment=sentiment,
                query_id=query.query_id,
                session_id=query.session_id,
                workspace_id=workspace_id,
            )
            for query, sentiment in zip(queries, sentiments, strict=True)
        )
        await asession.flush()

    @pytest.mark.parametrize(
        "create_data, period",
        [
            ("last_day", "last_day"),
            ("last_week", "last_week"),
            ("last_month", "last_month"),
            ("last_year", "last_year"),
        ],
        indirect=["create_data"],
    )
    async def test_time_series(
        self,
        create_data: pytest.FixtureRequest,
        period: str,
        rollback_asession: AsyncSession,
        workspace_3_id: int,
    ) -> None:
        """Test the time series endpoint.

        Parameters
        ----------
        create_data
            The data to create for the given time series.
        period
            The period to test the time series for.
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        workspace_3_id
            The ID of workspace 3.
        """

        today = datetime.now(timezone.utc)
        previous_date, frequency = get_previous_date_and_frequency(period=period)
        n_escalated = self.data_to_create[period]["negative"]
        n_not_escalated = self.data_to_create[period]["positive"] + self.N_NEUTRAL

        query_ts = await get_timeseries_query(
            asession=rollback_asession,
            end_date=today,
            frequency=frequency,
            start_date=previous_date,
            workspace_id=workspace_3_id,
        )

        assert sum(list(query_ts["escalated"].values())) == n_escalated
        assert sum(list(query_ts["not_escalated"].values())) == n_not_escalated

    @pytest.mark.parametrize(
        "create_data, period",
        [
            ("last_day", "last_day"),
            ("last_week", "last_week"),
            ("last_month", "last_month"),
            ("last_year", "last_year"),
        ],
        indirect=["create_data"],
    )
    async def test_time_series_urgency(
        self,
        create_data: pytest.FixtureRequest,
        period: str,
        rollback_asession: AsyncSession,
        workspace_3_id: int,
    ) -> None:
        """Test the time series urgency endpoint.

        Parameters
        ----------
        create_data
            The data to create for the given time series.
        period
            The period to test the time series for.
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        workspace_3_id
            The ID of workspace 3.
        """

        today = datetime.now(timezone.utc)
        previous_date, frequency = get_previous_date_and_frequency(period=period)

        n_urgent = self.data_to_create[period]["urgent"]
        urgency_ts = await get_timeseries_urgency(
            asession=rollback_asession,
            end_date=today,
            frequency=frequency,
            start_date=previous_date,
            workspace_id=workspace_3_id,
        )

        assert sum(list(urgency_ts.values())) == n_urgent

    @pytest.mark.parametrize(
        "create_data, period",
        [
            ("last_day", "last_day"),
            ("last_week", "last_week"),
            ("last_month", "last_month"),
            ("last_year", "last_year"),
        ],
        indirect=["create_data"],
    )
    async def test_full_overview_timeseries_format(
        self,
        create_data: pytest.FixtureRequest,
        period: str,
        rollback_asession: AsyncSession,
        workspace_3_id: int,
    ) -> None:
        """Test the full overview timeseries format.

        Parameters
        ----------
        create_data
            The data to create for the given time series.
        period
            The period to test the time series for.
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        workspace_3_id
            The ID of workspace 3.
        """

        today = datetime.now(timezone.utc)
        previous_date, frequency = get_previous_date_and_frequency(period=period)

        overview_ts = await get_overview_timeseries(
            asession=rollback_asession,
            start_date=previous_date,
            end_date=today,
            frequency=frequency,
            workspace_id=workspace_3_id,
        )

        assert isinstance(overview_ts, OverviewTimeSeries)

        assert hasattr(overview_ts, "downvoted")
        assert hasattr(overview_ts, "normal")
        assert hasattr(overview_ts, "urgent")

        assert isinstance(overview_ts.urgent, dict)
        assert isinstance(overview_ts.downvoted, dict)
        assert isinstance(overview_ts.normal, dict)

        # Quick check for types of keys and vals.
        if overview_ts.urgent:
            first_ts_key = next(iter(overview_ts.urgent.keys()))
            assert isinstance(first_ts_key, str)
            assert isinstance(overview_ts.urgent[first_ts_key], int)


class TestTopContent:
    """Tests for the top content endpoint."""

    content: list[dict[str, str | int]] = [
        {
            "title": "Ways to manage back pain during pregnancy",
            "query_count": 100,
            "positive_votes": 50,
            "negative_votes": 10,
        },
        {
            "title": "Headache during pregnancy is normal ‚except after 20 weeks",
            "query_count": 200,
            "positive_votes": 100,
            "negative_votes": 20,
        },
        {
            "title": "Yes, pregnancy can cause TOOTHACHE",
            "query_count": 300,
            "positive_votes": 150,
            "negative_votes": 30,
        },
        {
            "title": "Ways to manage HEARTBURN in pregnancy",
            "query_count": 400,
            "positive_votes": 200,
            "negative_votes": 40,
        },
        {
            "title": "Some LEG cramps are normal during pregnancy",
            "query_count": 500,
            "positive_votes": 250,
            "negative_votes": 50,
        },
    ]

    @pytest.fixture(scope="function")
    async def content_data(
        self, rollback_asession: AsyncSession, workspace_3_id: int
    ) -> AsyncGenerator[None, None]:
        """Add `N_DATAPOINTS` of data for each day in the past year.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        workspace_3_id
            The ID of workspace 3.

        Yields
        ------
        None
        """

        for _i, c in enumerate(self.content):
            content_db = ContentDB(
                content_embedding=np.random.rand(int(PGVECTOR_VECTOR_SIZE))
                .astype(np.float32)
                .tolist(),
                content_metadata={},
                content_text=f"Test content #{_i}",
                content_title=c["title"],
                created_datetime_utc=datetime.now(timezone.utc),
                is_archived=_i % 2 == 0,  # Mix archived content into DB
                negative_votes=c["negative_votes"],
                positive_votes=c["positive_votes"],
                query_count=c["query_count"],
                updated_datetime_utc=datetime.now(timezone.utc),
                workspace_id=workspace_3_id,
            )
            rollback_asession.add(content_db)

        await rollback_asession.commit()

        yield

    async def test_top_content(
        self,
        rollback_asession: AsyncSession,
        content_data: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> None:
        """Test the top content endpoint.

        NB: The archive feature will prepend the string "[DELETED] " to the content
        card title if the content card has been archived.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        content_data
            The pytest fixture request object.
        workspace_3_id
            The ID of workspace 3.
        """

        top_n = 4
        top_content = await get_top_content(
            asession=rollback_asession, top_n=top_n, workspace_id=workspace_3_id
        )
        assert len(top_content) == top_n

        # Sort `self.content` by query count.
        content_sorted = sorted(
            self.content, key=lambda x: x["query_count"], reverse=True
        )
        for i, c in enumerate(content_sorted[:top_n]):
            if i % 2 == 0:
                assert top_content[i].title == "[DELETED] " + str(c["title"])
            else:
                assert top_content[i].title == c["title"]
            assert top_content[i].query_count == c["query_count"]
            assert top_content[i].positive_votes == c["positive_votes"]
            assert top_content[i].negative_votes == c["negative_votes"]

    async def test_content_from_other_user_not_returned(
        self,
        rollback_asession: AsyncSession,
        content_data: pytest.FixtureRequest,
        workspace_2_id: int,
    ) -> None:
        """Test that content from other users is not returned.

        Parameters
        ----------
        rollback_asession
            The SQLAlchemy async session to use for all database connections.
        content_data
            The pytest fixture request object.
        workspace_2_id
            The ID of workspace 2.
        """

        top_content = await get_top_content(
            asession=rollback_asession, top_n=5, workspace_id=workspace_2_id
        )

        assert len(top_content) == 0


# ---------------------------------------------------------------------------
# Content performance (moved from the old performance-endpoint tests)
# ---------------------------------------------------------------------------
N_CONTENT_SHARED = [12, 10, 8, 6, 4]

# timeframe -> (bucket frequency, window length, half a bucket window).
PERFORMANCE_WINDOWS = {
    "day": (TimeFrequency.Hour, relativedelta(days=1), relativedelta(hours=12)),
    "week": (TimeFrequency.Day, relativedelta(weeks=1), relativedelta(days=4)),
    "month": (TimeFrequency.Day, relativedelta(months=1), relativedelta(days=15)),
    "year": (TimeFrequency.Month, relativedelta(years=1), relativedelta(days=180)),
}


def get_performance_window(
    *, timeframe: str
) -> tuple[TimeFrequency, datetime, datetime]:
    """Get the frequency and window the dashboard uses for a timeframe.

    Parameters
    ----------
    timeframe
        One of `day`, `week`, `month` or `year`.

    Returns
    -------
    tuple[TimeFrequency, datetime, datetime]
        The bucket frequency and the start and end of the window (ending now).
    """

    frequency, span, _ = PERFORMANCE_WINDOWS[timeframe]
    end_date = datetime.now(timezone.utc)
    return frequency, end_date - span, end_date


@pytest.fixture(params=list(PERFORMANCE_WINDOWS))
async def content_with_query_history(
    request: pytest.FixtureRequest,
    rollback_asession: AsyncSession,
    fresh_workspace_id: int,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[str, list[int]]:
    """Create contents in a fresh workspace with a share and feedback history.

    The length of `N_CONTENT_SHARED` is the number of contents that get a history,
    and each value is how many times that content is shared in the current period.
    The previous period gets ~1/2 of that and the period before ~1/3.

    Parameters
    ----------
    request
        The pytest request object; `param` is the timeframe.
    rollback_asession
        Session whose writes are discarded at the end of the test.
    fresh_workspace_id
        An empty workspace only this test can see.
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    tuple[str, list[int]]
        The timeframe the history was built for and the content IDs, most shared
        first.
    """

    _, _, delta = PERFORMANCE_WINDOWS[request.param]

    # One query is reused for every search result. This is a convenience that does
    # not happen in the real application.
    query_db = await save_user_query_to_db(
        asession=rollback_asession,
        user_query=QueryBase(
            generate_llm_response=False,
            query_metadata={},
            query_text="Test query - content history",
        ),
        workspace_id=fresh_workspace_id,
    )
    content_ids = [
        (
            await add_content(rollback_asession, fresh_workspace_id, f"Content {i}")
        ).content_id
        for i in range(len(N_CONTENT_SHARED))
    ]

    for idx, (n_response, content_id) in enumerate(
        zip(N_CONTENT_SHARED, content_ids, strict=True)
    ):
        sentiment = (
            FeedbackSentiment.POSITIVE if idx % 2 == 0 else FeedbackSentiment.NEGATIVE
        )
        # Current period (1 delta ago), previous (3 deltas) and the one before (5).
        for n_deltas, n_shares, offset in (
            (1, n_response, 0),
            (3, n_response // 2, n_response),
            (5, n_response // 3, 2 * n_response),
        ):
            monkeypatch.setattr(
                "app.question_answer.repository.datetime",
                MockDatetime(date=datetime.now(timezone.utc) - delta * n_deltas),
            )
            await save_content_for_query_to_db(
                asession=rollback_asession,
                contents={
                    idx * 100 + offset + i: QuerySearchResult(
                        distance=0.5,
                        id=content_id,
                        text="test text",
                        title=f"test title {content_id}",
                    )
                    for i in range(n_shares)
                },
                query_id=query_db.query_id,
                session_id=1,
                workspace_id=fresh_workspace_id,
            )
            await save_content_feedback_to_db(
                asession=rollback_asession,
                feedback=ContentFeedback(
                    content_id=content_ids[0],
                    feedback_secret_key="secret key",
                    feedback_sentiment=sentiment,
                    feedback_text="Great content",
                    query_id=query_db.query_id,
                    session_id=query_db.session_id,
                ),
            )

    return request.param, content_ids


class TestContentPerformance:
    """Tests for `get_timeseries_top_content` and `get_content_details`."""

    @pytest.mark.parametrize("n_top", [1, 3, 500, None])
    async def test_timeseries_top_content(
        self,
        n_top: int | None,
        content_with_query_history: tuple[str, list[int]],
        rollback_asession: AsyncSession,
        fresh_workspace_id: int,
    ) -> None:
        """The top contents are ranked by shares in the current window.

        Parameters
        ----------
        n_top
            The number of top contents to retrieve (`None` for no limit).
        content_with_query_history
            The timeframe the history was built for, and the content IDs.
        rollback_asession
            Session whose writes are discarded at the end of the test.
        fresh_workspace_id
            An empty workspace only this test can see.
        """

        frequency, start_date, end_date = get_performance_window(
            timeframe=content_with_query_history[0]
        )

        time_series = await get_timeseries_top_content(
            asession=rollback_asession,
            end_date=end_date,
            frequency=frequency,
            start_date=start_date,
            top_n=n_top,
            workspace_id=fresh_workspace_id,
        )

        assert len(time_series) == min(n_top or 500, len(N_CONTENT_SHARED))
        for content_count, content_stats in zip(
            N_CONTENT_SHARED, time_series, strict=False
        ):
            assert sum(content_stats.query_count_time_series.values()) == content_count

    async def test_other_workspace_sees_nothing(
        self,
        content_with_query_history: tuple[str, list[int]],
        rollback_asession: AsyncSession,
        workspace_2_id: int,
    ) -> None:
        """Another workspace does not see this workspace's content history.

        Parameters
        ----------
        content_with_query_history
            The timeframe the history was built for, and the content IDs.
        rollback_asession
            Session whose writes are discarded at the end of the test.
        workspace_2_id
            The ID of workspace 2.
        """

        frequency, start_date, end_date = get_performance_window(
            timeframe=content_with_query_history[0]
        )

        time_series = await get_timeseries_top_content(
            asession=rollback_asession,
            end_date=end_date,
            frequency=frequency,
            start_date=start_date,
            top_n=1,
            workspace_id=workspace_2_id,
        )

        assert time_series == []

    async def test_content_details(
        self,
        content_with_query_history: tuple[str, list[int]],
        rollback_asession: AsyncSession,
        fresh_workspace_id: int,
    ) -> None:
        """The drawer counts shares and votes in the window and caps the feedback.

        Parameters
        ----------
        content_with_query_history
            The timeframe the history was built for, and the content IDs.
        rollback_asession
            Session whose writes are discarded at the end of the test.
        fresh_workspace_id
            An empty workspace only this test can see.
        """

        frequency, start_date, end_date = get_performance_window(
            timeframe=content_with_query_history[0]
        )
        max_feedback_records = 10

        drawer_data = await get_content_details(
            asession=rollback_asession,
            content_id=content_with_query_history[1][0],
            end_date=end_date,
            frequency=frequency,
            max_feedback_records=max_feedback_records,
            start_date=start_date,
            workspace_id=fresh_workspace_id,
        )

        assert drawer_data.query_count == N_CONTENT_SHARED[0]
        assert drawer_data.positive_votes == np.ceil(len(N_CONTENT_SHARED) / 2)
        assert drawer_data.negative_votes == np.floor(len(N_CONTENT_SHARED) / 2)
        assert len(drawer_data.user_feedback) == min(
            len(N_CONTENT_SHARED), max_feedback_records
        )


# ---------------------------------------------------------------------------
# Small reads, each in a fresh workspace created inside the rolled-back session
# ---------------------------------------------------------------------------
NOW = datetime.now(timezone.utc)
WINDOW_START = NOW - timedelta(days=7)


@pytest.fixture
async def fresh_workspace_id(rollback_asession: AsyncSession) -> int:
    """Create an empty workspace that only this test can see.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.

    Returns
    -------
    int
        The new workspace's ID.
    """

    workspace = WorkspaceDB(
        created_datetime_utc=NOW,
        doc_language="ENGLISH",
        updated_datetime_utc=NOW,
        workspace_name=f"dashboard_repo_{uuid.uuid4().hex[:8]}",
    )
    rollback_asession.add(workspace)
    await rollback_asession.flush()
    return workspace.workspace_id


async def add_content(
    asession: AsyncSession, workspace_id: int, title: str = "Title"
) -> ContentDB:
    """Insert a content row.

    Parameters
    ----------
    asession
        The session to insert with.
    workspace_id
        The owning workspace.
    title
        The content title.

    Returns
    -------
    ContentDB
        The flushed content.
    """

    content = ContentDB(
        content_embedding=[0.0] * int(PGVECTOR_VECTOR_SIZE),
        content_metadata={},
        content_text=f"{title} text",
        content_title=title,
        created_datetime_utc=NOW,
        updated_datetime_utc=NOW,
        workspace_id=workspace_id,
    )
    asession.add(content)
    await asession.flush()
    return content


async def add_query(
    asession: AsyncSession, workspace_id: int, when: datetime, text: str = "q"
) -> QueryDB:
    """Insert a query row at a given time.

    Parameters
    ----------
    asession
        The session to insert with.
    workspace_id
        The owning workspace.
    when
        The query datetime.
    text
        The query text.

    Returns
    -------
    QueryDB
        The flushed query.
    """

    query = QueryDB(
        feedback_secret_key="abc123",
        query_datetime_utc=when,
        query_generate_llm_response=False,
        query_metadata={},
        query_text=text,
        workspace_id=workspace_id,
    )
    asession.add(query)
    await asession.flush()
    return query


async def test_content_title_and_text(
    rollback_asession: AsyncSession, fresh_workspace_id: int, workspace_2_id: int
) -> None:
    """The title and text are returned only for the owning workspace.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.
    fresh_workspace_id
        An empty workspace.
    workspace_2_id
        Another workspace.
    """

    content = await add_content(rollback_asession, fresh_workspace_id, "Malaria")

    row = await get_content_title_and_text(
        asession=rollback_asession,
        content_id=content.content_id,
        workspace_id=fresh_workspace_id,
    )
    other = await get_content_title_and_text(
        asession=rollback_asession,
        content_id=content.content_id,
        workspace_id=workspace_2_id,
    )

    assert row is not None
    assert (row.content_title, row.content_text) == ("Malaria", "Malaria text")
    assert other is None


async def test_content_feedback_texts(
    rollback_asession: AsyncSession, fresh_workspace_id: int
) -> None:
    """Only non-empty feedback inside the window is returned, newest first, capped.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.
    fresh_workspace_id
        An empty workspace.
    """

    content = await add_content(rollback_asession, fresh_workspace_id)
    query = await add_query(rollback_asession, fresh_workspace_id, NOW)
    feedback = [
        ("older", NOW - timedelta(days=2)),
        ("newest", NOW - timedelta(hours=1)),
        ("middle", NOW - timedelta(days=1)),
        ("", NOW - timedelta(hours=2)),  # Empty text is skipped.
        (None, NOW - timedelta(hours=3)),  # Missing text is skipped.
        ("too old", NOW - timedelta(days=30)),  # Outside the window.
    ]
    rollback_asession.add_all(
        ContentFeedbackDB(
            content_id=content.content_id,
            feedback_datetime_utc=when,
            feedback_sentiment="positive",
            feedback_text=text,
            query_id=query.query_id,
            workspace_id=fresh_workspace_id,
        )
        for text, when in feedback
    )
    await rollback_asession.flush()

    texts = await get_content_feedback_texts(
        asession=rollback_asession,
        content_id=content.content_id,
        end_date=NOW,
        max_feedback_records=2,
        start_date=WINDOW_START,
        workspace_id=fresh_workspace_id,
    )

    assert texts == ["newest", "middle"]


async def test_content_details_without_history(
    rollback_asession: AsyncSession, fresh_workspace_id: int
) -> None:
    """A content that was never shared has a zero-filled drawer.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.
    fresh_workspace_id
        An empty workspace.
    """

    content = await add_content(rollback_asession, fresh_workspace_id)

    drawer = await get_content_details(
        asession=rollback_asession,
        content_id=content.content_id,
        end_date=NOW,
        frequency=TimeFrequency.Day,
        max_feedback_records=5,
        start_date=WINDOW_START,
        workspace_id=fresh_workspace_id,
    )

    # Every day in the window is present, zero-filled.
    assert (drawer.title, drawer.query_count, drawer.user_feedback) == ("Title", 0, [])
    assert len(drawer.time_series) >= 7
    assert all(set(counts.values()) == {0} for counts in drawer.time_series.values())


async def test_raw_contents_and_queries(
    rollback_asession: AsyncSession, fresh_workspace_id: int
) -> None:
    """Topic-modelling inputs are read for the workspace and window only.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.
    fresh_workspace_id
        An empty workspace.
    """

    empty_contents = await get_raw_contents(
        asession=rollback_asession, workspace_id=fresh_workspace_id
    )
    empty_queries = await get_raw_queries(
        asession=rollback_asession,
        end_date=NOW,
        start_date=WINDOW_START,
        workspace_id=fresh_workspace_id,
    )
    content = await add_content(rollback_asession, fresh_workspace_id, "Fever")
    in_window = await add_query(
        rollback_asession, fresh_workspace_id, NOW - timedelta(days=1), "in"
    )
    await add_query(rollback_asession, fresh_workspace_id, NOW - timedelta(days=30))

    contents = await get_raw_contents(
        asession=rollback_asession, workspace_id=fresh_workspace_id
    )
    queries = await get_raw_queries(
        asession=rollback_asession,
        end_date=NOW,
        start_date=WINDOW_START,
        workspace_id=fresh_workspace_id,
    )

    assert (empty_contents, empty_queries) == ([], [])
    assert [(c.content_id, c.content_title) for c in contents] == [
        (content.content_id, "Fever")
    ]
    assert [(q.query_id, q.query_text) for q in queries] == [(in_window.query_id, "in")]


async def test_stats_cards_for_empty_workspace(
    rollback_asession: AsyncSession, fresh_workspace_id: int
) -> None:
    """An empty workspace has all-zero stats cards.

    Parameters
    ----------
    rollback_asession
        Session whose writes are discarded at the end of the test.
    fresh_workspace_id
        An empty workspace.
    """

    stats = await get_stats_cards(
        asession=rollback_asession,
        end_date=NOW,
        start_date=WINDOW_START,
        workspace_id=fresh_workspace_id,
    )

    assert stats.query_stats.n_questions == 0
    assert stats.urgency_stats.n_urgent == 0
    assert stats.content_feedback_stats.n_positive == 0
    assert stats.response_feedback_stats.n_negative == 0


def test_time_labels_query_rejects_unknown_frequency() -> None:
    """An unknown frequency raises `ValueError`."""

    with pytest.raises(ValueError, match="Invalid frequency"):
        get_time_labels_query(
            end_date=NOW,
            frequency="Fortnight",  # type: ignore[arg-type]
            start_date=WINDOW_START,
        )
