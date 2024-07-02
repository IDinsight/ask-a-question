from datetime import date, datetime, timedelta
from typing import Annotated

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..users.models import UserDB
from ..utils import setup_logger
from .models import get_stats_cards
from .schemas import DashboardOverview

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
logger = setup_logger()


@router.get("/overview/day", response_model=DashboardOverview)
async def retrieve_overview_day(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics
    """
    today = datetime.utcnow()
    day_ago = today - timedelta(days=1)

    stats = await retrieve_overview(
        user_id=user_db.user_id, asession=asession, start_date=day_ago, end_date=today
    )

    return stats


@router.get("/overview/week", response_model=DashboardOverview)
async def retrieve_overview_week(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics
    """
    today = datetime.utcnow()
    week_ago = today - timedelta(days=7)

    stats = await retrieve_overview(
        user_id=user_db.user_id, asession=asession, start_date=week_ago, end_date=today
    )

    return stats


@router.get("/overview/month", response_model=DashboardOverview)
async def retrieve_overview_month(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics
    """
    today = datetime.utcnow()
    month_ago = today + relativedelta(months=-1)

    stats = await retrieve_overview(
        user_id=user_db.user_id, asession=asession, start_date=month_ago, end_date=today
    )

    return stats


@router.get("/overview/year", response_model=DashboardOverview)
async def retrieve_overview_year(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics
    """
    today = datetime.utcnow()
    year_ago = today + relativedelta(years=-1)

    stats = await retrieve_overview(
        user_id=user_db.user_id, asession=asession, start_date=year_ago, end_date=today
    )

    return stats


async def retrieve_overview(
    user_id: int,
    asession: AsyncSession,
    start_date: date,
    end_date: date,
) -> DashboardOverview:
    """
    Retrieve all question answer statistics
    """
    stats = await get_stats_cards(
        user_id=user_id,
        asession=asession,
        start_date=start_date,
        end_date=end_date,
    )

    return DashboardOverview(stats_cards=stats)
