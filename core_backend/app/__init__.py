from typing import Callable

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
    urgency_detection,
    urgency_rules,
    whatsapp_qa,
)
from .config import (
    DOMAIN,
)
from .prometheus_middleware import PrometheusMiddleware
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
    app.include_router(admin.routers.router)
    app.include_router(question_answer.router)
    app.include_router(contents.router)
    app.include_router(question_dashboard.router)
    app.include_router(auth.router)
    app.include_router(whatsapp_qa.router)
    app.include_router(urgency_detection.router)
    app.include_router(urgency_rules.router)

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
