"""FastAPI entrypoint for the Ask A Question backend.

Defines the module-level `app` object, following the FastAPI layout in
https://fastapi.tiangolo.com/tutorial/testing/#separating-tests. Serve it with
`uvicorn app.main:app` (or gunicorn, see `startup.sh`); tests import it with
`from app.main import app`.

Each feature follows the same layering:

    router.py -> service.py -> repository.py -> models.py   (+ schemas.py)
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import uvicorn
from fastapi import Depends, FastAPI
from fastapi.logger import logger as fastapi_logger
from fastapi.middleware.cors import CORSMiddleware
from redis import asyncio as aioredis
from slowapi.errors import RateLimitExceeded
from uvicorn_worker import UvicornWorker  # moved out of uvicorn.workers (deprecated)

# Routers are imported under a `<feature>_router` alias. Importing them as bare
# `<feature>` would rebind e.g. `app.contents` to the router module and break
# dotted lookups such as mock.patch("app.contents.repository...").
from app.admin import router as admin_router
from app.auth import router as auth_router
from app.contents import router as contents_router
from app.core.config import (
    BACKEND_ROOT_PATH,
    CROSS_ENCODER_MODEL,
    DEBUG,
    DOMAIN,
    HTTPX_TIMEOUT,
    METRICS_TOKEN,
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
from app.core.security import (
    SecurityHeadersMiddleware,
    enforce_default_rate_limit,
    limiter,
    protect_metrics_app,
    rate_limit_exceeded_handler,
    validate_security_settings,
)
from app.dashboard import router as dashboard_router
from app.data_api import router as data_api_router
from app.docmuncher import router as docmuncher_router
from app.question_answer import router as question_answer_router
from app.tags import router as tags_router
from app.urgency_detection import router as urgency_detection_router
from app.urgency_rules import router as urgency_rules_router
from app.users import router as users_router
from app.workspaces import router as workspaces_router

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
    admin_router,
    auth_router,
    contents_router,
    dashboard_router,
    data_api_router,
    docmuncher_router,
    question_answer_router,
    tags_router,
    urgency_detection_router,
    urgency_rules_router,
    users_router,
    workspaces_router,
]

tags_metadata = [m.TAG_METADATA for m in FEATURE_ROUTERS if m is not docmuncher_router]


def load_crossencoder() -> Any:
    """Load the cross-encoder model used to rerank search results.

    `sentence_transformers` is imported here rather than at the top of the module:
    the import alone takes over a second, and it is only needed when
    `USE_CROSS_ENCODER == "True"`. Tests replace this function with a cheap fake.

    Returns
    -------
    Any
        A `sentence_transformers.CrossEncoder` instance.
    """

    from sentence_transformers import CrossEncoder

    return CrossEncoder(CROSS_ENCODER_MODEL)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
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
        app.state.crossencoder = load_crossencoder()

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


# 0. Refuse to start with a missing/weak JWT secret (raises InsecureConfigurationError).
validate_security_settings()

# 1. Build the app. `debug` stays off unless DEBUG=true: in debug mode FastAPI returns
# full tracebacks to API clients.
app = FastAPI(
    debug=DEBUG,
    # Applies RATE_LIMIT_DEFAULT to every route without its own `@limiter.limit`.
    dependencies=[Depends(enforce_default_rate_limit)],
    description=page_description,
    # Use the route function's name as the OpenAPI operationId (e.g. "retrieve_content"
    # instead of "retrieve_content_content__get"). admin_app generates its typed API
    # client from this spec, so these become readable SDK function names. Route
    # function names must therefore stay unique across all routers.
    generate_unique_id_function=lambda route: route.name,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    title="Ask A Question APIs",
)

# 2. Include routers for all the endpoints.
for feature in FEATURE_ROUTERS:
    app.include_router(feature.router)

# 3. Register handlers that turn service-layer exceptions into HTTP responses.
register_exception_handlers(app)

# 4. Request rate limiting (slowapi). The default limit is enforced by the app-wide
# `enforce_default_rate_limit` dependency (see step 1); credential routes are
# decorated with `@limiter.limit`. Over-limit requests become a 429 here.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# 5. Add CORS middleware for cross-origin requests.
origins = [
    f"http://{DOMAIN}",
    f"http://{DOMAIN}:3000",
    f"https://{DOMAIN}",
]
# Only the methods and request headers the admin app actually uses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# 6. Add Prometheus middleware and mount the metrics app on /metrics. The metrics app
# requires `Authorization: Bearer $METRICS_TOKEN` and is a 404 when the token is unset.
app.add_middleware(PrometheusMiddleware)
app.mount("/metrics", protect_metrics_app(create_metrics_app(), token=METRICS_TOKEN))

# Added last so it is the outermost middleware and also covers CORS preflight and
# error responses.
app.add_middleware(SecurityHeadersMiddleware)

# 7. Initialise Langfuse and Sentry if configured.
init_langfuse()
init_sentry()


class Worker(UvicornWorker):
    """Custom gunicorn worker class to allow `root_path` to be passed to Uvicorn."""

    CONFIG_KWARGS = {"root_path": BACKEND_ROOT_PATH}


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    fastapi_logger.setLevel(logging.DEBUG)
    uvicorn.run(
        "app.main:app",
        # Local dev server only (`python -m app.main`), usually inside a container.
        host="0.0.0.0",  # nosec B104
        port=8000,
        reload=True,
        log_level="debug",
        root_path=BACKEND_ROOT_PATH,
    )
