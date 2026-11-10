"""This module contains FastAPI routers for dashboard endpoints."""

from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from langfuse.decorators import observe  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_workspace_name
from app.core.database import get_async_session
from app.dashboard.schemas import (
    AIFeedbackSummary,
    DashboardOverview,
    DashboardPerformance,
    DashboardTimeFilter,
    DetailsDrawer,
    TimeFrequency,
    TopicsData,
)
from app.dashboard.service import (
    create_topic_plot,
    get_content_ai_summary_for_timeframe,
    get_content_details_for_timeframe,
    get_insights,
    get_insights_refresh_window,
    get_overview_for_timeframe,
    get_performance_for_timeframe,
    refresh_insights,
)

TAG_METADATA = {
    "name": "Dashboard",
    "description": "_Requires user login._ Dashboard data fetching operations.",
}

router = APIRouter(prefix="/dashboard", tags=[TAG_METADATA["name"]])


@router.get("/performance/{timeframe}/{content_id}", response_model=DetailsDrawer)
async def retrieve_content_details(
    content_id: int,
    timeframe: DashboardTimeFilter,
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> DetailsDrawer:
    """Retrieve detailed statistics of a content.

    Parameters
    ----------
    content_id
        The ID of the content to retrieve details for.
    timeframe
        The time frequency to retrieve details for.
    workspace_name
        The name of the workspace to retrieve details for.
    asession
        The SQLAlchemy async session to use for all database connections.
    start_date
        The start date for the time period.
    end_date
        The end date for the time period.

    Returns
    -------
    DetailsDrawer
        The details of the content.
    """

    return await get_content_details_for_timeframe(
        asession=asession,
        content_id=content_id,
        end_date=end_date,
        start_date=start_date,
        timeframe=timeframe,
        workspace_name=workspace_name,
    )


@router.get(
    "/performance/{timeframe}/{content_id}/ai-summary",
    response_model=AIFeedbackSummary,
)
@observe()
async def retrieve_content_ai_summary(
    content_id: int,
    timeframe: DashboardTimeFilter,
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> AIFeedbackSummary:
    """Retrieve AI summary of a content.

    Parameters
    ----------
    content_id
        The ID of the content to retrieve details for.
    timeframe
        The time frequency to retrieve details for.
    workspace_name
        The name of the workspace to retrieve details for.
    asession
        The SQLAlchemy async session to use for all database connections.
    start_date
        The start date for the time period.
    end_date
        The end date for the time period.

    Returns
    -------
    AIFeedbackSummary
        The AI summary of the content.
    """

    return await get_content_ai_summary_for_timeframe(
        asession=asession,
        content_id=content_id,
        end_date=end_date,
        start_date=start_date,
        timeframe=timeframe,
        workspace_name=workspace_name,
    )


@router.get("/performance/{timeframe}", response_model=DashboardPerformance)
async def retrieve_performance_frequency(
    timeframe: DashboardTimeFilter,
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
    top_n: int | None = None,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> DashboardPerformance:
    """Retrieve timeseries data on content usage and performance of each content.

    Parameters
    ----------
    timeframe
        The time frequency to retrieve performance for.
    workspace_name
        The name of the workspace to retrieve performance for.
    asession
        The SQLAlchemy async session to use for all database connections.
    top_n
        The number of top content to retrieve.
    start_date
        The start date for the time period.
    end_date
        The end date for the time period.

    Returns
    -------
    DashboardPerformance
        The dashboard performance timeseries.
    """

    return await get_performance_for_timeframe(
        asession=asession,
        end_date=end_date,
        start_date=start_date,
        timeframe=timeframe,
        top_n=top_n,
        workspace_name=workspace_name,
    )


@router.get("/overview/{timeframe}", response_model=DashboardOverview)
async def retrieve_overview_frequency(
    timeframe: DashboardTimeFilter,
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    frequency: Optional[TimeFrequency] = None,
) -> DashboardOverview:
    """Retrieve all question answer statistics for the last day.

    Parameters
    ----------
    timeframe
        The time frequency to retrieve overview for.
    workspace_name
        The name of the workspace to retrieve overview frequency for.
    asession
        The SQLAlchemy async session to use for all database connections.
    start_date
        The start date for the time period.
    end_date
        The end date for the time period.
    frequency
        The frequency at which to retrieve the statistics.

    Returns
    -------
    DashboardOverview
        The dashboard overview statistics.
    """

    return await get_overview_for_timeframe(
        asession=asession,
        end_date=end_date,
        frequency=frequency,
        start_date=start_date,
        timeframe=timeframe,
        workspace_name=workspace_name,
    )


@router.get("/insights/{timeframe}/refresh", response_model=dict)
async def refresh_insights_frequency(
    timeframe: DashboardTimeFilter,
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    request: Request,
    background_tasks: BackgroundTasks,
    asession: AsyncSession = Depends(get_async_session),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
) -> dict[str, str]:
    """Refresh topic modelling insights for the time period specified.

    Parameters
    ----------
    timeframe
        The time frequency to retrieve insights for.
    workspace_name
        The name of the workspace to retrieve insights for.
    request
        The request object.
    background_tasks
        The background tasks to run.
    asession
        The SQLAlchemy async session to use for all database connections.
    start_date
        The start date for the time period.
    end_date
        The end date for the time period.

    Returns
    -------
    dict
        A dictionary with a message indicating that the refresh task has started.
    """

    workspace_db, start_dt, end_dt = await get_insights_refresh_window(
        asession=asession,
        end_date=end_date,
        start_date=start_date,
        timeframe=timeframe,
        workspace_name=workspace_name,
    )

    background_tasks.add_task(
        refresh_insights,
        end_date=end_dt,
        redis=request.app.state.redis,
        start_date=start_dt,
        timeframe=timeframe,
        workspace_db=workspace_db,
    )

    return {"detail": "Refresh task started in background."}


@router.get("/insights/{timeframe}", response_model=TopicsData)
async def retrieve_insights_frequency(
    timeframe: DashboardTimeFilter,
    request: Request,
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> TopicsData:
    """Retrieve topic modelling insights for the time period specified.

    Parameters
    ----------
    timeframe
        The time frequency to retrieve insights for.
    request
        The request object.
    workspace_name
        The name of the workspace to retrieve insights for.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    TopicsData
        The topic modelling insights for the time period specified.
    """

    return await get_insights(
        asession=asession,
        redis=request.app.state.redis,
        timeframe=timeframe,
        workspace_name=workspace_name,
    )


@router.get("/topic_visualization/{timeframe}", response_model=dict)
async def create_plot(
    timeframe: DashboardTimeFilter,
    request: Request,
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> dict:
    """Create a Bokeh plot based on embeddings data retrieved from Redis.

    Parameters
    ----------
    timeframe
        The time frequency to retrieve insights for.
    request
        The request object.
    workspace_name
        The name of the workspace to create the plot for.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    dict
        A dictionary containing the Bokeh plot.

    Raises
    ------
    HTTPException
        If the embeddings data is not found in Redis.
    """

    return await create_topic_plot(
        asession=asession,
        redis=request.app.state.redis,
        timeframe=timeframe,
        workspace_name=workspace_name,
    )
