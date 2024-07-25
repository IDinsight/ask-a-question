from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CollectorRegistry, make_asgi_app, multiprocess

from . import (
    admin,
    auth,
    contents,
    dashboard,
    data_api,
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

🔑 <a href="https://app.ask-a-question.com/integrations" target="_blank">Get your API
key</a> |
📖 <a href="https://docs.ask-a-question.com" target="_blank">Docs</a> |
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" height="1em"
style="vertical-align: bottom;"><path d="m0 0h24v24h-24z" fill="#fff" opacity="0"
transform="matrix(-1 0 0 -1 24 24)"/><path d="m12 1a10.89 10.89 0 0 0 -11 10.77 10.79
10.79 0 0 0 7.52 10.23c.55.1.75-.23.75-.52s0-.93
0-1.83c-3.06.65-3.71-1.44-3.71-1.44a2.86 2.86 0 0 0 -1.22-1.58c-1-.66.08-.65.08-.65a2.31
2.31 0 0 1 1.68 1.11 2.37 2.37 0 0 0 3.2.89 2.33 2.33 0 0 1
.7-1.44c-2.44-.27-5-1.19-5-5.32a4.15 4.15 0 0 1 1.11-2.91 3.78 3.78 0 0 1
.11-2.84s.93-.29 3 1.1a10.68 10.68 0 0 1 5.5 0c2.1-1.39 3-1.1 3-1.1a3.78 3.78 0 0 1 .11
2.84 4.15 4.15 0 0 1 1.17 2.89c0 4.14-2.58 5.05-5 5.32a2.5 2.5 0 0 1 .75
2v2.95s.2.63.75.52a10.8 10.8 0 0 0 7.5-10.22 10.89 10.89 0 0 0 -11-10.77"
fill="#231f20"/></svg> <a href="https://github.com/IDinsight/ask-a-question"
target="_blank">GitHub</a> |
🔗 <a href="https://ask-a-question.com" target="_blank">Website</a>

Welcome to the API documentation for the
<a href="https://ask-a-question.com" target="_blank">Ask A Question</a> backend.
These APIs are used to interact with the Ask A Question application.

The important endpoints here are divided into the following two groups:

1. APIs to be called from your chat manager (authenticated via API key):
    - **Question-answering and feedback**: LLM-powered search and answer generation
      based on your content. Plus feedback collection for the answers.
    - **Urgency detection**: Detect urgent messages according to your urgency rules.

2. APIs used by the AAQ Admin App (authenticated via user login):
    - **Content management**: APIs to manage the contents in the
application.
    - **Content tag management**: APIs to manage the content tags in the
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
    app.include_router(data_api.router)

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
