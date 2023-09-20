from fastapi import FastAPI
from app.routers import admin
from app.routers import question_answer


def create_app():
    """Application Factory"""
    app = FastAPI()
    app.include_router(admin.router)
    app.include_router(question_answer.router)

    return app
