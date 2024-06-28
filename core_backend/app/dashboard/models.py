from datetime import date
from typing import Dict, Union

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..question_answer.models import (
    ContentFeedbackDB,
    QueryDB,
    ResponseFeedbackDB,
)
from ..urgency_detection.models import UrgencyResponseDB
from .schemas import (
    ContentFeedbackStats,
    QueryStats,
    ResponseFeedbackStats,
    StatsCards,
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


async def get_query_count_stats(
    user_id: int, asession: AsyncSession, start_date: date, end_date: date
) -> QueryStats:
    """
    Retrieve statistics for question answering
    """
    # Total questions asked in this period
    statement_curr = select(func.count(QueryDB.query_id)).where(
        QueryDB.user_id == user_id,
        QueryDB.query_datetime_utc <= end_date,
        QueryDB.query_datetime_utc > start_date,
    )
    n_questions_curr_period = (await asession.execute(statement_curr)).scalar() or 0

    # Total questions asked in the previous period
    statement_previous = select(func.count(QueryDB.query_id)).where(
        QueryDB.user_id == user_id,
        QueryDB.query_datetime_utc <= start_date,
        QueryDB.query_datetime_utc > start_date - (end_date - start_date),
    )
    n_questions_prev_period = (await asession.execute(statement_previous)).scalar() or 0

    # Percentage increase in questions asked
    if n_questions_prev_period == 0:
        percent_increase = 0.0
    else:
        percent_increase = (
            n_questions_curr_period - n_questions_prev_period
        ) / n_questions_prev_period

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
    statement_curr = (
        select(
            ResponseFeedbackDB.feedback_sentiment,
            func.count(ResponseFeedbackDB.feedback_id),
        )
        .join(ResponseFeedbackDB.query)
        .where(
            ResponseFeedbackDB.query.has(user_id=user_id),
            ResponseFeedbackDB.feedback_datetime_utc <= end_date,
            ResponseFeedbackDB.feedback_datetime_utc > start_date,
        )
        .group_by(ResponseFeedbackDB.feedback_sentiment)
    )

    feedback_curr_period = (await asession.execute(statement_curr)).fetchall()
    feedback_curr_period_dict = {row[0]: row[1] for row in feedback_curr_period}

    statement_previous = (
        select(
            ResponseFeedbackDB.feedback_sentiment,
            func.count(ResponseFeedbackDB.feedback_id),
        )
        .join(ResponseFeedbackDB.query)
        .where(
            ResponseFeedbackDB.query.has(user_id=user_id),
            ResponseFeedbackDB.feedback_datetime_utc <= start_date,
            ResponseFeedbackDB.feedback_datetime_utc
            > start_date - (end_date - start_date),
        )
        .group_by(ResponseFeedbackDB.feedback_sentiment)
    )

    feedback_prev_period = (await asession.execute(statement_previous)).fetchall()
    feedback_prev_period_dict = {row[0]: row[1] for row in feedback_prev_period}

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
    statement_curr = (
        select(
            ContentFeedbackDB.feedback_sentiment,
            func.count(ContentFeedbackDB.feedback_id),
        )
        .join(ContentFeedbackDB.content)
        .where(
            ContentFeedbackDB.content.has(user_id=user_id),
            ContentFeedbackDB.feedback_datetime_utc <= end_date,
            ContentFeedbackDB.feedback_datetime_utc > start_date,
        )
        .group_by(ContentFeedbackDB.feedback_sentiment)
    )

    feedback_curr_period = (await asession.execute(statement_curr)).fetchall()
    feedback_curr_period_dict = {row[0]: row[1] for row in feedback_curr_period}

    statement_previous = (
        select(
            ContentFeedbackDB.feedback_sentiment,
            func.count(ContentFeedbackDB.feedback_id),
        )
        .join(ContentFeedbackDB.content)
        .where(
            ContentFeedbackDB.content.has(user_id=user_id),
            ContentFeedbackDB.feedback_datetime_utc <= start_date,
            ContentFeedbackDB.feedback_datetime_utc
            > start_date - (end_date - start_date),
        )
        .group_by(ContentFeedbackDB.feedback_sentiment)
    )

    feedback_prev_period = (await asession.execute(statement_previous)).fetchall()
    feedback_prev_period_dict = {row[0]: row[1] for row in feedback_prev_period}

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

    if n_positive_prev == 0:
        percentage_positive_increase = 0.0
    else:
        percentage_positive_increase = (
            n_positive_curr - n_positive_prev
        ) / n_positive_prev

    if n_negative_prev == 0:
        percentage_negative_increase = 0.0
    else:
        percentage_negative_increase = (
            n_negative_curr - n_negative_prev
        ) / n_negative_prev

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

    statement_curr = (
        select(func.count(UrgencyResponseDB.urgency_response_id))
        .join(UrgencyResponseDB.query)
        .where(
            UrgencyResponseDB.query.has(user_id=user_id),
            UrgencyResponseDB.response_datetime_utc <= end_date,
            UrgencyResponseDB.response_datetime_utc > start_date,
            UrgencyResponseDB.is_urgent == True,  # noqa
        )
    )

    n_urgency_curr_period = (await asession.execute(statement_curr)).scalar() or 0

    statement_previous = (
        select(func.count(UrgencyResponseDB.urgency_response_id))
        .join(UrgencyResponseDB.query)
        .where(
            UrgencyResponseDB.query.has(user_id=user_id),
            UrgencyResponseDB.response_datetime_utc <= start_date,
            UrgencyResponseDB.response_datetime_utc
            > start_date - (end_date - start_date),
            UrgencyResponseDB.is_urgent == True,  # noqa
        )
    )

    n_urgency_prev_period = (await asession.execute(statement_previous)).scalar() or 0

    if n_urgency_prev_period == 0:
        percentage_increase = 0.0
    else:
        percentage_increase = (
            n_urgency_curr_period - n_urgency_prev_period
        ) / n_urgency_prev_period

    return UrgencyStats(
        n_urgent=n_urgency_curr_period,
        percentage_increase=percentage_increase,
    )
