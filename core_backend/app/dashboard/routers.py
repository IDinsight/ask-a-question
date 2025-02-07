"""This module contains FastAPI routers for dashboard endpoints."""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal, Optional

import pandas as pd
from dateutil.relativedelta import relativedelta
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_workspace_name
from ..database import get_async_session
from ..users.models import WorkspaceDB
from ..utils import setup_logger
from ..workspaces.utils import get_workspace_by_workspace_name
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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    # Use `start_dt`/`end_dt` to avoid typing errors etc.
    frequency, start_dt, end_dt = get_freq_start_end_date(
        end_date_str=end_date, start_date_str=start_date, timeframe=timeframe
    )

    details = await get_content_details(
        asession=asession,
        content_id=content_id,
        end_date=end_dt,
        frequency=frequency,
        max_feedback_records=int(MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT),
        start_date=start_dt,
        workspace_id=workspace_db.workspace_id,
    )
    return details


@router.get(
    "/performance/{timeframe}/{content_id}/ai-summary",
    response_model=AIFeedbackSummary,
)
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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    _, start_dt, end_dt = get_freq_start_end_date(
        end_date_str=end_date,
        frequency=TimeFrequency.Day,
        start_date_str=start_date,
        timeframe=timeframe,
    )

    ai_summary = await get_ai_answer_summary(
        asession=asession,
        content_id=content_id,
        end_date=end_dt,
        max_feedback_records=int(MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY),
        start_date=start_dt,
        workspace_id=workspace_db.workspace_id,
    )

    return AIFeedbackSummary(ai_summary=ai_summary)


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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    freq, start_dt, end_dt = get_freq_start_end_date(
        end_date_str=end_date,
        frequency=TimeFrequency.Day,
        start_date_str=start_date,
        timeframe=timeframe,
    )
    performance_stats = await retrieve_performance(
        asession=asession,
        end_date=end_dt,
        frequency=freq,
        start_date=start_dt,
        top_n=top_n,
        workspace_id=workspace_db.workspace_id,
    )

    return performance_stats


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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    # Use renamed `start_dt`/`end_dt` to avoid typing errors etc.
    freq, start_dt, end_dt = get_freq_start_end_date(
        end_date_str=end_date,
        frequency=frequency,
        start_date_str=start_date,
        timeframe=timeframe,
    )
    stats = await retrieve_overview(
        asession=asession,
        end_date=end_dt,
        frequency=freq,
        start_date=start_dt,
        workspace_id=workspace_db.workspace_id,
    )

    return stats


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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    # `TimeFrequency` doesn't actually matter here (but still required) so we just
    # pass day to get the start and end date.
    _, start_dt, end_dt = get_freq_start_end_date(
        end_date_str=end_date,
        frequency=TimeFrequency.Day,
        start_date_str=start_date,
        timeframe=timeframe,
    )

    background_tasks.add_task(
        refresh_insights,
        asession=asession,
        end_date=end_dt,
        request=request,
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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    redis = request.app.state.redis
    key = f"{workspace_db.workspace_name}_insights_{timeframe}_results"
    if await redis.exists(key):
        payload = await redis.get(key)
        parsed_payload = json.loads(payload)
        return TopicsData(**parsed_payload)
    return TopicsData(data=[], refreshTimeStamp="", status="not_started")


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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    redis = request.app.state.redis
    embeddings_key = f"{workspace_db.workspace_name}_embeddings_{timeframe}"
    embeddings_json = await redis.get(embeddings_key)

    if not embeddings_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Embeddings data not found."
        )

    df = pd.read_json(embeddings_json.decode("utf-8"), orient="split")
    return produce_bokeh_plot(embeddings_df=df)


def get_freq_start_end_date(
    *,
    end_date_str: Optional[str] = None,
    frequency: Optional[TimeFrequency] = None,
    start_date_str: Optional[str] = None,
    timeframe: DashboardTimeFilter,
) -> tuple[TimeFrequency, datetime, datetime]:
    """Get the frequency and start date for the given time frequency.

    Parameters
    ----------
    end_date_str
        The end date for the time period.
    frequency
        The frequency for the time period.
    start_date_str
        The start date for the time period.
    timeframe
        The time frequency to get the start date for.

    Returns
    -------
    tuple[TimeFrequency, datetime, datetime]
        The frequency and start and end datetimes for the given time frequency.

    Raises
    ------
    HTTPException
        If the start and end dates are not provided for a custom timeframe.
        If the frequency is not provided for a custom timeframe.
        If the date format is invalid.
        If the end date is before the start date.
        If the time frequency is invalid.
    ValueError
        If the time frequency is invalid.
    """

    now_utc = datetime.now(timezone.utc)
    if timeframe == "custom":
        if not start_date_str or not end_date_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="`start_date` and `end_date` are required for custom timeframe.",
            )
        if not frequency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="`frequency` is required for custom timeframe.",
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
                status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format; must be YYYY-MM-DD",
            ) from None

        if end_dt < start_dt:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="`end_date` must be >= `start_date`"
            )

        return frequency, start_dt, end_dt

    # For predefined timeframes, set default frequencies.
    match timeframe:
        case "day":
            return TimeFrequency.Hour, now_utc - timedelta(days=1), now_utc
        case "week":
            return TimeFrequency.Day, now_utc - timedelta(weeks=1), now_utc
        case "month":
            return TimeFrequency.Day, now_utc + relativedelta(months=-1), now_utc
        case "year":
            return TimeFrequency.Month, now_utc + relativedelta(years=-1), now_utc
        case _:
            raise ValueError(f"Invalid time frequency: {timeframe}")


async def refresh_insights(
    *,
    asession: AsyncSession = Depends(get_async_session),
    end_date: date,
    request: Request,
    start_date: date,
    timeframe: DashboardTimeFilter,
    workspace_db: WorkspaceDB,
) -> None:
    """Retrieve topic modelling insights for the time period specified and write to
    Redis. This function returns `None` since it is called by a background task and
    only ever writes to Redis.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    end_date
        The end date for the time period.
    request
        The request object.
    start_date
        The start date for the time period.
    timeframe
        The timeframe for the time period.
    workspace_db
        The workspace database object.
    """

    redis = request.app.state.redis
    await redis.set(
        f"{workspace_db.workspace_name}_insights_{timeframe}_results",
        TopicsData(
            data=[],
            refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
            status="in_progress",
        ).model_dump_json(),
    )

    step = None
    try:
        step = "Retrieve queries"
        time_period_queries = await get_raw_queries(
            asession=asession,
            end_date=end_date,
            start_date=start_date,
            workspace_id=workspace_db.workspace_id,
        )

        step = "Retrieve contents"
        content_data = await get_raw_contents(
            asession=asession, workspace_id=workspace_db.workspace_id
        )

        topic_output, embeddings_df = await topic_model_queries(
            content_data=content_data,
            query_data=time_period_queries,
            workspace_id=workspace_db.workspace_id,
        )

        step = "Write to Redis"
        embeddings_json = embeddings_df.to_json(orient="split")
        embeddings_key = f"{workspace_db.workspace_name}_embeddings_{timeframe}"
        await redis.set(embeddings_key, embeddings_json)
        await redis.set(
            f"{workspace_db.workspace_name}_insights_{timeframe}_results",
            topic_output.model_dump_json(),
        )
        return
    except Exception as e:  # pylint: disable=W0718
        error_msg = str(e)
        logger.error(error_msg)
        await redis.set(
            f"{workspace_db.workspace_name}_insights_{timeframe}_results",
            TopicsData(
                data=[],
                error_message=error_msg,
                failure_step=step,
                refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
                status="error",
            ).model_dump_json(),
        )


async def retrieve_overview(
    *,
    asession: AsyncSession,
    end_date: date,
    frequency: TimeFrequency,
    start_date: date,
    top_n: int = 4,
    workspace_id: int,
) -> DashboardOverview:
    """Retrieve all question answer statistics.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    end_date
        The ending date for the statistics.
    frequency
        The frequency at which to retrieve the statistics.
    start_date
        The starting date for the statistics.
    top_n
        The number of top content to retrieve.
    workspace_id
        The ID of the workspace to retrieve the statistics for.

    Returns
    -------
    DashboardOverview
        The dashboard overview statistics.
    """

    stats = await get_stats_cards(
        asession=asession,
        end_date=end_date,
        start_date=start_date,
        workspace_id=workspace_id,
    )

    heatmap = await get_heatmap(
        asession=asession,
        end_date=end_date,
        start_date=start_date,
        workspace_id=workspace_id,
    )

    time_series = await get_overview_timeseries(
        asession=asession,
        end_date=end_date,
        frequency=frequency,
        start_date=start_date,
        workspace_id=workspace_id,
    )

    top_content = await get_top_content(
        asession=asession, top_n=top_n, workspace_id=workspace_id
    )

    return DashboardOverview(
        heatmap=heatmap,
        stats_cards=stats,
        time_series=time_series,
        top_content=top_content,
    )


async def retrieve_performance(
    *,
    asession: AsyncSession,
    end_date: date,
    frequency: TimeFrequency,
    start_date: date,
    top_n: int | None,
    workspace_id: int,
) -> DashboardPerformance:
    """Retrieve timeseries data on content usage and performance of each content.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    end_date
        The ending date for the timeseries.
    frequency
        The frequency at which to retrieve the timeseries.
    start_date
        The starting date for the timeseries.
    top_n
        The number of top content to retrieve.
    workspace_id
        The ID of the workspace to retrieve the timeseries for.

    Returns
    -------
    DashboardPerformance
        The dashboard performance timeseries.
    """

    content_time_series = await get_timeseries_top_content(
        asession=asession,
        end_date=end_date,
        frequency=frequency,
        start_date=start_date,
        top_n=top_n,
        workspace_id=workspace_id,
    )
    return DashboardPerformance(content_time_series=content_time_series)
