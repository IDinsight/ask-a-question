from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from ..db.engine import get_async_session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter()


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
