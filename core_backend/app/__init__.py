from typing import Callable

import aioredis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
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
from .config import DOMAIN, LANGFUSE
from .database import get_async_session
from .prometheus_middleware import PrometheusMiddleware
from .users.models import get_all_users
from .utils import encode_api_limit, setup_logger

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


def create_app(redis_host: str) -> FastAPI:
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

    async def reset_quota() -> None:
        redis = app.state.redis
        async for asession in get_async_session():
            try:
                users = await get_all_users(asession)
                for user in users:
                    api_daily_quota = encode_api_limit(user.api_daily_quota)
                    await redis.set(
                        f"remaining-calls:{user.username}",
                        api_daily_quota,
                    )
                logger.info("Successfully Synced Redis to database")
            except Exception as e:
                logger.info(f"Redis sync failed: {e}")

    @app.on_event("startup")
    async def startup_event() -> None:
        """Startup event"""
        app.state.redis = await aioredis.from_url(redis_host)
        logger.info("Application started")
        scheduler = AsyncIOScheduler()
        await reset_quota()
        scheduler.add_job(reset_quota, "interval", minutes=1440)
        scheduler.start()
        app.state.scheduler = scheduler

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await app.state.redis.close()
        app.state.scheduler.shutdown()

    return app
