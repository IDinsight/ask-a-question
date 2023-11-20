from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .configs.app_config import QDRANT_COLLECTION_NAME, QDRANT_VECTOR_SIZE
from .routers import admin, auth, manage_content, question_answer, whatsapp_qa
from .utils import setup_logger

logger = setup_logger()


def create_app() -> FastAPI:
    """Application Factory"""
    app = FastAPI(title="Question Answering Service", debug=True)
    app.include_router(admin.router)
    app.include_router(question_answer.router)
    app.include_router(manage_content.router)
    app.include_router(auth.router)
    app.include_router(whatsapp_qa.router)

    origins = [
        "https://localhost",
        "https://localhost:3000",
        "http://localhost",
        "http://localhost:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
