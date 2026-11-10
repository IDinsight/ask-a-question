"""This module contains FastAPI routers for admin endpoints."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import service
from app.core.database import get_async_session

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

    error_message = await service.check_database_connection(asession=db_session)
    if error_message is not None:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": error_message},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})
