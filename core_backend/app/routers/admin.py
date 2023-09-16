from fastapi import APIRouter, Depends
from app.database import get_async_session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter()


@router.get("/healthcheck")
async def healthcheck(db_session: Session = Depends(get_async_session)):
    """ """
    try:
        await db_session.execute(text("SELECT 1;"))
    except SQLAlchemyError as e:
        return f"Failed database connection: {e}", 500

    return "All good", 200
