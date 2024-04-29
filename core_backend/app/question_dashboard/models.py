from datetime import datetime, timedelta
from datetime import timezone as tz
from typing import List

from sqlalchemy import Float, cast, extract, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..question_answer.models import ResponseFeedbackDB, UserQueryDB
from .schemas import QuestionDashBoard


async def get_dashboard_stats(asession: AsyncSession) -> QuestionDashBoard:
    """
    Retrieve statistics for question answering and upvotes
    """
    now = datetime.now(tz.utc).replace(tzinfo=None)
    six_months_ago = now - timedelta(days=30 * 6)
    question_stats = await get_questions_stats(asession, six_months_ago, now)
    upvote_stats = await get_upvotes_stats(asession, six_months_ago, now)
    return QuestionDashBoard(
        six_months_questions=question_stats, six_months_upvotes=upvote_stats
    )


async def get_questions_stats(
    asession: AsyncSession, from_date: datetime, to_date: datetime
) -> List[int]:
    """
    SQLALchemy data model to retrieve the number of questions asked in the past
    6 months
    """

    stmt = (
        select(
            extract("year", UserQueryDB.query_datetime_utc).label("year"),
            extract("month", UserQueryDB.query_datetime_utc).label("month"),
            cast(func.count(UserQueryDB.query_id), Float).label("count"),
        )
        .where(UserQueryDB.query_datetime_utc >= from_date)
        .group_by("year", "month")
        .order_by("year", "month")
    )
    result = await asession.execute(stmt)

    month_counts = [
        {"month": datetime(int(year), int(month), 1).strftime("%Y-%m"), "count": count}
        for year, month, count in result.all()
    ]

    dashboard_data = {
        (datetime(to_date.year, to_date.month, 1) - timedelta(days=30 * i)).strftime(
            "%Y-%m"
        ): 0
        for i in range(6)
    }

    dashboard_data.update({month["month"]: month["count"] for month in month_counts})

    # Sort by date and extract counts
    sorted_months = sorted(dashboard_data.items(), key=lambda x: x[0], reverse=False)
    six_months_count = [count for _, count in sorted_months]

    return six_months_count


async def get_upvotes_stats(
    asession: AsyncSession, from_date: datetime, to_date: datetime
) -> List[int]:
    """
    SQLALchemy data model to retrieve the number of questions asked in the past
    6 months
    """
    stmt = (
        select(
            extract("year", ResponseFeedbackDB.feedback_datetime_utc).label("year"),
            extract("month", ResponseFeedbackDB.feedback_datetime_utc).label("month"),
            cast(func.count(ResponseFeedbackDB.feedback_id), Float).label("count"),
        )
        .where(
            (ResponseFeedbackDB.feedback_datetime_utc >= from_date)
            & (ResponseFeedbackDB.feedback_sentiment == "positive")
        )
        .group_by("year", "month")
        .order_by("year", "month")
    )
    result = await asession.execute(stmt)
    month_counts = [
        {"month": datetime(int(year), int(month), 1).strftime("%Y-%m"), "count": count}
        for year, month, count in result.all()
    ]

    dashboard_data = {
        (datetime(to_date.year, to_date.month, 1) - timedelta(days=30 * i)).strftime(
            "%Y-%m"
        ): 0
        for i in range(6)
    }

    dashboard_data.update({month["month"]: month["count"] for month in month_counts})

    # Sort by date and extract counts
    sorted_months = sorted(dashboard_data.items(), key=lambda x: x[0], reverse=False)
    six_months_count = [count for _, count in sorted_months]
    return six_months_count
