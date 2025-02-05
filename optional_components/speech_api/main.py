"""This module contains endpoints for the speech API."""

from app.routers import router
from fastapi import FastAPI

app = FastAPI()

app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint of the Speech API.

    Returns
    -------
    dict[str, str]
        A message indicating the service is running.
    """

    return {"message": "Welcome to the Whisper Service"}
