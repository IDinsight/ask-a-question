import json
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal, Optional, Tuple

import pandas as pd
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..users.models import UserDB
from ..utils import setup_logger
from .config import (
    MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY,
    MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT,
)
from .models import (
    get_ai_answer_summary,
    get_content_details,
    get_heatmap,
    get_overview_timeseries,
    get_raw_contents,
    get_raw_queries,
    get_stats_cards,
    get_timeseries_top_content,
    get_top_content,
)
from .plotting import produce_bokeh_plot
from .schemas import (
    AIFeedbackSummary,
    DashboardOverview,
    DashboardPerformance,
    DetailsDrawer,
    TimeFrequency,
    TopicsData,
)
from .topic_modeling import topic_model_queries

TAG_METADATA = {
    "name": "Dashboard",
    "description": "_Requires user login._ Dashboard data fetching operations.",
}

router = APIRouter(prefix="/dashboard", tags=[TAG_METADATA["name"]])
logger = setup_logger()

DashboardTimeFilter = Literal["day", "week", "month", "year", "custom"]


def get_frequency_and_startdate(
    time_frequency: DashboardTimeFilter,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
) -> Tuple[TimeFrequency, datetime, datetime]:
    """
    Get the frequency and start date for the given time frequency.
    """
    now_utc = datetime.now(timezone.utc)
    if time_frequency == "custom":
        if not start_date_str or not end_date_str:
            raise HTTPException(
                status_code=400,
                detail="start_date and end_date are required for custom time_frequency",
            )
        try:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )

        except ValueError:
            raise HTTPException(
                400, detail="Invalid date format; must be YYYY-MM-DD"
            ) from None

        if end_dt < start_dt:
            raise HTTPException(400, detail="end_date must be >= start_date")

        # Do monthly bars if the time period is more than a year
        if start_dt - end_dt > timedelta(days=365):
            return TimeFrequency.Month, start_dt, end_dt

        return TimeFrequency.Day, start_dt, end_dt

    match time_frequency:
        case "day":
            return TimeFrequency.Hour, now_utc - timedelta(days=1), now_utc
        case "week":
            return TimeFrequency.Day, now_utc - timedelta(weeks=1), now_utc
        case "month":
            return TimeFrequency.Day, now_utc + relativedelta(months=-1), now_utc
        case "year":
            return TimeFrequency.Month, now_utc + relativedelta(years=-1), now_utc
        case _:
            raise ValueError(f"Invalid time frequency: {time_frequency}")


@router.get("/performance/{time_frequency}/{content_id}", response_model=DetailsDrawer)
async def retrieve_content_details(
    content_id: int,
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> DetailsDrawer:
    """
    Retrieve detailed statistics of a content
    """
    frequency, start_dt, end_dt = get_frequency_and_startdate(
        time_frequency, start_date, end_date
    )
    details = await get_content_details(
        user_id=user_db.user_id,
        content_id=content_id,
        asession=asession,
        start_date=start_dt,
        end_date=end_dt,
        frequency=frequency,
        max_feedback_records=int(MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT),
    )
    return details


@router.get(
    "/performance/{time_frequency}/{content_id}/ai-summary",
    response_model=AIFeedbackSummary,
)
async def retrieve_content_ai_summary(
    content_id: int,
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> AIFeedbackSummary:
    """
    Retrieve AI summary of a content
    """
    frequency, start_dt, end_dt = get_frequency_and_startdate(
        time_frequency, start_date, end_date
    )
    ai_summary = await get_ai_answer_summary(
        user_id=user_db.user_id,
        content_id=content_id,
        start_date=start_dt,
        end_date=end_dt,
        max_feedback_records=int(MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY),
        asession=asession,
    )
    return AIFeedbackSummary(ai_summary=ai_summary)


@router.get("/performance/{time_frequency}", response_model=DashboardPerformance)
async def retrieve_performance_frequency(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
    top_n: int | None = None,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> DashboardPerformance:
    """
    Retrieve timeseries data on content usage and performance of each content
    """
    frequency, start_dt, end_dt = get_frequency_and_startdate(
        time_frequency, start_date, end_date
    )
    performance_stats = await retrieve_performance(
        user_id=user_db.user_id,
        asession=asession,
        top_n=top_n,
        start_date=start_dt,
        end_date=end_dt,
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
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> DashboardOverview:
    """
    Retrieve all question answer statistics for the last day.
    """
    frequency, start_dt, end_dt = get_frequency_and_startdate(
        time_frequency, start_date, end_date
    )
    stats = await retrieve_overview(
        user_id=user_db.user_id,
        asession=asession,
        start_date=start_dt,
        end_date=end_dt,
        frequency=frequency,
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


@router.get("/insights/{time_frequency}/refresh", response_model=dict)
async def refresh_insights_frequency(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    request: Request,
    background_tasks: BackgroundTasks,
    asession: AsyncSession = Depends(get_async_session),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> dict:
    """
    Refresh topic modelling insights for the time period specified.
    """
    _, start_dt, end_dt = get_frequency_and_startdate(
        time_frequency, start_date, end_date
    )
    background_tasks.add_task(
        refresh_insights,
        time_frequency=time_frequency,
        user_db=user_db,
        request=request,
        start_date=start_dt,
        end_date=end_dt,
        asession=asession,
    )
    return {"detail": "Refresh task started in background."}


async def refresh_insights(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    request: Request,
    start_date: date,
    end_date: date,
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Retrieve topic modelling insights for the time period specified
    and write to Redis.
    Returns None since this function is called by a background task +
    only ever writes to Redis.
    """
    redis = request.app.state.redis
    await redis.set(
        f"{user_db.username}_insights_{time_frequency}_results",
        TopicsData(
            status="in_progress",
            refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
            data=[],
        ).model_dump_json(),
    )
    try:
        step = "Retrieve queries"
        time_period_queries = await get_raw_queries(
            user_id=user_db.user_id,
            asession=asession,
            start_date=start_date,
            end_date=end_date,
        )
        step = "Retrieve contents"
        content_data = await get_raw_contents(
            user_id=user_db.user_id, asession=asession
        )
        topic_output, embeddings_df = await topic_model_queries(
            user_id=user_db.user_id,
            query_data=time_period_queries,
            content_data=content_data,
        )
        step = "Write to Redis"
        embeddings_json = embeddings_df.to_json(orient="split")
        embeddings_key = f"{user_db.username}_embeddings_{time_frequency}"
        await redis.set(embeddings_key, embeddings_json)
        await redis.set(
            f"{user_db.username}_insights_{time_frequency}_results",
            topic_output.model_dump_json(),
        )
        return
    except Exception as e:
        error_msg = str(e)
        logger.error(error_msg)
        await redis.set(
            f"{user_db.username}_insights_{time_frequency}_results",
            TopicsData(
                status="error",
                refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
                data=[],
                error_message=error_msg,
                failure_step=step if step else None,
            ).model_dump_json(),
        )


@router.get("/insights/{time_frequency}", response_model=TopicsData)
async def retrieve_insights_frequency(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> TopicsData:
    """
    Retrieve topic modelling insights for the time period specified.
    """
    redis = request.app.state.redis
    key = f"{user_db.username}_insights_{time_frequency}_results"
    if await redis.exists(key):
        payload = await redis.get(key)
        parsed_payload = json.loads(payload)
        return TopicsData(**parsed_payload)
    return TopicsData(status="not_started", refreshTimeStamp="", data=[])


@router.get("/topic_visualization/{time_frequency}", response_model=dict)
async def create_plot(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> dict:
    """Creates a Bokeh plot based on embeddings data retrieved from Redis."""
    redis = request.app.state.redis
    _, start_dt, end_dt = get_frequency_and_startdate(
        time_frequency, start_date, end_date
    )
    embeddings_key = f"{user_db.username}_embeddings_{time_frequency}"
    embeddings_json = await redis.get(embeddings_key)
    if not embeddings_json:
        raise HTTPException(status_code=404, detail="Embeddings data not found")
    df = pd.read_json(embeddings_json.decode("utf-8"), orient="split")
    return produce_bokeh_plot(df)
