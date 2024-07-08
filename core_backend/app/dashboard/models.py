from datetime import date
from typing import Dict, List, Tuple, Union, get_args

from sqlalchemy import case, func, literal_column, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Subquery

from ..contents.models import ContentDB
from ..question_answer.models import (
    ContentFeedbackDB,
    QueryDB,
    ResponseFeedbackDB,
)
from ..urgency_detection.models import UrgencyResponseDB
from .schemas import (
    ContentFeedbackStats,
    Day,
    Heatmap,
    QueryStats,
    ResponseFeedbackStats,
    StatsCards,
    TimeFrequency,
    TimeHours,
    TimeSeries,
    TopContent,
    UrgencyStats,
)


async def get_stats_cards(
    user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> StatsCards:
    """
    Retrieve statistics for question answering and upvotes
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
    """
    Retrieve queries per two hour blocks each weekday between start and end date
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
    rows = result.fetchall()

    heatmap = initilize_heatmap()
    for row in rows:
        day_of_week = row.day_of_week
        hour_of_day = int(row.hour_of_day)
        n_questions = row.n_questions
        if int(hour_of_day) % 2 == 1:
            hour_grp = hour_of_day - 1
        else:
            hour_grp = hour_of_day
        hour_grp_str = f"{hour_grp:02}:00"
        heatmap[hour_grp_str][day_of_week] += n_questions  # type: ignore

    return Heatmap.model_validate(heatmap)


async def get_timeseries(
    user_id: int,
    asession: AsyncSession,
    start_date: date,
    end_date: date,
    frequency: TimeFrequency,
) -> TimeSeries:
    """
    Retrieve count of queries over time for the user
    """
    query_ts = await get_timeseries_query(
        user_id, asession, start_date, end_date, frequency
    )
    urgency_ts = await get_timeseries_urgency(
        user_id, asession, start_date, end_date, frequency
    )

    return TimeSeries(
        urgent=urgency_ts,
        not_urgent_escalated=query_ts["escalated"],
        not_urgent_not_escalated=query_ts["not_escalated"],
    )


async def get_top_content(
    user_id: int, asession: AsyncSession, top_n: int
) -> List[TopContent]:
    """
    Retrieve most frequently shared content
    """
    statement = (
        select(
            ContentDB.content_title,
            ContentDB.query_count,
            ContentDB.positive_votes,
            ContentDB.negative_votes,
            ContentDB.updated_datetime_utc,
        )
        .order_by(ContentDB.query_count.desc())
        .limit(top_n)
    )

    result = await asession.execute(statement)
    rows = result.fetchall()

    return [
        TopContent(
            title=r.content_title,
            query_count=r.query_count,
            positive_votes=r.positive_votes,
            negative_votes=r.negative_votes,
            last_updated=r.updated_datetime_utc,
        )
        for r in rows
    ]


def get_time_labels_query(
    frequency: TimeFrequency, start_date: date, end_date: date
) -> Tuple[str, Subquery]:
    """
    Get time labels for the query time series
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

    return interval_str, (
        select(
            func.date_trunc(interval_str, literal_column("period_start")).label(
                "time_period"
            )
        )
        .select_from(
            text(
                f"generate_series('{start_date}', '{end_date}', '1 {interval_str}'"
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
) -> Dict[str, Dict[str, int]]:
    """
    Retrieve count of queries over time for the user
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
        .group_by(ts_labels.c.time_period)
        .order_by(ts_labels.c.time_period)
    )

    result = await asession.execute(statement)
    rows = result.fetchall()
    escalated = dict()
    not_escalated = dict()
    format_str = "%m/%d/%Y %H:%M:%S" if frequency == TimeFrequency.Hour else "%m/%d/%Y"
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
) -> Dict[str, int]:
    """
    Retrieve count of urgent queries over time for the user
    """
    interval_str, ts_labels = get_time_labels_query(frequency, start_date, end_date)

    statement = (
        select(
            ts_labels.c.time_period,
            func.coalesce(
                func.count(
                    case(
                        (UrgencyResponseDB.is_urgent == True, 1),  # noqa
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
        .group_by(ts_labels.c.time_period)
        .order_by(ts_labels.c.time_period)
    )

    await asession.execute(statement)
    result = await asession.execute(statement)
    rows = result.fetchall()

    format_str = "%m/%d/%Y %H:%M:%S" if frequency == TimeFrequency.Hour else "%m/%d/%Y"

    return {row.time_period.strftime(format_str): row.n_urgent for row in rows}


def initilize_heatmap() -> Dict[TimeHours, Dict[Day, int]]:
    """
    Initialize heatmap dictionary
    """
    return {h: {d: 0 for d in get_args(Day)} for h in get_args(TimeHours)}


async def get_query_count_stats(
    user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> QueryStats:
    """
    Retrieve statistics for question answering
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
        n_questions=n_questions_curr_period,
        percentage_increase=percent_increase,
    )


async def get_response_feedback_stats(
    user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> ResponseFeedbackStats:
    """
    Retrieve statistics for response feedback
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
    """
    Retrieve statistics for content feedback
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
    feedback_curr_period_dict: dict, feedback_prev_period_dict: dict
) -> Dict[str, Union[int, float]]:
    """
    Get feedback statistics
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
    """
    Retrieve statistics for urgency
    """

    statement_combined = (
        select(
            func.sum(
                case(
                    (
                        (UrgencyResponseDB.response_datetime_utc <= end_date)
                        & (UrgencyResponseDB.response_datetime_utc > start_date)
                        & (UrgencyResponseDB.is_urgent == True),  # noqa
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
                        & (UrgencyResponseDB.is_urgent == True),  # noqa
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
        n_urgent=n_urgency_curr_period,
        percentage_increase=percentage_increase,
    )


def get_percentage_increase(n_curr: int, n_prev: int) -> float:
    """
    Calculate percentage increase
    """
    if n_prev == 0:
        return 0.0

    return (n_curr - n_prev) / n_prev
