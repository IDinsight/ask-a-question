"""This module contains tests for the dashboard overview endpoints."""

from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import numpy as np
import pytest
from dateutil.relativedelta import relativedelta
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core_backend.app.config import PGVECTOR_VECTOR_SIZE
from core_backend.app.contents.models import ContentDB
from core_backend.app.dashboard.models import (
    get_content_feedback_stats,
    get_heatmap,
    get_overview_timeseries,
    get_query_count_stats,
    get_response_feedback_stats,
    get_timeseries_query,
    get_timeseries_urgency,
    get_top_content,
    get_urgency_stats,
)
from core_backend.app.dashboard.schemas import OverviewTimeSeries, TimeFrequency
from core_backend.app.question_answer.models import (
    ContentFeedbackDB,
    QueryDB,
    ResponseFeedbackDB,
    save_content_feedback_to_db,
    save_response_feedback_to_db,
    save_user_query_to_db,
)
from core_backend.app.question_answer.schemas import (
    ContentFeedback,
    QueryBase,
    ResponseFeedbackBase,
)
from core_backend.app.schemas import FeedbackSentiment
from core_backend.app.urgency_detection.models import (
    UrgencyQueryDB,
    UrgencyResponseDB,
    save_urgency_query_to_db,
    save_urgency_response_to_db,
)
from core_backend.app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse

from .conftest import MockDatetime


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
        asession: AsyncSession,
        request: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> AsyncGenerator[tuple[int, int], None]:
        """Create urgency detection data for testing in workspace 3.

        Parameters
        ----------
        asession
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

        urgency_query_ids = []
        urgency_response_ids = []
        for message_text, is_urgent in data:
            urgency_query = UrgencyQuery(message_text=message_text)
            urgency_query_db = await save_urgency_query_to_db(
                asession=asession,
                feedback_secret_key="test_secret_key",
                urgency_query=urgency_query,
                workspace_id=workspace_3_id,
            )

            urgency_response = UrgencyResponse(
                details={}, is_urgent=is_urgent, matched_rules=[]
            )
            await save_urgency_response_to_db(
                asession=asession,
                response=urgency_response,
                urgency_query_db=urgency_query_db,
            )

            urgency_query_ids.append(urgency_query_db.urgency_query_id)
            urgency_response_ids.append(urgency_query_db.urgency_query_id)

        yield n_urgent, n_not_urgent

        await self.delete_urgency_data(
            asession=asession,
            urgency_detection_ids=urgency_query_ids,
            urgency_response_ids=urgency_response_ids,
        )

    @staticmethod
    async def delete_urgency_data(
        *,
        asession: AsyncSession,
        urgency_detection_ids: list[int],
        urgency_response_ids: list[int],
    ) -> None:
        """Delete urgency detection data from the database.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        urgency_detection_ids
            The IDs of the urgency detection queries to delete.
        urgency_response_ids
            The IDs of the urgency detection responses to delete.
        """

        delete_urgency_response = delete(UrgencyResponseDB).where(
            UrgencyResponseDB.urgency_response_id.in_(urgency_response_ids)
        )
        await asession.execute(delete_urgency_response)
        delete_urgency_query = delete(UrgencyQueryDB).where(
            UrgencyQueryDB.urgency_query_id.in_(urgency_detection_ids)
        )
        await asession.execute(delete_urgency_query)
        await asession.commit()

    async def test_urgency_detection_stats(
        self,
        asession: AsyncSession,
        urgency_detection: tuple[int, int],
        workspace_3_id: int,
    ) -> None:
        """Test the urgency detection stats endpoint.

        Parameters
        ----------
        asession
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
            asession=asession,
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
        asession: AsyncSession,
        faq_contents_in_workspace_3: list[int],
        monkeypatch: pytest.MonkeyPatch,
        workspace_3_id: int,
    ) -> AsyncGenerator[None, None]:
        """Create query and feedback data for testing in workspace 1.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        faq_contents_in_workspace_3
            The IDs of the FAQ contents in workspace 3.
        monkeypatch
            The pytest monkeypatch object.
        workspace_3_id
            The ID of workspace 3.

        Yields
        ------
        None
        """

        dates = [datetime.now(timezone.utc) - relativedelta(days=x) for x in range(16)]
        for i, date in enumerate(dates):
            monkeypatch.setattr(
                "core_backend.app.question_answer.models.datetime",
                MockDatetime(date=date),
            )
            query = QueryBase(generate_llm_response=False, query_text="Test query")
            query_db = await save_user_query_to_db(
                asession=asession,
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
                asession=asession, feedback=response_feedback
            )

            content_feedback = ContentFeedback(
                content_id=faq_contents_in_workspace_3[0],
                feedback_secret_key="test_secret_key",
                feedback_sentiment=sentiment,
                feedback_text=None,
                query_id=query_db.query_id,
                session_id=query_db.session_id,
            )
            await save_content_feedback_to_db(
                asession=asession, feedback=content_feedback
            )

        yield

        delete_response_feedback = delete(ResponseFeedbackDB).where(
            ResponseFeedbackDB.query_id > 0
        )
        await asession.execute(delete_response_feedback)
        delete_content_feedback = delete(ContentFeedbackDB).where(
            ContentFeedbackDB.query_id > 0
        )
        await asession.execute(delete_content_feedback)
        delete_query = delete(QueryDB).where(QueryDB.query_id > 0)
        await asession.execute(delete_query)
        await asession.commit()

    async def test_query_stats(
        self,
        asession: AsyncSession,
        queries_and_feedbacks: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> None:
        """Test the query stats endpoint.

        Parameters
        ----------
        asession
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
                asession=asession,
                end_date=end_date,
                start_date=start_date,
                workspace_id=workspace_3_id,
            )

            assert stats.n_questions == _i

            stats_response_feedback = await get_response_feedback_stats(
                asession=asession,
                end_date=end_date,
                start_date=start_date,
                workspace_id=workspace_3_id,
            )

            assert stats_response_feedback.n_positive == (_i + 1) // 2
            assert stats_response_feedback.n_negative == _i // 2

            await get_content_feedback_stats(
                asession=asession,
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
        asession: AsyncSession,
        request: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> AsyncGenerator[None, None]:
        """Create query data for testing.

        Parameters
        ----------
        asession
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
                asession.add(query)

        await asession.commit()

        yield

        delete_query = delete(QueryDB).where(QueryDB.query_id > 0)
        await asession.execute(delete_query)
        await asession.commit()

    @pytest.fixture(scope="function")
    async def queries_hour(
        self, asession: AsyncSession, workspace_3_id: int
    ) -> AsyncGenerator[None, None]:
        """Create query data for testing.

        Parameters
        ----------
        asession
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
                asession.add(query)

        await asession.commit()

        yield

        delete_query = delete(QueryDB).where(QueryDB.query_id > 0)
        await asession.execute(delete_query)
        await asession.commit()

    @pytest.mark.parametrize(
        "queries, period",
        [("week", "week"), ("month", "month"), ("year", "year")],
        indirect=["queries"],
    )
    async def test_heatmap_day(
        self,
        queries: pytest.FixtureRequest,
        period: str,
        asession: AsyncSession,
        workspace_3_id: int,
    ) -> None:
        """Test the heatmap day endpoint.

        Parameters
        ----------
        queries
            The query to test.
        period
            The period of the query to test.
        asession
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
            asession=asession,
            end_date=today,
            start_date=previous_date,
            workspace_id=workspace_3_id,
        )

        self.check_heatmap_day_totals(
            expected_counts=self.query_counts[period], heatmap=heatmap.model_dump()
        )

    async def test_heatmap_hour(
        self,
        asession: AsyncSession,
        queries_hour: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> None:
        """Test the heatmap hour endpoint.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        queries_hour
            The query to test.
        workspace_3_id
            The ID of workspace 3.
        """

        today = datetime.now(timezone.utc)
        previous_date = today - timedelta(days=1)
        heatmap = await get_heatmap(
            asession=asession,
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

        total_hourcount = {f"{i*2:02}:00": 0 for i in range(12)}
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
        asession: AsyncSession,
        request: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> AsyncGenerator[None, None]:
        """Create data for testing.

        Parameters
        ----------
        asession
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
            asession=asession,
            created_datetime=dt,
            urgent=urgent,
            workspace_id=workspace_3_id,
        )
        await self.create_urgency_query_and_response(
            asession=asession,
            created_datetime=dt_two_years,
            urgent=urgent_two_years,
            workspace_id=workspace_3_id,
        )

        await self.create_query_and_feedback(
            asession=asession,
            created_datetime=dt,
            n_negative=n_negative,
            n_neutral=self.N_NEUTRAL,
            n_positive=n_positive,
            workspace_id=workspace_3_id,
        )
        await self.create_query_and_feedback(
            asession=asession,
            created_datetime=dt_two_years,
            n_negative=n_negative_two_years,
            n_neutral=self.N_NEUTRAL,
            n_positive=n_positive_two_years,
            workspace_id=workspace_3_id,
        )

        yield

        await self.clean_up_urgency_data(asession=asession)
        await self.clean_up_query_data(asession=asession)

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

        for i in range(urgent * 2):
            urgency_db = UrgencyQueryDB(
                feedback_secret_key="abc123",
                message_datetime_utc=created_datetime,
                message_text="test message",
                workspace_id=workspace_id,
            )
            asession.add(urgency_db)
            await asession.commit()
            urgency_response = UrgencyResponseDB(
                details={"details": "test details"},
                is_urgent=(i % 2 == 0),
                query_id=urgency_db.urgency_query_id,
                response_datetime_utc=created_datetime,
                workspace_id=workspace_id,
            )
            asession.add(urgency_response)
            await asession.commit()

    @staticmethod
    async def clean_up_urgency_data(*, asession: AsyncSession) -> None:
        """Clean up urgency data from the database.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        """

        delete_urgency_response = delete(UrgencyResponseDB).where(
            UrgencyResponseDB.urgency_response_id > 0
        )
        await asession.execute(delete_urgency_response)
        delete_urgency_query = delete(UrgencyQueryDB).where(
            UrgencyQueryDB.urgency_query_id > 0
        )
        await asession.execute(delete_urgency_query)
        await asession.commit()

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

        for i in range(n_positive + n_negative + n_neutral):
            query = QueryDB(
                feedback_secret_key="abc123",
                query_datetime_utc=created_datetime,
                query_generate_llm_response=False,
                query_metadata={"details": "test details"},
                query_text="test message",
                workspace_id=workspace_id,
            )
            asession.add(query)
            await asession.commit()

            if i >= (n_positive + n_negative):
                sentiment = "neutral"
            else:
                sentiment = "positive" if i < n_positive else "negative"

            feedback = ResponseFeedbackDB(
                feedback_datetime_utc=created_datetime,
                feedback_sentiment=sentiment,
                query_id=query.query_id,
                session_id=query.session_id,
                workspace_id=workspace_id,
            )
            asession.add(feedback)
            await asession.commit()

    @staticmethod
    async def clean_up_query_data(*, asession: AsyncSession) -> None:
        """Clean up query data from the database.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        """

        delete_response_feedback = delete(ResponseFeedbackDB).where(
            ResponseFeedbackDB.query_id > 0
        )
        await asession.execute(delete_response_feedback)
        delete_query = delete(QueryDB).where(QueryDB.query_id > 0)
        await asession.execute(delete_query)
        await asession.commit()

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
        asession: AsyncSession,
        workspace_3_id: int,
    ) -> None:
        """Test the time series endpoint.

        Parameters
        ----------
        create_data
            The data to create for the given time series.
        period
            The period to test the time series for.
        asession
            The SQLAlchemy async session to use for all database connections.
        workspace_3_id
            The ID of workspace 3.
        """

        today = datetime.now(timezone.utc)
        previous_date, frequency = get_previous_date_and_frequency(period=period)
        n_escalated = self.data_to_create[period]["negative"]
        n_not_escalated = self.data_to_create[period]["positive"] + self.N_NEUTRAL

        query_ts = await get_timeseries_query(
            asession=asession,
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
        asession: AsyncSession,
        workspace_3_id: int,
    ) -> None:
        """Test the time series urgency endpoint.

        Parameters
        ----------
        create_data
            The data to create for the given time series.
        period
            The period to test the time series for.
        asession
            The SQLAlchemy async session to use for all database connections.
        workspace_3_id
            The ID of workspace 3.
        """

        today = datetime.now(timezone.utc)
        previous_date, frequency = get_previous_date_and_frequency(period=period)

        n_urgent = self.data_to_create[period]["urgent"]
        urgency_ts = await get_timeseries_urgency(
            asession=asession,
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
        asession: AsyncSession,
        workspace_3_id: int,
    ) -> None:
        """Test the full overview timeseries format.

        Parameters
        ----------
        create_data
            The data to create for the given time series.
        period
            The period to test the time series for.
        asession
            The SQLAlchemy async session to use for all database connections.
        workspace_3_id
            The ID of workspace 3.
        """

        today = datetime.now(timezone.utc)
        previous_date, frequency = get_previous_date_and_frequency(period=period)

        overview_ts = await get_overview_timeseries(
            asession=asession,
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
        self, asession: AsyncSession, workspace_3_id: int
    ) -> AsyncGenerator[None, None]:
        """Add `N_DATAPOINTS` of data for each day in the past year.

        Parameters
        ----------
        asession
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
            asession.add(content_db)

        await asession.commit()

        yield

        delete_content = delete(ContentDB).where(ContentDB.content_id > 0)
        await asession.execute(delete_content)
        await asession.commit()

    async def test_top_content(
        self,
        asession: AsyncSession,
        content_data: pytest.FixtureRequest,
        workspace_3_id: int,
    ) -> None:
        """Test the top content endpoint.

        NB: The archive feature will prepend the string "[DELETED] " to the content
        card title if the content card has been archived.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        content_data
            The pytest fixture request object.
        workspace_3_id
            The ID of workspace 3.
        """

        top_n = 4
        top_content = await get_top_content(
            asession=asession, top_n=top_n, workspace_id=workspace_3_id
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
        asession: AsyncSession,
        content_data: pytest.FixtureRequest,
        workspace_2_id: int,
    ) -> None:
        """Test that content from other users is not returned.

        Parameters
        ----------
        asession
            The SQLAlchemy async session to use for all database connections.
        content_data
            The pytest fixture request object.
        workspace_2_id
            The ID of workspace 2.
        """

        top_content = await get_top_content(
            asession=asession, top_n=5, workspace_id=workspace_2_id
        )

        assert len(top_content) == 0
