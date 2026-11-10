"""Cross-cutting observability: logging, Prometheus metrics, Sentry and Langfuse."""

import logging
from logging import Logger
from typing import Callable, Optional

import litellm
import sentry_sdk
from fastapi.requests import Request
from langfuse.decorators import langfuse_context  # type: ignore
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    make_asgi_app,
    multiprocess,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import (
    LANGFUSE,
    LOG_LEVEL,
    SENTRY_DSN,
    SENTRY_TRACES_SAMPLE_RATE,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Prometheus middleware for FastAPI."""

    def __init__(self, app: ASGIApp) -> None:
        """This middleware will collect metrics about requests made to the application
        and expose them on the `/metrics` endpoint.

        Parameters
        ----------
        app
            The FastAPI application instance.
        """

        super().__init__(app)
        self.counter = Counter(
            "requests",
            "Number of requests served, by http code",
            ["method", "code", "endpoint"],
        )
        self.histogram = Histogram(
            "durations_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Collect metrics about requests made to the application.

        Parameters
        ----------
         request
             The incoming request.
         call_next
             The next middleware in the chain.

         Returns
         -------
         Response
             The response to the incoming request.
        """

        if request.url.path == "/metrics":
            return await call_next(request)

        with self.histogram.labels(
            method=request.method, endpoint=request.url.path
        ).time():
            response = await call_next(request)

        self.counter.labels(
            method=request.method, code=response.status_code, endpoint=request.url.path
        ).inc()

        return response


# To prefix trace_id with project name.
LANGFUSE_PROJECT_NAME = None

if LANGFUSE == "True":
    langFuseLogger = litellm.utils.langFuseLogger
    if langFuseLogger is not None:
        try:
            LANGFUSE_PROJECT_NAME = (
                langFuseLogger.Langfuse.client.projects.get().data[0].name
            )
        except Exception as e:
            print(f"Failed to get Langfuse project name: {e}")
            LANGFUSE_PROJECT_NAME = None















def create_langfuse_metadata(
    *,
    feature_name: str | None = None,
    query_id: int | None = None,
    session_id: int | None = None,
    workspace_id: int | None = None,
) -> dict:
    """Create metadata for langfuse logging.

    Parameters
    ----------
    feature_name
        The name of the feature.
    query_id
        The ID of the query.
    session_id
        The ID of the session if it exists.
    workspace_id
        The ID of the workspace.

    Returns
    -------
    dict
        The metadata for langfuse logging.

    Raises
    ------
    ValueError
        If neither `query_id` nor `feature_name` is provided.
    """
    metadata = {}

    metadata["trace_id"] = langfuse_context.get_current_trace_id()

    if session_id is not None:
        metadata["session_id"] = session_id

    return metadata


def get_log_level_from_str(*, log_level_str: str = LOG_LEVEL) -> int:
    """Get log level from string.

    Parameters
    ----------
    log_level_str
        The log level string.

    Returns
    -------
    int
        The log level.
    """

    log_level_dict = {
        "CRITICAL": logging.CRITICAL,
        "DEBUG": logging.DEBUG,
        "ERROR": logging.ERROR,
        "INFO": logging.INFO,
        "NOTSET": logging.NOTSET,
        "WARNING": logging.WARNING,
    }

    return log_level_dict.get(log_level_str.upper(), logging.INFO)


def setup_logger(*, log_level: Optional[int] = None, name: str = __name__) -> Logger:
    """Setup logger for the application.

    Parameters
    ----------
    log_level
        The log level for the logger.
    name
        The name of the logger.

    Returns
    -------
    Logger
        The configured logger.
    """

    log_level = log_level or get_log_level_from_str()
    logger = logging.getLogger(name)

    # If the logger already has handlers, assume it was already configured and return
    # it.
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s %(filename)20s%(lineno)4s : %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )

    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


def create_metrics_app() -> Callable:
    """Create the Prometheus metrics ASGI app (multiprocess-aware for gunicorn).

    Returns
    -------
    Callable
        The metrics app, mounted at `/metrics` by `app.main.create_app`.
    """

    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return make_asgi_app(registry=registry)


def init_langfuse() -> None:
    """Route LiteLLM success/failure callbacks to Langfuse when `LANGFUSE=True`."""

    if LANGFUSE == "True":
        setup_logger().info("Setting up langfuse callbacks")
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]


def init_sentry() -> None:
    """Initialise Sentry error/trace reporting if a real `SENTRY_DSN` is configured."""

    if not SENTRY_DSN or SENTRY_DSN == "" or SENTRY_DSN == "https://...":
        setup_logger().warning("No SENTRY_DSN provided. Sentry is disabled.")
        return
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=float(SENTRY_TRACES_SAMPLE_RATE),
        _experiments={
            "continuous_profiling_auto_start": True,
        },
    )
