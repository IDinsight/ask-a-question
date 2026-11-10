"""Business logic for the dashboard.

Sections, in order:
1. Prompts used by the dashboard LLM calls.
2. Time-window helpers shared by the endpoints.
3. Endpoint orchestration (content details, AI summary, performance, overview,
   topic insights and the topic plot).
4. LLM calls (feedback summary, topic labels).
5. Topic modelling (BERTopic pipeline).
6. Bokeh plotting of the topic embeddings.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import textwrap
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Coroutine, Optional, cast

import numpy as np
import pandas as pd
from bokeh.core.types import ID
from bokeh.embed import json_item
from bokeh.embed.standalone import StandaloneEmbedJson
from bokeh.layouts import Spacer, column, row
from bokeh.models import (
    Button,
    CDSView,
    ColumnDataSource,
    CustomJS,
    CustomJSFilter,
    Div,
    FixedTicker,
    HoverTool,
    MultiSelect,
    TextInput,
    WheelZoomTool,
)
from bokeh.palettes import Turbo256
from bokeh.plotting import figure
from dateutil.relativedelta import relativedelta
from langfuse.decorators import langfuse_context, observe  # type: ignore
from pydantic import BaseModel
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

# BERTopic, UMAP, HDBSCAN and SentenceTransformer pull in torch/transformers and add
# about two seconds to start-up, so they are imported inside the functions that
# use them. This import is for type annotations only.
if TYPE_CHECKING:
    from bertopic import BERTopic

from app.core.config import (
    DISABLE_DASHBOARD_LLM,
    LITELLM_MODEL_DASHBOARD_SUMMARY,
    LITELLM_MODEL_TOPIC_MODEL,
    MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY,
    MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT,
    TOPIC_MODELING_CONTEXT,
)
from app.core.database import get_sqlalchemy_async_engine
from app.core.exceptions import BadRequestError, InternalServerError, NotFoundError
from app.core.observability import setup_logger
from app.core.utils import ask_llm_async, remove_json_markdown
from app.dashboard.repository import (
    get_content_details,
    get_content_feedback_texts,
    get_content_title_and_text,
    get_heatmap,
    get_overview_timeseries,
    get_raw_contents,
    get_raw_queries,
    get_stats_cards,
    get_timeseries_top_content,
    get_top_content,
)
from app.dashboard.schemas import (
    AIFeedbackSummary,
    BokehContentItem,
    DashboardOverview,
    DashboardPerformance,
    DashboardTimeFilter,
    DetailsDrawer,
    TimeFrequency,
    Topic,
    TopicsData,
    UserQuery,
)
from app.workspaces.models import WorkspaceDB
from app.workspaces.repository import get_workspace_by_workspace_name

# Silence the HuggingFace tokenizers fork warning raised during topic modelling.
os.environ["TOKENIZERS_PARALLELISM"] = "false"

logger = setup_logger(name="DASHBOARD AI SUMMARY")


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
class TopicModelLabelling:
    """Topic model labelling task."""

    class TopicModelLabellingResult(BaseModel):
        """Pydantic model for the output of the topic model labelling task."""

        topic_summary: str
        topic_title: str

    _context: str

    _prompt_base: str = textwrap.dedent(
        """
        You are a summarization bot designed to condense multiple
        messages into a topic description specific to {context}. You may
        encounter queries that are related to something other than {context}.
        Do your best to describe these too. If there is no common thread at all, respond
        with topic_title as "Unknown" and topic_summary as "Not available".

        When coming up with topic_title, be very concise.
        "topic_summary" should be a summary of the topics found in the
        provided messages. It expands on the topic_title. Restrict it to ONLY
        summarization. Do not include any additional information.
        """
    ).strip()

    _response_prompt: str = textwrap.dedent(
        """
        Respond in json string:

        {
           topic_title: str
           topic_summary: str
        }
        """
    ).strip()

    def __init__(self, *, context: str) -> None:
        """Initialize the topic model labelling task with context.

        Parameters
        ----------
        context
            The context for the topic model labelling task.
        """

        self._context = context

    def get_prompt(self) -> str:
        """Return the prompt for the topic model labelling task.

        Returns
        -------
        str
            The prompt for the topic model labelling task.
        """

        prompt = self._prompt_base.format(context=self._context)

        return prompt + "\n\n" + self._response_prompt

    @staticmethod
    def parse_json(*, json_str: str) -> dict[str, str]:
        """Validate the output of the topic model labelling task.

        Parameters
        ----------
        json_str
            The JSON string to validate.

        Returns
        -------
        dict[str, str]
            The validated JSON response.

        Raises
        ------
        ValueError
            If there is an error validating the output.
        """

        json_str = remove_json_markdown(text=json_str)

        try:
            result = TopicModelLabelling.TopicModelLabellingResult.model_validate_json(
                json_str
            )
        except ValueError as e:
            raise ValueError(f"Error validating the output: {e}") from e

        return result.model_dump()


def get_feedback_summary_prompt(*, content: str, content_title: str) -> str:
    """Return the prompt for the feedback summarization task.

    Parameters
    ----------
    content
        The content.
    content_title
        The title of the content.

    Returns
    -------
    str
        The prompt for the feedback summarization task.
    """

    ai_feedback_summary_prompt = textwrap.dedent(
        """
        The following is a list of feedback provided by the user for a content share
        with them. Summarize the key themes in the list of feedback text into a few
        sentences. Suggest ways to address their feedback where applicable. Your
        response should be no longer than 50 words and NOT be in dot point. Do not
        include headers.

        <CONTENT_TITLE>
        {content_title}
        </CONTENT_TITLE>

        <CONTENT>
        {content}
        </CONTENT>

        """
    ).strip()

    return ai_feedback_summary_prompt.format(
        content=content, content_title=content_title
    )


# ---------------------------------------------------------------------------
# Time-window helpers
# ---------------------------------------------------------------------------
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
    BadRequestError
        If the start and end dates are not provided for a custom timeframe.
        If the frequency is not provided for a custom timeframe.
        If the date format is invalid.
        If the end date is before the start date.
    ValueError
        If the time frequency is invalid.
    """

    now_utc = datetime.now(timezone.utc)
    if timeframe == "custom":
        if not start_date_str or not end_date_str:
            raise BadRequestError(
                "`start_date` and `end_date` are required for custom timeframe."
            )
        if not frequency:
            raise BadRequestError("`frequency` is required for custom timeframe.")

        try:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            raise BadRequestError("Invalid date format; must be YYYY-MM-DD") from None

        if end_dt < start_dt:
            raise BadRequestError("`end_date` must be >= `start_date`")

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


def create_session_id(
    prefix: str, start_dt: date | datetime, end_dt: date | datetime
) -> str:
    """Build a Langfuse session ID for a dashboard time window.

    Parameters
    ----------
    prefix
        The prefix identifying what the session is about.
    start_dt
        The start of the time window.
    end_dt
        The end of the time window.

    Returns
    -------
    str
        `<prefix>-<start>-<end>-<random 4-digit suffix>`.
    """

    return (
        prefix
        + "-"
        + f"{start_dt:%Y%m%d_%H%M%S}-{end_dt:%Y%m%d_%H%M%S}-"
        + f"{random.randint(0, 1000):04}"
    )


# ---------------------------------------------------------------------------
# Endpoint orchestration
# ---------------------------------------------------------------------------
async def get_content_details_for_timeframe(
    *,
    asession: AsyncSession,
    content_id: int,
    end_date: Optional[str],
    start_date: Optional[str],
    timeframe: DashboardTimeFilter,
    workspace_name: str,
) -> DetailsDrawer:
    """Retrieve detailed statistics of a content for a dashboard timeframe.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    content_id
        The ID of the content to retrieve details for.
    end_date
        The end date (YYYY-MM-DD) for a custom timeframe.
    start_date
        The start date (YYYY-MM-DD) for a custom timeframe.
    timeframe
        The time frequency to retrieve details for.
    workspace_name
        The name of the workspace to retrieve details for.

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

    return await get_content_details(
        asession=asession,
        content_id=content_id,
        end_date=end_dt,
        frequency=frequency,
        max_feedback_records=int(MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT),
        start_date=start_dt,
        workspace_id=workspace_db.workspace_id,
    )


async def get_ai_answer_summary(
    *,
    asession: AsyncSession,
    content_id: int,
    end_date: date,
    max_feedback_records: int,
    start_date: date,
    workspace_id: int,
) -> str | None:
    """Get AI answer summary.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    content_id
        The ID of the content to retrieve the summary for.
    end_date
        The ending date for the summary.
    max_feedback_records
        The maximum number of feedback records to retrieve.
    start_date
        The starting date for the summary.
    workspace_id
        The ID of the workspace to retrieve the summary for.

    Returns
    -------
    str | None
        The AI answer summary.

    Raises
    ------
    ValueError
        If the content with the specified ID is not found.
    """

    if DISABLE_DASHBOARD_LLM:
        logger.info("LLM functionality is disabled. Returning default message.")
        return None

    all_feedback = await get_content_feedback_texts(
        asession=asession,
        content_id=content_id,
        end_date=end_date,
        max_feedback_records=max_feedback_records,
        start_date=start_date,
        workspace_id=workspace_id,
    )
    content_row = await get_content_title_and_text(
        asession=asession, content_id=content_id, workspace_id=workspace_id
    )

    if not content_row:
        raise ValueError(
            f"Content with ID '{content_id}' for workspace ID '{workspace_id}' not "
            f"found."
        )

    ai_summary = (
        await generate_ai_summary(
            content_text=content_row.content_text,
            content_title=content_row.content_title,
            feedback=all_feedback,
            workspace_id=workspace_id,
        )
        if all_feedback
        else "No feedback to summarize."
    )

    return ai_summary


async def get_content_ai_summary_for_timeframe(
    *,
    asession: AsyncSession,
    content_id: int,
    end_date: Optional[str],
    start_date: Optional[str],
    timeframe: DashboardTimeFilter,
    workspace_name: str,
) -> AIFeedbackSummary:
    """Summarize the user feedback on a content for a dashboard timeframe.

    Must run inside a Langfuse-observed call: it tags the current trace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    content_id
        The ID of the content to summarize feedback for.
    end_date
        The end date (YYYY-MM-DD) for a custom timeframe.
    start_date
        The start date (YYYY-MM-DD) for a custom timeframe.
    timeframe
        The time frequency to summarize feedback for.
    workspace_name
        The name of the workspace the content belongs to.

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

    langfuse_context.update_current_trace(
        name="content_feedback_summary",
        session_id=create_session_id(
            f"content_{content_id}_feedback", start_dt, end_dt
        ),
        metadata={"content_id": content_id, "workspace_id": workspace_db.workspace_id},
    )

    return AIFeedbackSummary(ai_summary=ai_summary)


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


async def get_performance_for_timeframe(
    *,
    asession: AsyncSession,
    end_date: Optional[str],
    start_date: Optional[str],
    timeframe: DashboardTimeFilter,
    top_n: int | None,
    workspace_name: str,
) -> DashboardPerformance:
    """Retrieve content usage and performance timeseries for a dashboard timeframe.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    end_date
        The end date (YYYY-MM-DD) for a custom timeframe.
    start_date
        The start date (YYYY-MM-DD) for a custom timeframe.
    timeframe
        The time frequency to retrieve performance for.
    top_n
        The number of top content to retrieve.
    workspace_name
        The name of the workspace to retrieve performance for.

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
    return await retrieve_performance(
        asession=asession,
        end_date=end_dt,
        frequency=freq,
        start_date=start_dt,
        top_n=top_n,
        workspace_id=workspace_db.workspace_id,
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


async def get_overview_for_timeframe(
    *,
    asession: AsyncSession,
    end_date: Optional[str],
    frequency: Optional[TimeFrequency],
    start_date: Optional[str],
    timeframe: DashboardTimeFilter,
    workspace_name: str,
) -> DashboardOverview:
    """Retrieve all question answer statistics for a dashboard timeframe.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    end_date
        The end date (YYYY-MM-DD) for a custom timeframe.
    frequency
        The frequency at which to retrieve the statistics (custom timeframe only).
    start_date
        The start date (YYYY-MM-DD) for a custom timeframe.
    timeframe
        The time frequency to retrieve overview for.
    workspace_name
        The name of the workspace to retrieve the overview for.

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
    return await retrieve_overview(
        asession=asession,
        end_date=end_dt,
        frequency=freq,
        start_date=start_dt,
        workspace_id=workspace_db.workspace_id,
    )


async def get_insights_refresh_window(
    *,
    asession: AsyncSession,
    end_date: Optional[str],
    start_date: Optional[str],
    timeframe: DashboardTimeFilter,
    workspace_name: str,
) -> tuple[WorkspaceDB, datetime, datetime]:
    """Resolve the workspace and time window for an insights refresh.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    end_date
        The end date (YYYY-MM-DD) for a custom timeframe.
    start_date
        The start date (YYYY-MM-DD) for a custom timeframe.
    timeframe
        The time frequency to refresh insights for.
    workspace_name
        The name of the workspace to refresh insights for.

    Returns
    -------
    tuple[WorkspaceDB, datetime, datetime]
        The workspace, and the start and end datetimes of the window.
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
    return workspace_db, start_dt, end_dt


@observe()
async def refresh_insights(
    *,
    end_date: date,
    redis: aioredis.Redis,
    start_date: date,
    timeframe: DashboardTimeFilter,
    workspace_db: WorkspaceDB,
) -> None:
    """Retrieve topic modelling insights for the time period specified and write to
    Redis. This function returns `None` since it is called by a background task and
    only ever writes to Redis.

    It opens its own database session because the request-scoped session is closed
    by the time a background task runs.

    Parameters
    ----------
    end_date
        The end date for the time period.
    redis
        The Redis client to write the results to.
    start_date
        The start date for the time period.
    timeframe
        The timeframe for the time period.
    workspace_db
        The workspace database object.
    """

    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        await redis.set(
            f"{workspace_db.workspace_name}_insights_{timeframe}_results",
            TopicsData(
                data=[],
                refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
                status="in_progress",
            ).model_dump_json(),
        )

        # `step` records how far we got so a failure can be reported to the frontend.
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

            langfuse_context.update_current_trace(
                name="topic_modeling",
                session_id=create_session_id("topic_modeling", start_date, end_date),
                metadata={"workspace_id": workspace_db.workspace_id},
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


async def get_insights(
    *,
    asession: AsyncSession,
    redis: aioredis.Redis,
    timeframe: DashboardTimeFilter,
    workspace_name: str,
) -> TopicsData:
    """Read the cached topic modelling insights for a timeframe from Redis.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    redis
        The Redis client holding the cached insights.
    timeframe
        The time frequency to retrieve insights for.
    workspace_name
        The name of the workspace to retrieve insights for.

    Returns
    -------
    TopicsData
        The cached insights, or an empty `not_started` result if no refresh has run.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    key = f"{workspace_db.workspace_name}_insights_{timeframe}_results"
    if await redis.exists(key):
        payload = await redis.get(key)
        parsed_payload = json.loads(payload)
        return TopicsData(**parsed_payload)
    return TopicsData(data=[], refreshTimeStamp="", status="not_started")


async def create_topic_plot(
    *,
    asession: AsyncSession,
    redis: aioredis.Redis,
    timeframe: DashboardTimeFilter,
    workspace_name: str,
) -> StandaloneEmbedJson:
    """Build the Bokeh topic plot from the embeddings cached in Redis.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    redis
        The Redis client holding the cached embeddings.
    timeframe
        The time frequency to plot.
    workspace_name
        The name of the workspace to create the plot for.

    Returns
    -------
    StandaloneEmbedJson
        The Bokeh plot as a JSON object.

    Raises
    ------
    NotFoundError
        If the embeddings data is not found in Redis.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    embeddings_key = f"{workspace_db.workspace_name}_embeddings_{timeframe}"
    embeddings_json = await redis.get(embeddings_key)

    if not embeddings_json:
        raise NotFoundError("Embeddings data not found.")

    df = pd.read_json(embeddings_json.decode("utf-8"), orient="split")
    return produce_bokeh_plot(embeddings_df=df)


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------
async def generate_ai_summary(
    *, content_text: str, content_title: str, feedback: list[str], workspace_id: int
) -> str:
    """Generate AI summary for Page 2 of the dashboard.

    Parameters
    ----------
    content_text
        The text of the content to summarize.
    content_title
        The title of the content to summarize.
    feedback
        The user feedback to provide to the AI.
    workspace_id
        The workspace ID.

    Returns
    -------
    str
        The AI summary.
    """
    ai_feedback_summary_prompt = get_feedback_summary_prompt(
        content=content_text, content_title=content_title
    )

    ai_summary = await ask_llm_async(
        litellm_model=LITELLM_MODEL_DASHBOARD_SUMMARY,
        system_message=ai_feedback_summary_prompt,
        user_message="\n".join(feedback),
    )

    logger.info(f"AI Summary generated for {content_title} with feedback: {feedback}")
    return ai_summary


async def generate_topic_label(
    *,
    context: str,
    sample_texts: list[str],
    topic_id: int,
    topic_model: BERTopic,
    workspace_id: int,
) -> dict[str, str]:
    """Generate topic labels for example queries.

    Parameters
    ----------
    context
        The context of the topic label.
    sample_texts
        The sample texts to use for generating the topic label.
    topic_id
        The topic ID.
    topic_model
        The topic model object.
    workspace_id
        The workspace ID.

    Returns
    -------
    dict[str, str]
        The topic label.
    """

    if topic_id == -1:
        return {"topic_title": "Unclassified", "topic_summary": "Not available."}

    if DISABLE_DASHBOARD_LLM:
        logger.info("LLM functionality is disabled. Generating labels using KeyBERT.")

        # Use KeyBERT-inspired method to generate topic labels.
        # Assume topic_model is provided.
        topic_info = topic_model.get_topic(topic_id)
        if not topic_info:
            logger.warning(f"No topic info found for topic_id {topic_id}.")
            return {"topic_title": "Unknown", "topic_summary": "Not available."}

        # Extract top keywords.
        top_keywords = [word for word, _ in topic_info]
        topic_title = ", ".join(top_keywords[:3])  # Use top 3 keywords as title

        # Use all keywords as summary.
        # Line formatting looks odd since 'pre-wrap' is enabled on the frontend.
        topic_summary = f"""{" ".join(top_keywords)}

Hint: To enable full AI summaries please set the DASHBOARD_LLM environment variable to "True" in your configuration."""  # noqa: E501
        logger.info(
            f"Generated topic label for topic_id {topic_id} using basic keywords."
        )
        return {"topic_title": topic_title, "topic_summary": topic_summary}

    # If LLM is enabled, proceed with LLM-based label generation.
    topic_model_labelling = TopicModelLabelling(context=context)

    combined_texts = "\n".join(
        [f"{i}. {text}" for i, text in enumerate(sample_texts, 1)]
    )

    topic_json = await ask_llm_async(
        json_=True,
        litellm_model=LITELLM_MODEL_TOPIC_MODEL,
        system_message=topic_model_labelling.get_prompt(),
        user_message=combined_texts,
    )

    try:
        topic = topic_model_labelling.parse_json(json_str=topic_json)
    except ValueError as e:
        logger.warning(
            (
                f"Error generating topic label for {context}: {e}. "
                "Setting topic to 'Unknown'"
            )
        )
        topic = {"topic_title": "Unknown", "topic_summary": "Not available."}

    logger.info(f"Topic label generated for {context}: {topic}")
    return topic


# ---------------------------------------------------------------------------
# Topic modelling
# ---------------------------------------------------------------------------
def add_reduced_embeddings(*, results_df: pd.DataFrame, topic_model: BERTopic) -> None:
    """Add reduced embeddings (2D) to the results DataFrame.

    Parameters
    ----------
    results_df
        A DataFrame containing the topic modeling results.
    topic_model
        A fitted BERTopic model.
    """

    reduced_embeddings = topic_model.umap_model.embedding_
    results_df["x"] = reduced_embeddings[:, 0]
    results_df["y"] = reduced_embeddings[:, 1]


def fit_topic_model(*, embeddings: np.ndarray, texts: list[str]) -> BERTopic:
    """Fit a BERTopic model on the provided texts and embeddings.

    Parameters
    ----------
    embeddings
        An array of embeddings for the provided texts.
    texts
        A list of strings to fit the topic model on.

    Returns
    -------
    BERTopic
        A fitted BERTopic model.
    """

    # Heavy imports, done lazily (see the note at the top of the module).
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from umap import UMAP

    umap_model = UMAP(
        metric="cosine", min_dist=0.0, n_components=2, n_neighbors=15, random_state=42
    )
    hdbscan_model = HDBSCAN(
        cluster_selection_method="eom",
        metric="euclidean",
        min_cluster_size=20,
        prediction_data=True,
    )
    topic_model = BERTopic(
        calculate_probabilities=True,
        hdbscan_model=hdbscan_model,
        umap_model=umap_model,
        verbose=False,
    )
    topic_model.fit(texts, embeddings)

    return topic_model


def generate_embeddings(*, texts: list[str]) -> np.ndarray:
    """Generate embeddings for the provided texts using SentenceTransformer.

    Parameters
    ----------
    texts
        A list of strings to generate embeddings for.

    Returns
    -------
    np.ndarray
        An array of embeddings for the provided texts.
    """

    # Heavy import, done lazily (see the note at the top of the module).
    from sentence_transformers import SentenceTransformer

    sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings_any = sentence_model.encode(
        texts, convert_to_numpy=True, convert_to_tensor=False, show_progress_bar=False
    )
    embeddings = cast(np.ndarray, embeddings_any)  # Needed for mypy issues
    return embeddings


async def generate_topic_labels_async(
    *, results_df: pd.DataFrame, topic_model: BERTopic, workspace_id: int
) -> dict[int, dict[str, str]]:
    """Generate topic labels asynchronously using an LLM or alternative method.

    Parameters
    ----------
    results_df
        A DataFrame containing the topic modeling results.
    topic_model
        A fitted BERTopic model.
    workspace_id
        The ID of the workspace.

    Returns
    -------
    dict[int, dict[str, str]]
        A dictionary mapping topic IDs to their labels.
    """

    tasks: list[Coroutine[Any, Any, dict[str, str]]] = []
    topic_ids: list[int] = []

    # Ensure `topic_id` is integer type.
    results_df["topic_id"] = results_df["topic_id"].astype(int)

    # Group by `topic_id`.
    grouped = results_df.groupby("topic_id")
    for topic_id_any, topic_df in grouped:
        topic_id = cast(int, topic_id_any)  # For type checking
        if topic_id == -1:  # Skip noise/unclassified topics
            continue

        # Get top 5 query samples for the topic.
        topic_queries = topic_df[topic_df["type"] == "query"]["text"].head(5).tolist()

        # Create task for generating topic label.
        topic_id_int = int(topic_id)
        tasks.append(
            generate_topic_label(
                context=TOPIC_MODELING_CONTEXT,
                sample_texts=topic_queries,
                topic_id=topic_id_int,
                topic_model=topic_model,
                workspace_id=workspace_id,
            )
        )
        topic_ids.append(topic_id_int)

    # Run tasks concurrently if there are tasks.
    topic_dicts = await asyncio.gather(*tasks) if tasks else []

    # Map `topic_ids` to `topic_dicts`.
    topic_labels = dict(zip(topic_ids, topic_dicts, strict=False))

    # Logging for debugging.
    logger.debug(f"Generated topic_labels: {topic_labels}")

    return topic_labels


def get_topic_title(*, row: pd.Series, topic_labels: dict[int, dict[str, str]]) -> str:
    """Get the topic title for a given row.

    Parameters
    ----------
    row
        A row from the DataFrame.
    topic_labels
        A dictionary mapping topic IDs to their labels.

    Returns
    -------
    str
        The topic title for the given row.
    """

    if row["topic_id"] == -1:
        return "Unclassified"
    if row["type"] == "content":
        return "Content"
    return topic_labels.get(row["topic_id"], {}).get("topic_title", "Unknown Topic")


def prepare_dataframes(
    *, content_data: list[BokehContentItem], query_data: list[UserQuery]
) -> pd.DataFrame:
    """Prepare a unified dataframe combining queries and content data.

    Parameters
    ----------
    content_data
        A list of `BokehContentItem` objects containing content data.
    query_data
        A list of `UserQuery` objects containing the raw queries and their datetime
        stamps.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the combined data from queries and content.
    """

    # Convert to DataFrames.
    content_df = pd.DataFrame.from_records([x.model_dump() for x in content_data])
    content_df["type"] = "content"

    query_df = pd.DataFrame.from_records([x.model_dump() for x in query_data])
    query_df["type"] = "query"
    query_df["query_datetime_utc"] = query_df["query_datetime_utc"].astype(str)

    # Combine queries and content.
    full_texts = query_df["query_text"].tolist() + content_df["content_text"].tolist()
    types = query_df["type"].tolist() + content_df["type"].tolist()
    datetimes = query_df["query_datetime_utc"].tolist() + [""] * len(content_df)

    # Create combined DataFrame.
    results_df = pd.DataFrame(
        {"text": full_texts, "type": types, "datetime": datetimes}
    )

    return results_df


def prepare_topics_data(
    *, results_df: pd.DataFrame, topic_labels: dict[int, dict[str, str]]
) -> TopicsData:
    """Prepare the `TopicsData` object for the frontend.

    Parameters
    ----------
    results_df
        A DataFrame containing the topic modeling results.
    topic_labels
        A dictionary mapping topic IDs to their labels.

    Returns
    -------
    TopicsData
        A `TopicsData` object containing the topics and their details.
    """

    topics_list = []

    # Group by `topic_id`.
    grouped = results_df.groupby("topic_id")

    for topic_id_any, topic_df in grouped:
        topic_id = cast(int, topic_id_any)  # For type checking
        only_queries = topic_df[topic_df["type"] == "query"]

        # Collect unclassified queries.
        if topic_id == -1:
            continue

        # Get topic information.
        topic_dict = topic_labels.get(
            topic_id, {"topic_title": "Unknown", "topic_summary": ""}
        )

        # Get topic samples.
        topic_samples_slice = only_queries[["text", "datetime"]].head(20)
        string_topic_samples = [
            {
                "query_text": str(sample["text"]),
                "query_datetime_utc": str(sample["datetime"]),
            }
            for sample in topic_samples_slice.to_dict(orient="records")
        ]

        # Create the `Topic` object.
        topic = Topic(
            topic_id=int(topic_id),
            topic_name=topic_dict["topic_title"],
            topic_popularity=len(only_queries),
            topic_samples=string_topic_samples,
            topic_summary=topic_dict["topic_summary"],
        )
        topics_list.append(topic)

    # Sort topics by popularity.
    topics_list = sorted(topics_list, key=lambda x: -x.topic_popularity)

    # Prepare `TopicsData` object.
    topics_data = TopicsData(
        data=topics_list,
        refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
        status="completed",
    )

    return topics_data


async def topic_model_queries(
    *,
    content_data: list[BokehContentItem],
    query_data: list[UserQuery],
    workspace_id: int,
) -> tuple[TopicsData, pd.DataFrame]:
    """Perform topic modeling on user queries and content data.

    Parameters
    ----------
    content_data
        A list of `BokehContentItem` objects containing content data.
    query_data
        A list of `UserQuery` objects containing the raw queries and their datetime
        stamps.
    workspace_id
        The ID of the workspace.

    Returns
    -------
    tuple[TopicsData, pd.DataFrame]
        A tuple containing `TopicsData` objects for the frontend and a DataFrame with
        embeddings.
    """

    if not query_data:
        logger.warning("No queries to cluster")
        return (
            TopicsData(
                data=[],
                error_message="No queries to cluster",
                failure_step="Run topic modeling",
                refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
                status="error",
            ),
            pd.DataFrame(),
        )

    if not content_data:
        logger.warning("No content data to cluster")
        return (
            TopicsData(
                data=[],
                error_message="No content data to cluster",
                failure_step="Run topic modeling",
                refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
                status="error",
            ),
            pd.DataFrame(),
        )

    n_queries = len(query_data)
    n_contents = len(content_data)

    if not sum([n_queries, n_contents]) >= 500:
        logger.warning("Not enough data to cluster")
        return (
            TopicsData(
                data=[],
                error_message="""Not enough data to cluster.
                Please provide at least 500 total queries and content items.""",
                failure_step="Run topic modeling",
                refreshTimeStamp=datetime.now(timezone.utc).isoformat(),
                status="error",
            ),
            pd.DataFrame(),
        )

    # Prepare dataframes.
    results_df = prepare_dataframes(content_data=content_data, query_data=query_data)

    # Generate embeddings.
    embeddings = generate_embeddings(texts=results_df["text"].tolist())

    # Fit the BERTopic model.
    topic_model = fit_topic_model(
        embeddings=embeddings, texts=results_df["text"].tolist()
    )

    # Transform documents to get topics and probabilities.
    topics, _ = topic_model.transform(results_df["text"], embeddings)
    results_df["topic_id"] = topics

    # Add reduced embeddings (for visualization).
    add_reduced_embeddings(results_df=results_df, topic_model=topic_model)

    # Generate topic labels using LLM or alternative method.
    topic_labels = await generate_topic_labels_async(
        results_df=results_df, topic_model=topic_model, workspace_id=workspace_id
    )

    # Add topic titles to the dataFrame.
    results_df["topic_title"] = results_df.apply(
        lambda row: get_topic_title(row=row, topic_labels=topic_labels), axis=1
    )

    # Prepare `TopicsData` for frontend.
    topics_data = prepare_topics_data(results_df=results_df, topic_labels=topic_labels)

    return topics_data, results_df


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
# pylint: disable=R0915
def produce_bokeh_plot(*, embeddings_df: pd.DataFrame) -> StandaloneEmbedJson:
    """Create a Bokeh plot with queries and content points, and a Div to display
    selected points organized by topic, handling duplicate topic titles by using
    `topic_id`.

    Parameters
    ----------
    embeddings_df
        Dataframe containing the embeddings data.

    Returns
    -------
    StandaloneEmbedJson
        The Bokeh plot as a JSON object.

    Raises
    ------
    InternalServerError
        If the embeddings data is missing required columns.
    """

    # Ensure required columns are present.
    required_columns = ["x", "y", "text", "type", "topic_title", "topic_id"]
    if not all(col in embeddings_df.columns for col in required_columns):
        raise InternalServerError("Embeddings data missing required columns.")

    # Capitalize 'type' column and create 'display_text' column.
    embeddings_df["type"] = embeddings_df["type"].str.capitalize()
    embeddings_df["display_text"] = embeddings_df.apply(
        lambda row_: (
            row_["text"] if row_["type"] == "Query" else f"[Content] {row_['text']}"
        ),
        axis=1,
    )

    # Ensure 'Content' entries have 'topic_title' == 'Content' and 'topic_id' == -2.
    embeddings_df.loc[
        embeddings_df["type"].str.lower() == "content",
        ["topic_id", "topic_title"],
    ] = [-2, "Content"]

    # Combine 'Unknown' topics with 'Unclassified', excluding 'Content' entries.
    embeddings_df.loc[
        (embeddings_df["topic_title"].str.lower() == "unknown")
        & (embeddings_df["type"] != "Content"),
        ["topic_id", "topic_title"],
    ] = [-1, "Unclassified"]

    # Define special topics.
    special_topics = ["Content"]  # 'Content' is the only special topic now

    # Make 'Unclassified' and 'Content' topics semi-transparent.
    embeddings_df["alpha"] = embeddings_df["topic_title"].apply(
        lambda t: 0.6 if t.lower() in ["unclassified", "content"] else 1.0
    )

    # Make 'Unclassified' and 'Content' topics gray, everything else blue.
    embeddings_df["color"] = embeddings_df["topic_title"].apply(
        lambda t: "gray" if t.lower() in ["unclassified", "content"] else "blue"
    )

    # Identify known topics excluding special topics and 'Unclassified'
    # (topic_id == -1).
    known_topics_df = embeddings_df[
        (
            ~embeddings_df["topic_title"]
            .str.lower()
            .isin([t.lower() for t in special_topics])
        )
        & (embeddings_df["topic_id"] != -1)
    ][["topic_title", "topic_id"]].drop_duplicates()

    known_topics = known_topics_df["topic_id"].tolist()

    # Assign colors to known topics.
    palette = Turbo256  # Full spectrum color palette
    random.seed(42)  # Set seed for reproducibility between re-rendering plot

    if len(known_topics) <= len(palette):
        topic_colors = random.sample(palette, len(known_topics))
    else:
        # If there are more topics than palette colors, cycle through the palette.
        topic_colors = [palette[i % len(palette)] for i in range(len(known_topics))]

    topic_color_map = dict(zip(known_topics, topic_colors))

    # Map colors to embeddings_df based on topic_id, excluding 'Unclassified' (-1).
    embeddings_df.loc[embeddings_df["topic_id"].isin(known_topics), "color"] = (
        embeddings_df["topic_id"].map(topic_color_map)
    )

    # Exclude 'Content' from `topic_counts`.
    topic_counts = (
        embeddings_df[~embeddings_df["topic_title"].str.lower().isin(["content"])]  # type: ignore
        .groupby(["topic_id", "topic_title"])
        .size()
        .reset_index(name="counts")
    )

    # Sort topics by popularity (descending), but place 'Unclassified' at the top.
    is_unclassified = topic_counts["topic_title"].str.lower() == "unclassified"
    sorted_topics = pd.concat(
        [
            topic_counts[is_unclassified],
            topic_counts[~is_unclassified].sort_values(by="counts", ascending=False),
        ],
        ignore_index=True,
    )

    # Prepare MultiSelect options and mappings.
    topic_options = [
        (str(topic_id), f"{title} ({count})")
        for topic_id, title, count in zip(
            sorted_topics["topic_id"],
            sorted_topics["topic_title"],
            sorted_topics["counts"],
        )
    ]

    # Extract topic IDs, excluding 'Content'.
    unique_topic_ids = sorted_topics["topic_id"].tolist()

    # Separate queries and content.
    query_df = embeddings_df[embeddings_df["type"] == "Query"]
    content_df = embeddings_df[embeddings_df["type"] == "Content"]

    # Create ColumnDataSources for queries and content.
    source_queries = ColumnDataSource(query_df)
    source_content = ColumnDataSource(content_df)

    # Create MultiSelect widget for topic selection.
    multi_select = MultiSelect(
        value=[str(tid) for tid in unique_topic_ids],  # All topics selected by default
        options=topic_options,
        width=360,
        height=600,
    )

    # Add TextInput widgets for content and query search.
    content_search_input = TextInput(value="", title="Search Content:", width=300)
    query_search_input = TextInput(value="", title="Search Queries:", width=300)

    # Create combined filter for queries.
    queries_filter = CustomJSFilter(
        args={"multi_select": multi_select, "search_input": query_search_input},
        code="""
        const indices = [];
        const data = source.data;
        const topics = data['topic_id'];
        const texts = data['text'];
        const selected_topics = multi_select.value.map(Number);
        const search_value = search_input.value.toLowerCase();

        for (let i = 0; i < topics.length; i++) {
            const topic_id = topics[i];
            const text = texts[i].toLowerCase();
            const text_match = text.includes(search_value);
            const topic_match = selected_topics.includes(topic_id);
            if (topic_match && text_match) {
                indices.push(true);
            } else {
                indices.push(false);
            }
        }
        return indices;
    """,
    )

    # Create modified filter for content to always include 'Content' points.
    content_filter = CustomJSFilter(
        args={"multi_select": multi_select, "search_input": content_search_input},
        code="""
        const indices = [];
        const data = source.data;
        const topics = data['topic_id'];
        const texts = data['text'];
        const search_value = search_input.value.toLowerCase();

        for (let i = 0; i < topics.length; i++) {
            const topic_id = topics[i];
            const text = texts[i].toLowerCase();
            const text_match = text.includes(search_value);
            // Include 'Content' points regardless of topic selection
            if (topic_id === -2 && text_match) {
                indices.push(true);
            } else {
                const selected_topics = multi_select.value.map(Number);
                const topic_match = selected_topics.includes(topic_id);
                if (topic_match && text_match) {
                    indices.push(true);
                } else {
                    indices.push(false);
                }
            }
        }
        return indices;
    """,
    )

    # Create views for queries and content using combined filters.
    view_queries = CDSView(filter=queries_filter)
    view_content = CDSView(filter=content_filter)

    # Attach 'js_on_change' to trigger re-render for queries when topic selection or
    # query search input changes.
    multi_select.js_on_change(
        "value",
        CustomJS(
            args={"source_queries": source_queries, "source_content": source_content},
            code="""
            source_queries.change.emit();
            source_content.change.emit();
        """,
        ),
    )

    query_search_input.js_on_change(
        "value",
        CustomJS(
            args={"source_queries": source_queries},
            code="""
            source_queries.change.emit();
            """,
        ),
    )

    content_search_input.js_on_change(
        "value",
        CustomJS(
            args={"source_content": source_content},
            code="""
            source_content.change.emit();
            """,
        ),
    )

    # Create the plot.
    plot = figure(height=610, tools="pan,wheel_zoom,reset,lasso_select", width=750)

    # Set the wheel zoom tool as the active scroll tool.
    wheel_zoom = plot.select_one({"type": WheelZoomTool})
    plot.toolbar.active_scroll = wheel_zoom

    # Adjust plot appearance.
    plot.xaxis.visible = False  # Remove x-axis numbers
    plot.yaxis.visible = False  # Remove y-axis numbers
    plot.xgrid.grid_line_color = "lightgray"  # Keep x-grid lines visible
    plot.ygrid.grid_line_color = "lightgray"  # Keep y-grid lines visible

    # Add more frequent ticks every 3 units.
    plot.xaxis.ticker = FixedTicker(ticks=list(range(-100, 101, 3)))
    plot.yaxis.ticker = FixedTicker(ticks=list(range(-100, 101, 3)))

    # Add query points as circles.
    query_renderer = plot.circle(
        "x",
        "y",
        size=6,
        color="color",
        source=source_queries,
        view=view_queries,
        legend_label="Queries",
        alpha="alpha",
        selection_line_color="black",
        selection_line_width=2,
        nonselection_alpha=0.3,  # Set non-selected points alpha to 0.3
    )

    # Add content points as hollow squares with updated `view_content`.
    content_renderer = plot.square(
        "x",
        "y",
        size=13,
        line_color="black",
        fill_alpha=0,
        color="color",
        source=source_content,
        view=view_content,
        legend_label="Content",
        alpha="alpha",
        selection_line_color="black",
        selection_line_width=2,
        nonselection_alpha=0.3,  # Set non-selected points alpha to 0.3
    )

    # Adjust legend.
    plot.legend.location = "top_left"
    plot.legend.click_policy = "hide"

    # Configure hover tool with styling to wrap long text.
    hover = HoverTool(
        tooltips="""
        <div style="width:300px; white-space: normal;">
            <b>Text:</b> @display_text <br>
            <b>Topic:</b> @topic_title
        </div>
        """,
        renderers=[query_renderer, content_renderer],
    )
    plot.add_tools(hover)

    # Create a Div to display aggregated selected points organized by topic.
    div = Div(
        styles={"white-space": "pre-wrap", "overflow-y": "auto"},
        sizing_mode="stretch_width",
        height=350,  # Reduced height by ~30%
    )

    # JavaScript code to synchronize selection and update Div.
    sync_selection_code = """
        const indices_queries = source_queries.selected.indices;
        const indices_content = source_content.selected.indices;

        const data_queries = source_queries.data;
        const data_content = source_content.data;

        // Aggregate selected points by topic
        let topics = {};
        // Process selected queries
        for (let i of indices_queries) {
            const topic = data_queries['topic_title'][i];
            const query = data_queries['display_text'][i];
            if (!(topic in topics)) {
                topics[topic] = [];
            }
            topics[topic].push(query);
        }
        // Process selected content
        for (let i of indices_content) {
            const topic = data_content['topic_title'][i];
            const query = data_content['display_text'][i];
            if (!(topic in topics)) {
                topics[topic] = [];
            }
            topics[topic].push(query);
        }
        // Build HTML content
        let content = "";
        for (let topic in topics) {
            content += "<b>" + topic + "</b><br>";
            for (let q of topics[topic]) {
                content += q + "<br>";
            }
            content += "<br>";
        }
        div.text = content;
    """

    # Attach callbacks to synchronize selections.
    sync_selection_callback = CustomJS(
        args={
            "div": div,
            "source_content": source_content,
            "source_queries": source_queries,
        },
        code=sync_selection_code,
    )

    for source in [source_queries, source_content]:
        source.selected.js_on_change("indices", sync_selection_callback)

    # Create 'Select All' and 'Deselect All' buttons for topics.
    select_all_button = Button(label="Select All", width=100, height=30)
    deselect_all_button = Button(label="Deselect All", width=100, height=30)

    # JavaScript callbacks for the buttons.
    select_all_callback = CustomJS(
        args={"multi_select": multi_select},
        code=f"""
        multi_select.value = {[str(tid) for tid in unique_topic_ids]};
        multi_select.change.emit();
    """,
    )
    select_all_button.js_on_click(select_all_callback)

    deselect_all_callback = CustomJS(
        args={"multi_select": multi_select},
        code="""
        multi_select.value = [];
        multi_select.change.emit();
    """,
    )
    deselect_all_button.js_on_click(deselect_all_callback)

    # Create the left column: Buttons and Scrollable topics.
    left_column = column(
        Div(text="<b>Topics:</b>", margin=(0, 0, 0, 0)),
        row(select_all_button, deselect_all_button, sizing_mode="fixed"),
        Spacer(height=13),  # Padding so that layout looks neatest
        multi_select,
    )

    # Create the search bars row.
    search_bars = column(
        row(
            content_search_input,
            Spacer(width=104),  # For padding purposes again
            query_search_input,
            sizing_mode="stretch_width",
            margin=(0, 0, 11, 0),
        ),
    )

    # Create the right column: Search bars and plot.
    right_column = column(search_bars, plot)

    # Combine the left and right columns into the top layout.
    top_layout = row(left_column, right_column, sizing_mode="stretch_width")

    # Create the data table (Div) with full width below the top layout.
    div_layout = column(
        Div(
            text="<h4>Selected points (use the lasso tool to populate this table)</h4>",
            styles={"text-align": "center"},
        ),
        div,
        sizing_mode="stretch_width",
    )

    # Create the overall layout
    layout = column(top_layout, div_layout, sizing_mode="stretch_width")

    return json_item(layout, ID("myplot"))
