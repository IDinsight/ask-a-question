"""This module contains the FastAPI router for the dashboard endpoints."""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal, Tuple

import pandas as pd
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Request
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
) -> AIFeedbackSummary:
    """
    Retrieve AI summary of a content
    """

    today = datetime.now(timezone.utc)
    _, start_date = get_frequency_and_startdate(time_frequency)

    ai_summary = await get_ai_answer_summary(
        user_id=user_db.user_id,
        content_id=content_id,
        start_date=start_date,
        end_date=today,
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


@router.get("/insights/{time_frequency}/refresh", response_model=dict)
async def refresh_insights_frequency(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    request: Request,
    asession: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Refresh topic modelling insights for the time period specified.
    """

    _, start_date = get_frequency_and_startdate(time_frequency)

    await refresh_insights(
        time_frequency=time_frequency,
        user_db=user_db,
        request=request,
        start_date=start_date,
        asession=asession,
    )

    return {"status": "success"}


async def refresh_insights(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    request: Request,
    start_date: date,
    asession: AsyncSession = Depends(get_async_session),
) -> TopicsData:
    """
    Retrieve topic modelling insights for the time period specified
    and write to Redis.
    """

    redis = request.app.state.redis
    time_period_queries = await get_raw_queries(
        user_id=user_db.user_id,
        asession=asession,
        start_date=start_date,
    )

    content_data = await get_raw_contents(user_id=user_db.user_id, asession=asession)

    topic_output, embeddings_df = await topic_model_queries(
        user_id=user_db.user_id,
        query_data=time_period_queries,
        content_data=content_data,
    )

    embeddings_json = embeddings_df.to_json(orient="split")

    embeddings_key = f"{user_db.username}_embeddings_{time_frequency}"

    await redis.set(embeddings_key, embeddings_json)

    await redis.set(
        f"{user_db.username}_insights_{time_frequency}_results",
        topic_output.model_dump_json(),
    )
    return topic_output


@router.get("/insights/{time_frequency}", response_model=TopicsData)
async def retrieve_insights_frequency(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    request: Request,
) -> TopicsData:
    """
    Retrieve topic modelling insights for the time period specified.
    """

    redis = request.app.state.redis

    if await redis.exists(f"{user_db.username}_insights_{time_frequency}_results"):
        payload = await redis.get(
            f"{user_db.username}_insights_{time_frequency}_results"
        )
        parsed_payload = json.loads(payload)
        topics_data = TopicsData(**parsed_payload)
        return topics_data

    return TopicsData(
        refreshTimeStamp="",
        data=[],
    )


@router.get("/topic_visualization/{time_frequency}", response_model=dict)
async def create_plot(
    time_frequency: DashboardTimeFilter,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    request: Request,
) -> dict:
    """Creates a Bokeh plot based on embeddings data retrieved from Redis."""

    # Get Redis client
    redis = request.app.state.redis

    # Define the Redis key
    embeddings_key = f"{user_db.username}_embeddings_{time_frequency}"

    # Get the embeddings JSON from Redis
    embeddings_json = await redis.get(embeddings_key)
    if embeddings_json is None:
        # Handle missing data
        raise HTTPException(status_code=404, detail="Embeddings data not found")

    # Decode and parse the JSON
    embeddings_json = embeddings_json.decode("utf-8")
    embeddings_df = pd.read_json(embeddings_json, orient="split")

    # Create the Bokeh plot
    bokeh_plot_json = produce_bokeh_plot(embeddings_df)
    return bokeh_plot_json
