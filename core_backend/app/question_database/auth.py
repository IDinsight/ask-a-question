from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .app_config import bearer_tokens_dict, db_specific_settings
from .engine import get_sqlalchemy_async_engine

bearer = HTTPBearer()


async def auth_bearer_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict[str, Any]:
    """
    Authenticate using basic bearer token.
    Used for setting the database session and connecting to
    the question-answer endpoints.
    """
    token = credentials.credentials
    settings = None
    if token in bearer_tokens_dict.keys():
        db_name = bearer_tokens_dict[token].lower()
        settings = db_specific_settings[f"metric_{db_name}"]
    else:
        raise HTTPException(
            status_code=401,
            detail="Invalid bearer token. Please make sure the bearer\
                            token matches the available databases",
        )

    asession = get_sqlalchemy_async_engine(
        which_db=settings.WHICH_DB,
        db_type=settings.METRIC_DB_TYPE,
        db_api=settings.METRIC_DB_ASYNC_API,
        db_path=settings.METRIC_DB_PATH,
        user=settings.METRIC_DB_USER,
        password=settings.METRIC_DB_PASSWORD,
        host=settings.METRIC_DB_HOST,
        port=settings.METRIC_DB_PORT,
        db=settings.METRIC_DB,
    )
    async with AsyncSession(
        asession,
        expire_on_commit=False,
    ) as async_session:
        return {
            "async_session": async_session,
            "settings": settings,
        }
