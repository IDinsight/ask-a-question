"""This module contains the FastAPI router for the dashboard endpoints."""

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal, Tuple

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..users.models import UserDB
from ..utils import setup_logger
from .models import (
    get_content_details,
    get_heatmap,
    get_overview_timeseries,
    get_stats_cards,
    get_timeseries_top_content,
    get_top_content,
)
from .schemas import (
    DashboardOverview,
    DashboardPerformance,
    DetailsDrawer,
    TimeFrequency,
)

TAG_METADATA = {
    "name": "Dashboard",
    "description": "_Requires user login._ Dashboard data fetching operations.",
}

router = APIRouter(prefix="/dashboard", tags=[TAG_METADATA["name"]])
logger = setup_logger()

DashboardTimeFilter = Literal["day", "week", "month", "year"]


@router.get("/performance/{time_frequency}/{content_id}", response_model=DetailsDrawer)
async def retrieve_content_details(
    content_id: int,
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DetailsDrawer:
    """
    Retrieve detailed statistics of a content
    """

    today = datetime.now(timezone.utc)
    frequency, start_date = get_frequency_and_startdate(time_frequency)

    details = await get_content_details(
        user_id=user_db.user_id,
        content_id=content_id,
        asession=asession,
        start_date=start_date,
        end_date=today,
        frequency=frequency,
    )
    return details


@router.get("/performance/{time_frequency}", response_model=DashboardPerformance)
async def retrieve_performance_frequency(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
    top_n: int | None = None,
) -> DashboardPerformance:
    """
    Retrieve timeseries data on content usage and performance of each content
    """

    today = datetime.now(timezone.utc)
    frequency, start_date = get_frequency_and_startdate(time_frequency)

    performance_stats = await retrieve_performance(
        user_id=user_db.user_id,
        asession=asession,
        top_n=top_n,
        start_date=start_date,
        end_date=today,
        frequency=frequency,
    )
    return performance_stats


async def retrieve_performance(
    user_id: int,
    asession: AsyncSession,
    top_n: int | None,
    start_date: date,
    end_date: date,
    frequency: TimeFrequency,
) -> DashboardPerformance:
    """
    Retrieve timeseries data on content usage and performance of each content
    """
    content_time_series = await get_timeseries_top_content(
        user_id=user_id,
        asession=asession,
        top_n=top_n,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
    )

    return DashboardPerformance(content_time_series=content_time_series)


@router.get("/overview/{time_frequency}", response_model=DashboardOverview)
async def retrieve_overview_frequency(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics for the last day.
    """

    today = datetime.now(timezone.utc)
    frequency, start_date = get_frequency_and_startdate(time_frequency)

    stats = await retrieve_overview(
        user_id=user_db.user_id,
        asession=asession,
        start_date=start_date,
        end_date=today,
        frequency=frequency,
    )

    return stats


def get_frequency_and_startdate(
    time_frequency: DashboardTimeFilter,
) -> Tuple[TimeFrequency, datetime]:
    """
    Get the time frequency and start date based on the time filter
    """
    match time_frequency:
        case "day":
            return TimeFrequency.Hour, datetime.now(timezone.utc) - timedelta(days=1)
        case "week":
            return TimeFrequency.Day, datetime.now(timezone.utc) - timedelta(weeks=1)
        case "month":
            return TimeFrequency.Day, datetime.now(timezone.utc) + relativedelta(
                months=-1
            )
        case "year":
            return TimeFrequency.Week, datetime.now(timezone.utc) + relativedelta(
                years=-1
            )
        case _:
            raise ValueError(f"Invalid time frequency: {time_frequency}")


async def retrieve_overview(
    user_id: int,
    asession: AsyncSession,
    start_date: date,
    end_date: date,
    frequency: TimeFrequency,
    top_n: int = 4,
) -> DashboardOverview:
    """Retrieve all question answer statistics.

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
    frequency
        The frequency at which to retrieve the statistics.
    top_n
        The number of top content to retrieve.

    Returns
    -------
    DashboardOverview
        The dashboard overview statistics.
    """

    stats = await get_stats_cards(
        user_id=user_id,
        asession=asession,
        start_date=start_date,
        end_date=end_date,
    )

    heatmap = await get_heatmap(
        user_id=user_id,
        asession=asession,
        start_date=start_date,
        end_date=end_date,
    )

    time_series = await get_overview_timeseries(
        user_id=user_id,
        asession=asession,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
    )

    top_content = await get_top_content(
        user_id=user_id,
        asession=asession,
        top_n=top_n,
    )

    return DashboardOverview(
        stats_cards=stats,
        heatmap=heatmap,
        time_series=time_series,
        top_content=top_content,
    )
