"""This module contains the main entry point for the FastAPI application."""

import logging

import uvicorn
from fastapi.logger import logger
from uvicorn_worker import UvicornWorker  # moved out of uvicorn.workers (deprecated)

from app import create_app
from app.core.config import BACKEND_ROOT_PATH

app = create_app()


class Worker(UvicornWorker):
    """Custom worker class to allow `root_path` to be passed to Uvicorn."""

    CONFIG_KWARGS = {"root_path": BACKEND_ROOT_PATH}


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
        root_path=BACKEND_ROOT_PATH,
    )
