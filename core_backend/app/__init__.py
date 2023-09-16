from fastapi import FastAPI
from .routers import admin


def create_app():

    app = FastAPI()
    app.include_router(admin.router)

    return app
