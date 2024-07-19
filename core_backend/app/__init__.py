from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    CollectorRegistry,
    make_asgi_app,
    multiprocess,
)

from . import (
    admin,
    auth,
    contents,
    dashboard,
    question_answer,
    tags,
    urgency_detection,
    urgency_rules,
    user_tools,
)
from .config import DOMAIN, LANGFUSE
from .prometheus_middleware import PrometheusMiddleware
from .utils import setup_logger

logger = setup_logger()

page_description = """
Welcome to the API documentation for the Ask A Question backend. These API is used to
interact with the Ask A Question application.

The important endpoints here are divided into the following two groups:

1. APIs to be called from your chat manager (authenticated via API key):
- **Question-answering and feedback collection**: LLM-powered question answering based
on your content. Plus feedback collection for the answers.
- **Urgency detection**: Detect urgent messages according to your urgency rules.

2. APIs used by the AAQ Admin App (authenticated via user login):
- **Question-answering content management**: APIs to manage the contents in the
application.
- **Question-answering content tag management**: APIs to manage the content tags in the
application.
- **Urgency rules management**: APIs to manage the urgency rules in the application.
"""
tags_metadata = [
    question_answer.TAG_METADATA,
    urgency_detection.TAG_METADATA,
    contents.TAG_METADATA,
    tags.TAG_METADATA,
    urgency_rules.TAG_METADATA,
    dashboard.TAG_METADATA,
    auth.TAG_METADATA,
    user_tools.TAG_METADATA,
    admin.TAG_METADATA,
]

if LANGFUSE == "True":
    logger.info("Setting up langfuse callbacks")
    import litellm

    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan events for the FastAPI application.

    :param app: FastAPI application instance.
    """

    logger.info("Application started")
    yield
    logger.info("Application finished")


def create_metrics_app() -> Callable:
    """Create prometheus metrics app"""
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return make_asgi_app(registry=registry)


def create_app() -> FastAPI:
    """Create the FastAPI application for the backend. The process is as follows:

    1. Include routers for all the endpoints.
    2. Add CORS middleware for cross-origin requests.
    3. Add Prometheus middleware for metrics.
    4. Mount the metrics app on /metrics as an independent application.

    :returns:
        app: FastAPI application instance.
    """

    app = FastAPI(
        title="Ask A Question APIs",
        description=page_description,
        debug=True,
        openapi_tags=tags_metadata,
        lifespan=lifespan,
    )
    app.include_router(contents.router)
    app.include_router(tags.router)
    app.include_router(question_answer.router)
    app.include_router(urgency_rules.router)
    app.include_router(urgency_detection.router)
    app.include_router(dashboard.router)
    app.include_router(auth.router)
    app.include_router(user_tools.router)
    app.include_router(admin.routers.router)

    origins = [
        f"http://{DOMAIN}",
        f"http://{DOMAIN}:3000",
        f"https://{DOMAIN}",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(PrometheusMiddleware)
    metrics_app = create_metrics_app()
    app.mount("/metrics", metrics_app)

    return app
