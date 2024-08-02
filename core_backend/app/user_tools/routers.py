from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..users.models import (
    UserAlreadyExistsError,
    UserDB,
    save_user_to_db,
    update_user_api_key,
)
from ..users.schemas import UserCreate, UserCreateWithPassword, UserRetrieve
from ..utils import generate_key, setup_logger, update_api_limits
from .schemas import KeyResponse

TAG_METADATA = {
    "name": "Admin",
    "description": "_Requires user login._ Only administrator user has access to these "
    "endpoints.",
}

router = APIRouter(prefix="/user", tags=["Admin"])
logger = setup_logger()


@router.post("/", response_model=UserCreate)
async def create_user(
    user: UserCreateWithPassword,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    request: Request,
    asession: AsyncSession = Depends(get_async_session),
) -> UserCreate | None:
    """
    Create user endpoint. Can only be used by user with ID 1.
    """
    if user_db.user_id != 1:
        raise HTTPException(
            status_code=403,
            detail="This user does not have permission to create new users.",
        )

    try:
        user_new = await save_user_to_db(
            user=user,
            asession=asession,
        )
        await update_api_limits(
            request.app.state.redis, user_new.username, user_new.api_daily_quota
        )

        return UserCreate(
            username=user_new.username,
            content_quota=user_new.content_quota,
            api_daily_quota=user_new.api_daily_quota,
        )
    except UserAlreadyExistsError as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=400, detail="User with that username already exists."
        ) from e


@router.get("/", response_model=UserRetrieve)
async def get_user(
    user_db: Annotated[UserDB, Depends(get_current_user)],
) -> UserRetrieve | None:
    """
    Get user endpoint. Returns the user object for the requester.
    """

    return UserRetrieve(
        user_id=user_db.user_id,
        username=user_db.username,
        content_quota=user_db.content_quota,
        api_key_first_characters=user_db.api_key_first_characters,
        api_key_updated_datetime_utc=user_db.api_key_updated_datetime_utc,
        created_datetime_utc=user_db.created_datetime_utc,
        updated_datetime_utc=user_db.updated_datetime_utc,
    )


@router.put("/rotate-key", response_model=KeyResponse)
async def get_new_api_key(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> KeyResponse | None:
    """
    Generate a new API key for the requester's account. Takes a user object,
    generates a new key, replaces the old one in the database, and returns
    a user object with the new key.
    """

    new_api_key = generate_key()

    try:
        # this is neccesarry to attach the user_db to the session
        asession.add(user_db)
        await update_user_api_key(
            user_db=user_db,
            new_api_key=new_api_key,
            asession=asession,
        )
        return KeyResponse(
            username=user_db.username,
            new_api_key=new_api_key,
        )
    except SQLAlchemyError as e:
        logger.error(f"Error updating user api key: {e}")
        raise HTTPException(
            status_code=500, detail="Error updating user api key"
        ) from e
