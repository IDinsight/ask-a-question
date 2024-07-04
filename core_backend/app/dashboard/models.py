from datetime import date
from typing import Dict, Union, get_args

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
    Time,
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
        hour_of_day = row.hour_of_day
        n_questions = row.n_questions

        if hour_of_day % 2 == 1:
            hour_grp = hour_of_day - 1
        else:
            hour_grp = hour_of_day
        hour_grp_str = f"{hour_grp:02}:00"
        heatmap[hour_grp_str][day_of_week] += n_questions  # type: ignore

    return Heatmap.model_validate(heatmap)


def get_linechart(
    user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> Dict[str, Dict[str, int]]:
    """
    Retrieve count of queries over time for the user
    """
    return dict()


def initilize_heatmap() -> Dict[Time, Dict[Day, int]]:
    """
    Initialize heatmap dictionary
    """
    return {h: {d: 0 for d in get_args(Day)} for h in get_args(Time)}


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
