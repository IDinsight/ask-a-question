"""This module contains FastAPI routers for admin endpoints."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session

TAG_METADATA = {
    "name": "Admin",
    "description": "Healthcheck endpoint for the application",
}

router = APIRouter(tags=[TAG_METADATA["name"]])


@router.get("/healthcheck")
async def healthcheck(
    db_session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    """Healthcheck endpoint - checks connection to the database.

    Parameters
    ----------
    db_session
        The database session object.

    Returns
    -------
    JSONResponse
        A JSON response with the status of the database connection.
    """

    try:
        await db_session.execute(text("SELECT 1;"))
    except SQLAlchemyError as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Failed database connection: {e}"},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})
