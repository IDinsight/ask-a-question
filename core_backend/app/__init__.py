from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    CollectorRegistry,
    make_asgi_app,
    multiprocess,
)

from .configs.app_config import DOMAIN, QDRANT_COLLECTION_NAME, QDRANT_VECTOR_SIZE
from .routers import admin, auth, manage_content, question_answer, whatsapp_qa
from .utils import setup_logger

logger = setup_logger()


def make_metrics_app() -> Callable:
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

    metrics_app = make_metrics_app()
    app.mount("/metrics", metrics_app)

    @app.on_event("startup")
    def startup_event() -> None:
        """Startup event"""

        from .db.vector_db import create_qdrant_collection, get_qdrant_client

        qdrant_client = get_qdrant_client()

        if QDRANT_COLLECTION_NAME not in {
            collection.name
            for collection in qdrant_client.get_collections().collections
        }:
            create_qdrant_collection(QDRANT_COLLECTION_NAME, QDRANT_VECTOR_SIZE)
            logger.info(f"Created collection {QDRANT_COLLECTION_NAME}")

    return app
