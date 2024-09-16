"""This module contains the FastAPI router for the dashboard endpoints."""

import json
import random
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal, Tuple

import pandas as pd
from bokeh.embed import json_item
from bokeh.layouts import column, row
from bokeh.models import (
    CheckboxGroup,
    ColumnDataSource,
    CustomJS,
    DataTable,
    HoverTool,
    TableColumn,
    WheelZoomTool,
)
from bokeh.palettes import Turbo256
from bokeh.plotting import figure
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
        embeddings_dataframe={},
    )


@router.get("/bokeh", response_model=dict)
async def create_plot(request: Request) -> dict:
    """Creates a Bokeh plot based on embeddings data retrieved from Redis."""
    # Get Redis client
    redis = request.app.state.redis

    # Define the Redis key
    embeddings_key = "admin_embeddings_week"

    # Get the embeddings JSON from Redis
    embeddings_json = await redis.get(embeddings_key)
    if embeddings_json is None:
        # Handle missing data
        raise HTTPException(status_code=404, detail="Embeddings data not found")

    # Decode and parse the JSON
    embeddings_json = embeddings_json.decode("utf-8")
    embeddings_df = pd.read_json(embeddings_json, orient="split")
    embeddings_df["type"] = embeddings_df["type"].str.capitalize()

    # Ensure required columns are present
    required_columns = ["x_coord", "y_coord", "text", "type", "topic_title"]
    if not all(col in embeddings_df.columns for col in required_columns):
        raise HTTPException(
            status_code=500, detail="Embeddings data missing required columns"
        )

    # Assign 'grey' color to 'Unknown' or 'Unclassified' topics
    embeddings_df["color"] = "grey"  # Default color
    unknown_topics = ["Unknown", "Unclassified"]
    # Identify known topics
    known_topics = embeddings_df[
        ~embeddings_df["topic_title"]
        .str.lower()
        .isin([t.lower() for t in unknown_topics])
    ]["topic_title"].unique()

    # Randomly assign colors to known topics
    palette = Turbo256  # Full spectrum color palette
    random.seed(42)  # Set seed for reproducibility
    topic_colors = random.sample(palette, len(known_topics))
    topic_color_map = dict(zip(known_topics, topic_colors))

    # Map colors to embeddings_df
    embeddings_df.loc[embeddings_df["topic_title"].isin(known_topics), "color"] = (
        embeddings_df["topic_title"].map(topic_color_map)
    )

    # Create data sources
    # Filter queries
    query_df = embeddings_df[embeddings_df["type"] == "Query"]
    # Filter contents
    content_df = embeddings_df[embeddings_df["type"] == "Content"]

    # Create ColumnDataSource for queries
    source_queries = ColumnDataSource(
        data=dict(
            x=query_df["x_coord"],
            y=query_df["y_coord"],
            color=query_df["color"],
            text=query_df["text"].tolist(),
            type=query_df["type"].tolist(),
            topic_title=query_df["topic_title"].tolist(),
        )
    )

    # Create ColumnDataSource for content
    source_content = ColumnDataSource(
        data=dict(
            x=content_df["x_coord"],
            y=content_df["y_coord"],
            color=content_df["color"],
            text=content_df["text"].tolist(),
            type=content_df["type"].tolist(),
            topic_title=content_df["topic_title"].tolist(),
        )
    )

    # Create a figure with LassoSelectTool
    plot = figure(
        width=700,
        height=500,
        tools="pan,wheel_zoom,reset,lasso_select",
        title="Embeddings Visualization",
        x_axis_label="X Coordinate",
        y_axis_label="Y Coordinate",
    )

    wheel_zoom = plot.select_one(WheelZoomTool)
    plot.toolbar.active_scroll = wheel_zoom

    # Add query points as circles with size units in data coordinates
    query_renderer = plot.circle(
        "x",
        "y",
        size=8,  # Adjust size based on your data range
        color="color",
        source=source_queries,
        legend_label="Queries",
        alpha=0.7,
    )

    # Add content points as squares with size units in data coordinates,
    # initially invisible
    content_renderer = plot.square(
        "x",
        "y",
        size=15,  # Adjust size based on your data range
        color="navy",
        source=source_content,
        visible=False,
        legend_label="Content",
        alpha=1.0,
    )

    # Adjust legend
    plot.legend.location = "top_left"
    plot.legend.click_policy = "hide"

    # Checkbox group to toggle content points visibility
    checkbox = CheckboxGroup(labels=["Show content cards"])

    # Callback to toggle the visibility of content points
    checkbox_callback = CustomJS(
        args=dict(content_renderer=content_renderer),
        code="""
        content_renderer.visible = cb_obj.active.includes(0);
    """,
    )

    # Attach the callback to the checkbox group
    checkbox.js_on_change("active", checkbox_callback)

    # Add hover tool to display text and cluster information
    hover = HoverTool(
        tooltips=[
            ("Text", "@text"),
            ("Type", "@type"),
            ("Topic", "@topic_title"),
        ],
        renderers=[query_renderer, content_renderer],
    )
    plot.add_tools(hover)

    # DataTable to display selected points
    columns = [
        TableColumn(field="text", title="Text"),
        TableColumn(field="type", title="Type"),
        TableColumn(field="topic_title", title="Topic"),
    ]
    data_table_source = ColumnDataSource(data=dict(text=[], type=[], topic_title=[]))
    data_table = DataTable(
        source=data_table_source,
        columns=columns,
        width=500,
        height=500,
        selectable=True,
    )

    # JavaScript code to synchronize selection and update DataTable
    sync_selection_code = """
        // Synchronize selections between query and content sources
        const indices = [];
        for (let i = 0; i < source_queries.selected.indices.length; i++) {
            indices.push(source_queries.selected.indices[i]);
        }
        for (let i = 0; i < source_content.selected.indices.length; i++) {
            indices.push(source_content.selected.indices[i]);
        }

        // Update DataTable
        const d_out = data_table_source.data;
        d_out['text'] = [];
        d_out['type'] = [];
        d_out['topic_title'] = [];

        // Add selected query data
        for (let i of source_queries.selected.indices) {
            d_out['text'].push(source_queries.data['text'][i]);
            d_out['type'].push(source_queries.data['type'][i]);
            d_out['topic_title'].push(source_queries.data['topic_title'][i]);
        }
        // Add selected content data
        for (let i of source_content.selected.indices) {
            d_out['text'].push(source_content.data['text'][i]);
            d_out['type'].push(source_content.data['type'][i]);
            d_out['topic_title'].push(source_content.data['topic_title'][i]);
        }
        data_table_source.change.emit();
    """

    # Attach callbacks to synchronize selections
    source_queries.selected.js_on_change(
        "indices",
        CustomJS(
            args=dict(
                source_queries=source_queries,
                source_content=source_content,
                data_table_source=data_table_source,
            ),
            code=sync_selection_code,
        ),
    )

    source_content.selected.js_on_change(
        "indices",
        CustomJS(
            args=dict(
                source_queries=source_queries,
                source_content=source_content,
                data_table_source=data_table_source,
            ),
            code=sync_selection_code,
        ),
    )

    # Ensure that selection tools affect both data sources
    plot.renderers.extend([query_renderer, content_renderer])

    # Layout the components
    layout = column(row(plot, data_table), checkbox)

    return json_item(layout, "myplot")
