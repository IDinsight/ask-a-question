from fastapi import FastAPI
from app.routers import admin
from app.routers import question_answer
from app.routers import manage_content


def create_app() -> FastAPI:
    """Application Factory"""
    app = FastAPI()
    app.include_router(admin.router)
    app.include_router(question_answer.router)
    app.include_router(manage_content.router)

    return app
