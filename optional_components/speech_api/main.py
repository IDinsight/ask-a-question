from app.routers import router
from fastapi import FastAPI

app = FastAPI()

app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint of the Speech API.
    """
    return {"message": "Welcome to the Whisper Service"}
