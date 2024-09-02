"""This module contains functionalities for managing the dashboard statistics."""

from datetime import date, datetime, timezone
from typing import Any, Sequence, cast, get_args

from sqlalchemy import Row, case, desc, func, literal_column, select, text, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import and_
from sqlalchemy.sql.expression import Subquery

from ..contents.models import ContentDB
from ..llm_call.dashboard import generate_ai_summary
from ..question_answer.models import (
    ContentFeedbackDB,
    QueryDB,
    QueryResponseContentDB,
    ResponseFeedbackDB,
)
from ..urgency_detection.models import UrgencyResponseDB
from .config import GENERATE_AI_ANSWER
from .schemas import (
    ContentFeedbackStats,
    Day,
    DetailsDrawer,
    Heatmap,
    OverviewTimeSeries,
    QueryStats,
    ResponseFeedbackStats,
    StatsCards,
    TimeFrequency,
    TimeHours,
    TopContent,
    TopContentTimeSeries,
    UrgencyStats,
    UserFeedback,
    UserQuery,
)

N_SAMPLES_TOPIC_MODELING = 2000


async def get_stats_cards(
    *, user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> StatsCards:
    """Retrieve statistics for question answering and upvotes.

    Parameters
    ----------
    user_id
        The ID of the user to retrieve the statistics for.
    asession
        `AsyncSession` object for database transactions.
    start_date
        The starting date for the statistics.
    end_date
        The ending date for the statistics.

    Returns
    -------
    StatsCards
        The statistics for question answering and upvotes.
    """

    query_stats = await get_query_count_stats(user_id, asession, start_date, end_date)
    response_feedback_stats = await get_response_feedback_stats(
        user_id, asession, start_date, end_date
    )
    content_feedback_stats = await get_content_feedback_stats(
        user_id, asession, start_date, end_date
    )
    urgency_stats = await get_urgency_stats(user_id, asession, start_date, end_date)

    return StatsCards(
        query_stats=query_stats,
        response_feedback_stats=response_feedback_stats,
        content_feedback_stats=content_feedback_stats,
        urgency_stats=urgency_stats,
    )


async def get_heatmap(
    user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> Heatmap:
    """Retrieve queries per two hour blocks each weekday between start and end date.

    Parameters
    ----------
    user_id
        The ID of the user to retrieve the heatmap for.
    asession
        `AsyncSession` object for database transactions.
    start_date
        The starting date for the heatmap.
    end_date
        The ending date for the heatmap.

    Returns
    -------
    Heatmap
        The heatmap of queries per two hour blocks.
    """

    statement = (
        select(
            func.to_char(QueryDB.query_datetime_utc, "Dy").label("day_of_week"),
            func.to_char(QueryDB.query_datetime_utc, "HH24").label("hour_of_day"),
            func.count(QueryDB.query_id).label("n_questions"),
        )
        .where(
            (QueryDB.user_id == user_id)
            & (QueryDB.query_datetime_utc >= start_date)
            & (QueryDB.query_datetime_utc < end_date)
        )
        .group_by("day_of_week", "hour_of_day")
    )

    result = await asession.execute(statement)
    rows = result.fetchall()  # (day of week, hour of day, n_questions)

    heatmap = initialize_heatmap()
    for row in rows:
        day_of_week = row.day_of_week
        hour_of_day = int(row.hour_of_day)
        n_questions = row.n_questions
        if int(hour_of_day) % 2 == 1:
            hour_grp = hour_of_day - 1
        else:
            hour_grp = hour_of_day
        hour_grp_str = cast(TimeHours, f"{hour_grp:02}:00")
        heatmap[hour_grp_str][day_of_week] += n_questions

    return Heatmap.model_validate(heatmap)


async def get_overview_timeseries(
    user_id: int,
    asession: AsyncSession,
    start_date: date,
    end_date: date,
    frequency: TimeFrequency,
) -> OverviewTimeSeries:
    """Retrieve count of queries over time for the user.

    Parameters
    ----------
    user_id
        The ID of the user to retrieve the queries count timeseries for.
    asession
        `AsyncSession` object for database transactions.
    start_date
        The starting date for the queries count timeseries.
    end_date
        The ending date for the queries count timeseries.
    frequency
        The frequency at which to retrieve the queries count timeseries.

    Returns
    -------
    OverviewTimeSeries
        The queries count timeseries.
    """

    query_ts = await get_timeseries_query(
        user_id, asession, start_date, end_date, frequency
    )
    urgency_ts = await get_timeseries_urgency(
        user_id, asession, start_date, end_date, frequency
    )

    return OverviewTimeSeries(
        urgent=urgency_ts,
        not_urgent_escalated=query_ts["escalated"],
        not_urgent_not_escalated=query_ts["not_escalated"],
    )


async def get_top_content(
    *, user_id: int, asession: AsyncSession, top_n: int
) -> list[TopContent]:
    """Retrieve most frequently shared content.

    Parameters
    ----------
    user_id
        The ID of the user to retrieve the top content for.
    asession
        `AsyncSession` object for database transactions.
    top_n
        The number of top content to retrieve.

    Returns
    -------
    list[TopContent]
        List of most frequently shared content.
    """

    statement = (
        select(
            ContentDB.content_title,
            ContentDB.query_count,
            ContentDB.positive_votes,
            ContentDB.negative_votes,
            ContentDB.updated_datetime_utc,
            ContentDB.is_archived,
        )
        .order_by(ContentDB.query_count.desc())
        .where(ContentDB.user_id == user_id)
    )
    statement = statement.limit(top_n)

    result = await asession.execute(statement)
    rows = result.fetchall()
    return [
        TopContent(
            title="[DELETED] " + r.content_title if r.is_archived else r.content_title,
            query_count=r.query_count,
            positive_votes=r.positive_votes,
            negative_votes=r.negative_votes,
            last_updated=r.updated_datetime_utc,
        )
        for r in rows
    ]


def get_time_labels_query(
    frequency: TimeFrequency, start_date: date, end_date: date
) -> tuple[str, Subquery]:
    """Get time labels for the query time series query.

    Parameters
    ----------
    frequency
        The frequency at which to retrieve the time labels.
    start_date
        The starting date for the time labels.
    end_date
        The ending date for the time labels.

    Returns
    -------
    tuple[str, Subquery]
        The interval string and the time label retrieval query.

    Raises
    ------
    ValueError
        If the frequency is invalid.
    """

    match frequency:
        case TimeFrequency.Day:
            interval_str = "day"
        case TimeFrequency.Week:
            interval_str = "week"
        case TimeFrequency.Hour:
            interval_str = "hour"
        case _:
            raise ValueError("Invalid frequency")

    extra_interval = "hour" if interval_str == "hour" else "day"
    return interval_str, (
        select(
            func.date_trunc(interval_str, literal_column("period_start")).label(
                "time_period"
            )
        )
        .select_from(
            text(
                f"generate_series('{start_date}'::timestamp, '{end_date}'::timestamp + "
                f"'1 {extra_interval}'::interval, '1 {interval_str}'"
                "::interval) AS period_start"
            )
        )
        .alias("ts_labels")
    )


async def get_timeseries_query(
    user_id: int,
    asession: AsyncSession,
    start_date: date,
    end_date: date,
    frequency: TimeFrequency,
) -> dict[str, dict[str, int]]:
    """Retrieve the timeseries corresponding to escalated and not escalated queries
    over the specified time period.

    NB: The SQLAlchemy statement below selects time periods from `ts_labels` and counts
    the number of negative and non-negative feedback entries from `ResponseFeedbackDB`
    for each time period, after filtering for a specific user. It groups and orders the
    results by time period. The outer join with `ResponseFeedbackDB` is based on the
    truncation of dates to the specified interval (`interval_str`). This joins
    `ResponseFeedbackDB` to `ts_labels` on matching truncated dates.

    Parameters
    ----------
    user_id
        The ID of the user to retrieve the queries count timeseries query for.
    asession
        `AsyncSession` object for database transactions.
    start_date
        The starting date for the queries count timeseries query.
    end_date
        The ending date for the queries count timeseries query.
    frequency
        The frequency at which to retrieve the queries count timeseries.

    Returns
    -------
    dict[str, dict[str, int]]
        Dictionary whose keys are "escalated" and "not_escalated" and whose values are
        dictionaries containing the count of queries over time for each category.
    """

    interval_str, ts_labels = get_time_labels_query(frequency, start_date, end_date)

    statement = (
        select(
            ts_labels.c.time_period,
            func.coalesce(
                func.count(
                    case(
                        (ResponseFeedbackDB.feedback_sentiment == "negative", 1),
                        else_=None,
                    )
                ),
                0,
            ).label("negative_feedback_count"),
            func.coalesce(
                func.count(
                    case(
                        (ResponseFeedbackDB.feedback_sentiment != "negative", 1),
                        else_=None,
                    )
                ),
                0,
            ).label("non_negative_feedback_count"),
        )
        .select_from(ts_labels)
        .outerjoin(
            ResponseFeedbackDB,
            func.date_trunc(interval_str, ResponseFeedbackDB.feedback_datetime_utc)
            == func.date_trunc(interval_str, ts_labels.c.time_period),
        )
        .where(ResponseFeedbackDB.query.has(user_id=user_id))
        .group_by(ts_labels.c.time_period)
        .order_by(ts_labels.c.time_period)
    )

    result = await asession.execute(statement)
    rows = result.fetchall()
    escalated = dict()
    not_escalated = dict()
    format_str = "%Y-%m-%dT%H:%M:%S.000000Z"  # ISO 8601 format (required by frontend)
    for row in rows:
        escalated[row.time_period.strftime(format_str)] = row.negative_feedback_count
        not_escalated[row.time_period.strftime(format_str)] = (
            row.non_negative_feedback_count
        )

    return dict(escalated=escalated, not_escalated=not_escalated)


async def get_timeseries_urgency(
    user_id: int,
    asession: AsyncSession,
    start_date: date,
    end_date: date,
    frequency: TimeFrequency,
) -> dict[str, int]:
    """Retrieve the timeseries corresponding to the count of urgent queries over time
    for the specified user.

    NB: The SQLAlchemy statement below retrieves the count of urgent responses
    (`n_urgent`) for each time_period from the `ts_labels` table, where the responses
    are matched based on truncated dates, filtered by a specific user ID, and ordered
    by the specified time period. The outer join with `UrgencyResponseDB` table is
    based on matching truncated dates. The truncation is done using `func.date_trunc`
    with `interval_str` (e.g., 'month', 'year', etc.), ensuring that dates are compared
    at the same granularity.

    Parameters
    ----------
    user_id
        The ID of the user to retrieve the timeseries corresponding to the count of
        urgent queries over time for.
    asession
        `AsyncSession` object for database transactions.
    start_date
        The starting date for the count of urgent queries.
    end_date
        The ending date for the count of urgent queries.
    frequency
        The frequency at which to retrieve the count of urgent queries.

    Returns
    -------
    dict[str, int]
        Dictionary containing the count of urgent queries over time.
    """

    interval_str, ts_labels = get_time_labels_query(frequency, start_date, end_date)

    statement = (
        select(
            ts_labels.c.time_period,
            func.coalesce(
                func.count(
                    case(
                        (UrgencyResponseDB.is_urgent == true(), 1),
                        else_=None,
                    )
                ),
                0,
            ).label("n_urgent"),
        )
        .select_from(ts_labels)
        .outerjoin(
            UrgencyResponseDB,
            func.date_trunc(interval_str, UrgencyResponseDB.response_datetime_utc)
            == func.date_trunc(interval_str, ts_labels.c.time_period),
        )
        .where(ResponseFeedbackDB.query.has(user_id=user_id))
        .group_by(ts_labels.c.time_period)
        .order_by(ts_labels.c.time_period)
    )

    await asession.execute(statement)
    result = await asession.execute(statement)
    rows = result.fetchall()

    format_str = "%Y-%m-%dT%H:%M:%S.000000Z"  # ISO 8601 format (required by frontend)
    return {row.time_period.strftime(format_str): row.n_urgent for row in rows}


async def get_timeseries_top_content(
    user_id: int,
    asession: AsyncSession,
    top_n: int | None,
    start_date: date,
    end_date: date,
    frequency: TimeFrequency,
) -> list[TopContentTimeSeries]:
    """
    Retrieve most frequently shared content and feedback between the start and end date.
    Note that this retrieves top N content from the `QueryResponseContentDB` table
    and not from the `ContentDB` table.ContentDB

    Returns
    """

    interval_str, ts_labels = get_time_labels_query(frequency, start_date, end_date)

    top_content_base = (
        select(
            ContentDB.content_id,
            ContentDB.content_title,
            ContentDB.updated_datetime_utc,
            func.count(QueryResponseContentDB.query_id).label("total_query_count"),
        )
        .select_from(QueryResponseContentDB)
        .join(
            ContentDB,
            QueryResponseContentDB.content_id == ContentDB.content_id,
        )
        .where(
            ContentDB.user_id == user_id,
            QueryResponseContentDB.created_datetime_utc >= start_date,
            QueryResponseContentDB.created_datetime_utc < end_date,
        )
        .group_by(
            ContentDB.content_title,
            ContentDB.content_id,
        )
        .order_by(desc("total_query_count"))
    )

    if top_n:
        top_content_base = top_content_base.limit(top_n)

    top_content = top_content_base.subquery("top_content")

    content_w_feedback = (
        select(
            ContentFeedbackDB.content_id,
            func.count(
                case((ContentFeedbackDB.feedback_sentiment == "positive", 1))
            ).label("n_positive_feedback"),
            func.count(
                case((ContentFeedbackDB.feedback_sentiment == "negative", 1))
            ).label("n_negative_feedback"),
        )
        .where(
            ContentFeedbackDB.user_id == user_id,
            ContentFeedbackDB.feedback_datetime_utc >= start_date,
            ContentFeedbackDB.feedback_datetime_utc < end_date,
        )
        .group_by(ContentFeedbackDB.content_id)
        .subquery("content_w_feedback")
    )

    top_content_w_feedback = (
        select(
            top_content.c.content_id,
            top_content.c.content_title,
            top_content.c.total_query_count,
            top_content.c.updated_datetime_utc,
            func.coalesce(content_w_feedback.c.n_positive_feedback, 0).label(
                "n_positive_feedback"
            ),
            func.coalesce(content_w_feedback.c.n_negative_feedback, 0).label(
                "n_negative_feedback"
            ),
        )
        .select_from(top_content)
        .join(
            content_w_feedback,
            top_content.c.content_id == content_w_feedback.c.content_id,
            isouter=True,
        )
        .subquery("top_content_w_feedback")
    )

    all_combinations_w_feedback = (
        select(
            ts_labels.c.time_period,
            top_content_w_feedback.c.content_id,
            top_content_w_feedback.c.content_title,
            top_content_w_feedback.c.total_query_count,
            top_content_w_feedback.c.updated_datetime_utc,
            top_content_w_feedback.c.n_positive_feedback,
            top_content_w_feedback.c.n_negative_feedback,
        )
        .select_from(ts_labels)
        .join(top_content_w_feedback, text("1=1"))
        .subquery("all_combinations_w_feedback")
    )

    # Main query to get the required data
    statement = (
        select(
            all_combinations_w_feedback.c.time_period,
            all_combinations_w_feedback.c.content_id,
            all_combinations_w_feedback.c.content_title,
            all_combinations_w_feedback.c.total_query_count,
            func.coalesce(func.count(QueryResponseContentDB.query_id), 0).label(
                "query_count"
            ),
            all_combinations_w_feedback.c.n_positive_feedback,
            all_combinations_w_feedback.c.n_negative_feedback,
        )
        .select_from(all_combinations_w_feedback)
        .join(
            QueryResponseContentDB,
            and_(
                all_combinations_w_feedback.c.content_id
                == QueryResponseContentDB.content_id,
                func.date_trunc(
                    interval_str, QueryResponseContentDB.created_datetime_utc
                )
                == func.date_trunc(
                    interval_str, all_combinations_w_feedback.c.time_period
                ),
            ),
            isouter=True,
        )
        .group_by(
            all_combinations_w_feedback.c.time_period,
            all_combinations_w_feedback.c.content_id,
            all_combinations_w_feedback.c.content_title,
            all_combinations_w_feedback.c.total_query_count,
            all_combinations_w_feedback.c.n_positive_feedback,
            all_combinations_w_feedback.c.n_negative_feedback,
        )
        .order_by(
            desc("total_query_count"),
            all_combinations_w_feedback.c.content_id,
            all_combinations_w_feedback.c.time_period,
        )
    )

    result = await asession.execute(statement)
    rows = result.fetchall()
    format_str = "%Y-%m-%dT%H:%M:%S.000000Z"  # ISO 8601 format (required by frontend)

    return convert_rows_to_top_content_time_series(rows, format_str)


def set_curr_content_values(r: Row[Any]) -> dict[str, Any]:
    """
    Set current content values
    """
    return {
        "id": r.content_id,
        "title": r.content_title,
        "total_query_count": r.total_query_count,
        "positive_votes": r.n_positive_feedback,
        "negative_votes": r.n_negative_feedback,
    }


def convert_rows_to_top_content_time_series(
    rows: Sequence[Row[Any]], format_str: str
) -> list[TopContentTimeSeries]:
    """
    Convert rows to list of TopContentTimeSeries
    """
    curr_content_id = None
    curr_content_values = {}
    time_series = dict()
    top_content_time_series: list[TopContentTimeSeries] = []
    for r in rows:
        if curr_content_id is None:
            curr_content_values = set_curr_content_values(r)
            curr_content_id = r.content_id
            time_series = {r.time_period.strftime(format_str): r.query_count}
        elif curr_content_id == r.content_id:
            time_series[r.time_period.strftime(format_str)] = r.query_count
        else:
            top_content_time_series.append(
                TopContentTimeSeries(
                    **curr_content_values,
                    query_count_time_series=time_series,
                )
            )
            curr_content_values = set_curr_content_values(r)
            time_series = {r.time_period.strftime(format_str): r.query_count}
            curr_content_id = r.content_id
    if curr_content_id is not None:
        top_content_time_series.append(
            TopContentTimeSeries(
                **curr_content_values,
                query_count_time_series=time_series,
            )
        )

    return top_content_time_series


async def get_content_details(
    user_id: int,
    content_id: int,
    asession: AsyncSession,
    start_date: date,
    end_date: date,
    frequency: TimeFrequency,
    max_feedback_records: int,
) -> DetailsDrawer:
    """
    Retrieve detailed statistics of a content.

    SQL to run within start_date and end_date and for user_id:
    1. Get ts_labels
    2. Get title, query_count_timeseries from QueryResponseContentDB
    2. Get positive_count_timeseries, negative_count_timeseries from ContentFeedbackDB
    3. Get user feedback (timestamp, question, feedback) from ContentFeedbackDB
    """
    day_between = (end_date - start_date).days
    day_between = day_between if day_between > 0 else 1

    interval_str, ts_labels = get_time_labels_query(frequency, start_date, end_date)
    query_count_ts = (
        select(
            func.date_trunc(interval_str, ts_labels.c.time_period).label("time_period"),
            func.coalesce(func.count(QueryResponseContentDB.query_id), 0).label(
                "query_count"
            ),
            ContentDB.content_title,
        )
        .select_from(ts_labels)
        .join(
            QueryResponseContentDB,
            and_(
                func.date_trunc(
                    interval_str, QueryResponseContentDB.created_datetime_utc
                )
                == func.date_trunc(interval_str, ts_labels.c.time_period),
                QueryResponseContentDB.content_id == content_id,
                QueryResponseContentDB.user_id == user_id,
            ),
            isouter=True,
        )
        .join(
            ContentDB,
            ContentDB.content_id == content_id,
            isouter=True,
        )
        .group_by(ts_labels.c.time_period, ContentDB.content_title)
        .subquery("query_count_ts")
    )

    feedback_ts = (
        select(
            query_count_ts.c.time_period,
            query_count_ts.c.query_count,
            query_count_ts.c.content_title,
            func.coalesce(
                func.count(
                    case((ContentFeedbackDB.feedback_sentiment == "positive", 1))
                ),
                0,
            ).label("positive_count"),
            func.coalesce(
                func.count(
                    case((ContentFeedbackDB.feedback_sentiment == "negative", 1))
                ),
                0,
            ).label("negative_count"),
        )
        .select_from(query_count_ts)
        .join(
            ContentFeedbackDB,
            and_(
                func.date_trunc(interval_str, ContentFeedbackDB.feedback_datetime_utc)
                == query_count_ts.c.time_period,
                ContentFeedbackDB.content_id == content_id,
                ContentFeedbackDB.user_id == user_id,
            ),
            isouter=True,
        )
        .group_by(
            query_count_ts.c.time_period,
            query_count_ts.c.content_title,
            query_count_ts.c.query_count,
        )
        .order_by(query_count_ts.c.time_period)
    )

    user_feedback = (
        select(
            ContentFeedbackDB.feedback_datetime_utc,
            QueryDB.query_text,
            ContentFeedbackDB.feedback_text,
        )
        .join(QueryDB)
        .where(
            ContentFeedbackDB.content_id == content_id,
            ContentFeedbackDB.user_id == user_id,
            ContentFeedbackDB.feedback_datetime_utc >= start_date,
            ContentFeedbackDB.feedback_datetime_utc < end_date,
            ContentFeedbackDB.feedback_text.is_not(None),
            ContentFeedbackDB.feedback_text != "",
        )
        .order_by(ContentFeedbackDB.feedback_datetime_utc.desc())
        .limit(max_feedback_records)
    )

    result_ts = await asession.execute(feedback_ts)
    result_feedback = await asession.execute(user_feedback)

    rows_ts = result_ts.fetchall()
    rows_feedback = result_feedback.fetchall()

    format_str = "%Y-%m-%dT%H:%M:%S.000000Z"  # ISO 8601 format (required by frontend)

    return convert_rows_to_details_drawer(
        timeseries=rows_ts,
        feedback=rows_feedback,
        format_str=format_str,
        n_days=day_between,
    )


async def get_ai_answer_summary(
    content_id: int,
    user_id: int,
    start_date: date,
    end_date: date,
    max_feedback_records: int,
    asession: AsyncSession,
) -> str:
    """
    Get AI answer summary
    """

    if not GENERATE_AI_ANSWER:
        return "Not Available"

    user_feedback = (
        select(
            ContentFeedbackDB.feedback_text,
        )
        .join(QueryDB)
        .where(
            ContentFeedbackDB.content_id == content_id,
            ContentFeedbackDB.user_id == user_id,
            ContentFeedbackDB.feedback_datetime_utc >= start_date,
            ContentFeedbackDB.feedback_datetime_utc < end_date,
            ContentFeedbackDB.feedback_text.is_not(None),
            ContentFeedbackDB.feedback_text != "",
        )
        .order_by(ContentFeedbackDB.feedback_datetime_utc.desc())
        .limit(max_feedback_records)
    )

    content = select(ContentDB.content_title, ContentDB.content_text).where(
        ContentDB.content_id == content_id, ContentDB.user_id == user_id
    )
    result_feedback = await asession.execute(user_feedback)
    rows_feedback = result_feedback.fetchall()
    all_feedback = [r.feedback_text for r in rows_feedback]

    content_result = await asession.execute(content)
    content_row = content_result.fetchone()

    if not content_row:
        raise ValueError(f"Content with id {content_id} for user {user_id} not found")

    if all_feedback:
        ai_summary = await generate_ai_summary(
            user_id=user_id,
            content_title=content_row.content_title,
            content_text=content_row.content_text,
            feedback=all_feedback,
        )
    else:
        ai_summary = "No feedback to summarize."

    return ai_summary


def convert_rows_to_details_drawer(
    timeseries: Sequence[Row[Any]],
    feedback: Sequence[Row[Any]],
    format_str: str,
    n_days: int,
) -> DetailsDrawer:
    """
    Convert rows to DetailsDrawer
    """
    time_series = {}
    query_count = 0
    positive_count = 0
    negative_count = 0
    title = ""

    if timeseries:
        title = timeseries[0].content_title

    for r in timeseries:
        time_series[r.time_period.strftime(format_str)] = {
            "query_count": r.query_count,
            "positive_count": r.positive_count,
            "negative_count": r.negative_count,
        }
        query_count += r.query_count
        positive_count += r.positive_count
        negative_count += r.negative_count

    feedback_rows = []
    for r in feedback:
        feedback_rows.append(
            UserFeedback(
                timestamp=r.feedback_datetime_utc.strftime(format_str),
                question=r.query_text,
                feedback=r.feedback_text,
            )
        )

    return DetailsDrawer(
        title=title,
        query_count=query_count,
        positive_votes=positive_count,
        negative_votes=negative_count,
        daily_query_count_avg=query_count // n_days,
        time_series=time_series,
        user_feedback=feedback_rows,
    )


def initialize_heatmap() -> dict[TimeHours, dict[Day, int]]:
    """Initialize the heatmap dictionary.

    Returns
    -------
    dict[TimeHours, dict[Day, int]]
        The initialized heatmap dictionary
    """

    return {h: {d: 0 for d in get_args(Day)} for h in get_args(TimeHours)}


async def get_query_count_stats(
    user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> QueryStats:
    """Retrieve statistics for question answering for the specified period. The current
    period is defined by `start_date` and `end_date`. The previous period is defined as
    the same window in time before the current period. The statistics include:

    1. The total number of questions asked in the current period.
    2. The percentage increase in the number of questions asked in the current period
        from the previous period.

    Parameters
    ----------
    user_id
        The ID of the user to retrieve the statistics for.
    asession
        `AsyncSession` object for database transactions.
    start_date
        The starting date for the statistics.
    end_date
        The ending date for the statistics.

    Returns
    -------
    QueryStats
        The statistics for question answering.
    """

    # Total questions asked in this period
    statement_combined = select(
        func.sum(
            case(
                (
                    (QueryDB.query_datetime_utc <= end_date)
                    & (QueryDB.query_datetime_utc > start_date),
                    1,
                ),
                else_=0,
            )
        ).label("current_period_count"),
        func.sum(
            case(
                (
                    (QueryDB.query_datetime_utc <= start_date)
                    & (
                        QueryDB.query_datetime_utc
                        > start_date - (end_date - start_date)
                    ),
                    1,
                ),
                else_=0,
            )
        ).label("previous_period_count"),
    ).where(QueryDB.user_id == user_id)

    # Execute the combined statement
    result = await asession.execute(statement_combined)
    counts = result.fetchone()

    n_questions_curr_period = (
        counts.current_period_count if counts and counts.current_period_count else 0
    )
    n_questions_prev_period = (
        counts.previous_period_count if counts and counts.previous_period_count else 0
    )

    # Percentage increase in questions asked
    percent_increase = get_percentage_increase(
        n_questions_curr_period, n_questions_prev_period
    )

    return QueryStats(
        n_questions=n_questions_curr_period, percentage_increase=percent_increase
    )


async def get_response_feedback_stats(
    user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> ResponseFeedbackStats:
    """Retrieve statistics for response feedback grouped by sentiment. The current
    period is defined by `start_date` and `end_date`. The previous period is defined as
    the same window in time before the current period. The statistics include:

    1. The total number of positive and negative feedback received in the current
        period.
    2. The percentage increase in the number of positive and negative feedback received
        in the current period from the previous period.

    Parameters
    ----------
    user_id
        The ID of the user to retrieve response feedback statistics for.
    asession
        `AsyncSession` object for database transactions.
    start_date
        The starting date to retrieve response feedback statistics.
    end_date
        The ending date to retrieve response feedback statistics.

    Returns
    -------
    ResponseFeedbackStats
        The statistics for response feedback.
    """

    statement_combined = (
        select(
            ResponseFeedbackDB.feedback_sentiment,
            func.sum(
                case(
                    (
                        (ResponseFeedbackDB.feedback_datetime_utc <= end_date)
                        & (ResponseFeedbackDB.feedback_datetime_utc > start_date),
                        1,
                    ),
                    else_=0,
                )
            ).label("current_period_count"),
            func.sum(
                case(
                    (
                        (ResponseFeedbackDB.feedback_datetime_utc <= start_date)
                        & (
                            ResponseFeedbackDB.feedback_datetime_utc
                            > start_date - (end_date - start_date)
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("previous_period_count"),
        )
        .join(ResponseFeedbackDB.query)
        .where(ResponseFeedbackDB.query.has(user_id=user_id))
        .group_by(ResponseFeedbackDB.feedback_sentiment)
    )

    # Execute the combined statement
    result = await asession.execute(statement_combined)
    feedback_counts = result.fetchall()

    feedback_curr_period_dict = {
        row[0]: row[1] for row in feedback_counts if row[1] is not None
    }
    feedback_prev_period_dict = {
        row[0]: row[2] for row in feedback_counts if row[2] is not None
    }

    feedback_stats = get_feedback_stats(
        feedback_curr_period_dict, feedback_prev_period_dict
    )

    return ResponseFeedbackStats.model_validate(feedback_stats)


async def get_content_feedback_stats(
    user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> ContentFeedbackStats:
    """Retrieve statistics for content feedback. The current period is defined by
    `start_date` and `end_date`. The previous period is defined as the same window in
    time before the current period. The statistics include:

    1. The total number of positive and negative feedback received in the current
        period.
    2. The percentage increase in the number of positive and negative feedback received
        in the current period from the previous period.

    Parameters
    ----------
    user_id
        The ID of the user to retrieve content feedback statistics for.
    asession
        `AsyncSession` object for database transactions.
    start_date
        The start date to retrieve content feedback statistics.
    end_date
        The end date to retrieve content feedback statistics

    Returns
    -------
    ContentFeedbackStats
        The statistics for content feedback.
    """

    statement_combined = (
        select(
            ContentFeedbackDB.feedback_sentiment,
            func.sum(
                case(
                    (
                        (ContentFeedbackDB.feedback_datetime_utc <= end_date)
                        & (ContentFeedbackDB.feedback_datetime_utc > start_date),
                        1,
                    ),
                    else_=0,
                )
            ).label("current_period_count"),
            func.sum(
                case(
                    (
                        (ContentFeedbackDB.feedback_datetime_utc <= start_date)
                        & (
                            ContentFeedbackDB.feedback_datetime_utc
                            > start_date - (end_date - start_date)
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("previous_period_count"),
        )
        .join(ContentFeedbackDB.content)
        .where(ContentFeedbackDB.content.has(user_id=user_id))
        .group_by(ContentFeedbackDB.feedback_sentiment)
    )

    result = await asession.execute(statement_combined)
    feedback_counts = result.fetchall()

    feedback_curr_period_dict = {
        row[0]: row[1] for row in feedback_counts if row[1] is not None
    }
    feedback_prev_period_dict = {
        row[0]: row[2] for row in feedback_counts if row[2] is not None
    }
    feedback_stats = get_feedback_stats(
        feedback_curr_period_dict, feedback_prev_period_dict
    )

    return ContentFeedbackStats.model_validate(feedback_stats)


def get_feedback_stats(
    feedback_curr_period_dict: dict[str, int], feedback_prev_period_dict: dict[str, int]
) -> dict[str, int | float]:
    """Get feedback statistics.

    Parameters
    ----------
    feedback_curr_period_dict
        The dictionary containing feedback statistics for the current period.
    feedback_prev_period_dict
        The dictionary containing feedback statistics for the previous period.

    Returns
    -------
    dict[str, int | float]
        The feedback statistics.
    """

    n_positive_curr = feedback_curr_period_dict.get("positive", 0)
    n_negative_curr = feedback_curr_period_dict.get("negative", 0)
    n_positive_prev = feedback_prev_period_dict.get("positive", 0)
    n_negative_prev = feedback_prev_period_dict.get("negative", 0)

    percentage_positive_increase = get_percentage_increase(
        n_positive_curr, n_positive_prev
    )
    percentage_negative_increase = get_percentage_increase(
        n_negative_curr, n_negative_prev
    )

    return {
        "n_positive": n_positive_curr,
        "n_negative": n_negative_curr,
        "percentage_positive_increase": percentage_positive_increase,
        "percentage_negative_increase": percentage_negative_increase,
    }


async def get_urgency_stats(
    user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> UrgencyStats:
    """Retrieve statistics for urgency. The current period is defined by `start_date`
    and `end_date`. The previous period is defined as the same window in time before
    the current period. The statistics include:

    1. The total number of urgent queries in the current period.
    2. The percentage increase in the number of urgent queries in the current period
        from the previous period.

    Parameters
    ----------
    user_id
        The ID of the user to retrieve urgency statistics for.
    asession
        `AsyncSession` object for database transactions.
    start_date
        The starting date for the urgency statistics.
    end_date
        The ending date for the urgency statistics.

    Returns
    -------
    UrgencyStats
        The statistics for urgency.
    """

    statement_combined = (
        select(
            func.sum(
                case(
                    (
                        (UrgencyResponseDB.response_datetime_utc <= end_date)
                        & (UrgencyResponseDB.response_datetime_utc > start_date)
                        & (UrgencyResponseDB.is_urgent == true()),
                        1,
                    ),
                    else_=0,
                )
            ).label("current_period_count"),
            func.sum(
                case(
                    (
                        (UrgencyResponseDB.response_datetime_utc <= start_date)
                        & (
                            UrgencyResponseDB.response_datetime_utc
                            > start_date - (end_date - start_date)
                        )
                        & (UrgencyResponseDB.is_urgent == true()),
                        1,
                    ),
                    else_=0,
                )
            ).label("previous_period_count"),
        )
        .join(UrgencyResponseDB.query)
        .where(UrgencyResponseDB.query.has(user_id=user_id))
    )

    # Execute the combined statement
    result = await asession.execute(statement_combined)
    counts = result.fetchone()

    n_urgency_curr_period = (
        counts.current_period_count if counts and counts.current_period_count else 0
    )
    n_urgency_prev_period = (
        counts.previous_period_count if counts and counts.previous_period_count else 0
    )

    percentage_increase = get_percentage_increase(
        n_urgency_curr_period, n_urgency_prev_period
    )

    return UrgencyStats(
        n_urgent=n_urgency_curr_period, percentage_increase=percentage_increase
    )


def get_percentage_increase(n_curr: int, n_prev: int) -> float:
    """Calculate percentage increase.

    Parameters
    ----------
    n_curr
        The current count.
    n_prev
        The previous count.

    Returns
    -------
    float
        The percentage increase.
    """

    if n_prev == 0:
        return 0.0

    return (n_curr - n_prev) / n_prev


async def get_raw_queries(
    asession: AsyncSession,
    user_id: int,
    start_date: date,
) -> list[UserQuery]:
    """Retrieve 2000 randomly sampled raw queries (query_text) and their
    datetime stamps within the specified date range.
    Parameters
    ----------
    asession
        `AsyncSession` object for database transactions.
    user_id
        The ID of the user to retrieve the queries for.
    start_date
        The starting date for the queries.
    Returns
    -------
    list[UserQuery]
        A list of UserQuery objects
    """

    statement = (
        select(QueryDB.query_text, QueryDB.query_datetime_utc, QueryDB.query_id)
        .where(
            (QueryDB.user_id == user_id)
            & (QueryDB.query_datetime_utc >= start_date)
            & (QueryDB.query_datetime_utc < datetime.now(tz=timezone.utc))
        )
        .order_by(func.random())
        .limit(N_SAMPLES_TOPIC_MODELING)
    )

    result = await asession.execute(statement)
    rows = result.fetchall()
    if not rows:
        query_list = []
    else:
        query_list = [
            UserQuery(
                query_id=row.query_id,
                query_text=row.query_text,
                query_datetime_utc=row.query_datetime_utc,
            )
            for row in rows
        ]

    return query_list
