from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal

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

DashboardTimeFilter = Literal["day", "week", "month", "year"]


@router.get("/overview/{time_frequency}", response_model=DashboardOverview)
async def retrieve_overview_day(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics
    """

    today = datetime.now(timezone.utc)

    match time_frequency:
        case "day":
            start_date = today - timedelta(days=1)
            frequency = TimeFrequency.Hour
        case "week":
            start_date = today - timedelta(weeks=1)
            frequency = TimeFrequency.Day  # pylint: disable=redefined-variable-type
        case "month":
            start_date = today + relativedelta(months=-1)
            frequency = TimeFrequency.Day
        case "year":
            start_date = today + relativedelta(years=-1)
            frequency = TimeFrequency.Week
        case _:
            raise ValueError(f"Invalid time frequency: {time_frequency}")

    stats = await retrieve_overview(
        user_id=user_db.user_id,
        asession=asession,
        start_date=start_date,
        end_date=today,
        frequency=frequency,
    )

    return stats


async def retrieve_overview(
    user_id: int,
    asession: AsyncSession,
    start_date: date,
    end_date: date,
    frequency: TimeFrequency,
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
        top_n=4,
    )

    return DashboardOverview(
        stats_cards=stats,
        heatmap=heatmap,
        time_series=time_series,
        top_content=top_content,
    )
