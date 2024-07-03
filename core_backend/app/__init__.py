from typing import Callable

import aioredis
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
    question_answer,
    question_dashboard,
    tags,
    urgency_detection,
    urgency_rules,
    user_tools,
    whatsapp_qa,
)
from .config import DOMAIN, LANGFUSE, REDIS_HOST
from .prometheus_middleware import PrometheusMiddleware
from .utils import setup_logger

logger = setup_logger()


if LANGFUSE == "True":
    logger.info("Setting up langfuse callbacks")
    import litellm

    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]


def create_metrics_app() -> Callable:
    """Create prometheus metrics app"""
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return make_asgi_app(registry=registry)


def create_app() -> FastAPI:
    """Application Factory"""
    app = FastAPI(title="Question Answering Service", debug=True)
    app.include_router(admin.routers.router)
    app.include_router(question_answer.router)
    app.include_router(contents.router)
    app.include_router(question_dashboard.router)
    app.include_router(auth.router)
    app.include_router(whatsapp_qa.router)
    app.include_router(user_tools.router)
    app.include_router(urgency_detection.router)
    app.include_router(urgency_rules.router)
    app.include_router(tags.router)

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

    @app.on_event("startup")
    async def startup_event() -> None:
        """Startup event"""
        app.state.redis = await aioredis.from_url(REDIS_HOST)
        logger.info("Application started")

    @app.on_event("shutdown")
    async def shutdown():
        await app.state.redis.close()

    return app
