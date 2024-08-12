"""This module contains the FastAPI router for the dashboard endpoints."""

from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..users.models import UserDB
from ..utils import setup_logger
from .models import get_heatmap, get_stats_cards, get_timeseries, get_top_content
from .schemas import DashboardOverview, TimeFrequency

TAG_METADATA = {
    "name": "Dashboard",
    "description": "_Requires user login._ Dashboard data fetching operations.",
}

router = APIRouter(prefix="/dashboard", tags=[TAG_METADATA["name"]])
logger = setup_logger()


@router.get("/overview/day", response_model=DashboardOverview)
async def retrieve_overview_day(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics for the last day.
    """
    today = datetime.now(timezone.utc)
    day_ago = today - timedelta(days=1)

    stats = await retrieve_overview(
        user_id=user_db.user_id,
        asession=asession,
        start_date=day_ago,
        end_date=today,
        frequency=TimeFrequency.Hour,
    )

    return stats


@router.get("/overview/week", response_model=DashboardOverview)
async def retrieve_overview_week(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics for the last week.
    """
    today = datetime.now(timezone.utc)
    week_ago = today - timedelta(days=7)

    stats = await retrieve_overview(
        user_id=user_db.user_id,
        asession=asession,
        start_date=week_ago,
        end_date=today,
        frequency=TimeFrequency.Day,
    )

    return stats


@router.get("/overview/month", response_model=DashboardOverview)
async def retrieve_overview_month(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics for the last month.
    """
    today = datetime.now(timezone.utc)
    month_ago = today + relativedelta(months=-1)

    stats = await retrieve_overview(
        user_id=user_db.user_id,
        asession=asession,
        start_date=month_ago,
        end_date=today,
        frequency=TimeFrequency.Day,
    )

    return stats


@router.get("/overview/year", response_model=DashboardOverview)
async def retrieve_overview_year(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics for the last year.
    """
    today = datetime.now(timezone.utc)
    year_ago = today + relativedelta(years=-1)

    stats = await retrieve_overview(
        user_id=user_db.user_id,
        asession=asession,
        start_date=year_ago,
        end_date=today,
        frequency=TimeFrequency.Week,
    )

    return stats


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

    time_series = await get_timeseries(
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
