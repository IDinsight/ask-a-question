from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    CollectorRegistry,
    make_asgi_app,
    multiprocess,
)

from .configs.app_config import (
    DOMAIN,
)
from .prometheus_middleware import PrometheusMiddleware
from .routers import (
    admin,
    auth,
    manage_content,
    manage_language,
    question_answer,
    whatsapp_qa,
)
from .utils import setup_logger

logger = setup_logger()


def create_metrics_app() -> Callable:
    """Create prometheus metrics app"""
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return make_asgi_app(registry=registry)


def create_app() -> FastAPI:
    """Application Factory"""
    app = FastAPI(title="Question Answering Service", debug=True)
    app.include_router(admin.router)
    app.include_router(question_answer.router)
    app.include_router(manage_content.router)
    app.include_router(auth.router)
    app.include_router(whatsapp_qa.router)
    app.include_router(manage_language.router)

    origins = [
        f"http://{DOMAIN}",
        f"http://{DOMAIN}:3000",
        f"https://{DOMAIN}",
        f"https://{DOMAIN}:3000",
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
    def startup_event() -> None:
        """Startup event"""
        logger.info("Application started")

    return app
