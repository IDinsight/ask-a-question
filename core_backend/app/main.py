"""FastAPI application entrypoint.

Wires every feature's router into one app and attaches the cross-cutting pieces
from `app.core`: domain-exception handlers, CORS, Prometheus metrics, Sentry and
Langfuse. Each feature follows the same layering:

    router.py -> service.py -> repository.py -> models.py   (+ schemas.py)

`router` handles HTTP only, `service` holds business rules, `repository` holds all
database queries, and `models` holds the SQLAlchemy ORM classes.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import asyncio as aioredis
from sentence_transformers import CrossEncoder

from app.admin import router as admin
from app.auth import router as auth
from app.contents import router as contents
from app.core.config import (
    CROSS_ENCODER_MODEL,
    DOMAIN,
    HTTPX_TIMEOUT,
    REDIS_HOST,
    USE_CROSS_ENCODER,
)
from app.core.exceptions import register_exception_handlers
from app.core.observability import (
    PrometheusMiddleware,
    create_metrics_app,
    init_langfuse,
    init_sentry,
    setup_logger,
)
from app.dashboard import router as dashboard
from app.data_api import router as data_api
from app.docmuncher import router as docmuncher
from app.question_answer import router as question_answer
from app.tags import router as tags
from app.urgency_detection import router as urgency_detection
from app.urgency_rules import router as urgency_rules
from app.users import router as users
from app.workspaces import router as workspaces

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
    - **Workspace management**: APIs to manage the workspaces in the application.
"""

# Order here controls the order of routers and OpenAPI tag groups in the docs.
# `docmuncher` is left out of the OpenAPI tag list, as it was before.
FEATURE_ROUTERS = [
    admin,
    auth,
    contents,
    dashboard,
    data_api,
    docmuncher,
    question_answer,
    tags,
    urgency_detection,
    urgency_rules,
    users,
    workspaces,
]

tags_metadata = [
    m.TAG_METADATA for m in FEATURE_ROUTERS if m is not docmuncher
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan events for the FastAPI application.

    The process is as follows:

    1. Connect to redis.
    2. Load the cross-encoder model if enabled.
    3. Set up HTTPX client for making HTTP requests.
    4. Yield control to the application.
    5. Close the Redis connection when the application finishes.
    6. Close the HTTPX client when the application finishes.

    Parameters
    ----------
    app
        The application instance.
    """

    logger.info("Application started")

    # 1.
    app.state.redis = await aioredis.from_url(REDIS_HOST)

    # 2.
    if USE_CROSS_ENCODER == "True":
        app.state.crossencoder = CrossEncoder(
            CROSS_ENCODER_MODEL,
        )

    # 3.
    logger.info("Setting up HTTPX client for making HTTP requests...")
    timeout = httpx.Timeout(HTTPX_TIMEOUT, read=None)
    app.state.httpx_client = httpx.AsyncClient(timeout=timeout)
    logger.info("Finished setting up HTTPX client!")

    # 4.
    yield

    # 5.
    logger.info("Closing Redis connection...")
    await app.state.redis.aclose()
    logger.info("Redis connection closed!")

    # 6.
    logger.info("Closing HTTPX client...")
    await app.state.httpx_client.aclose()
    logger.info("HTTPX client closed!")

    logger.info("Application finished")


def create_app() -> FastAPI:
    """Create the FastAPI application for the backend. The process is as follows:

    1. Include routers for all the endpoints.
    2. Register handlers that turn service-layer exceptions into HTTP responses.
    3. Add CORS middleware for cross-origin requests.
    4. Add Prometheus middleware and mount the metrics app on /metrics.
    5. Initialise Langfuse and Sentry if configured.

    Returns
    -------
    FastAPI
        The application instance.
    """

    app = FastAPI(
        debug=True,
        description=page_description,
        openapi_tags=tags_metadata,
        lifespan=lifespan,
        title="Ask A Question APIs",
    )

    # 1.
    for feature in FEATURE_ROUTERS:
        app.include_router(feature.router)

    # 2.
    register_exception_handlers(app)

    # 3.
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

    # 4.
    app.add_middleware(PrometheusMiddleware)
    app.mount("/metrics", create_metrics_app())

    # 5.
    init_langfuse()
    init_sentry()

    return app
