from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session

TAG_METADATA = {
    "name": "Healthcheck",
    "description": "Healthcheck endpoint for the application",
}

router = APIRouter(tags=[TAG_METADATA["name"]])


@router.get("/healthcheck")
async def healthcheck(
    db_session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    """
    Healthcheck endpoint - checks connection to Db
    """
    try:
        await db_session.execute(text("SELECT 1;"))
    except SQLAlchemyError as e:
        return JSONResponse(
            status_code=500, content={"message": f"Failed database connection: {e}"}
        )
    return JSONResponse(status_code=200, content={"status": "ok"})
