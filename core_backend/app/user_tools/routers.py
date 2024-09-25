from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_admin_user, get_current_user
from ..database import get_async_session
from ..users.models import (
    UserAlreadyExistsError,
    UserDB,
    get_user_by_id,
    is_username_valid,
    save_user_to_db,
    update_user_api_key,
    update_user_in_db,
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
    admin_user_db: Annotated[UserDB, Depends(get_admin_user)],
    request: Request,
    asession: AsyncSession = Depends(get_async_session),
) -> UserCreate | None:
    """
    Create user endpoint. Can only be used by admin users.
    """

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
            is_admin=user_new.is_admin,
            content_quota=user_new.content_quota,
            api_daily_quota=user_new.api_daily_quota,
        )
    except UserAlreadyExistsError as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=400, detail="User with that username already exists."
        ) from e


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


@router.put("/{user_id}", response_model=UserRetrieve)
async def update_user(
    user_id: int,
    user: UserCreate,
    admin_user_db: Annotated[UserDB, Depends(get_admin_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> UserRetrieve | None:
    """
    Update user endpoint.
    """

    user_db = await get_user_by_id(user_id=user_id, asession=asession)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.username != user_db.username:
        if not await is_username_valid(user.username, asession):
            raise HTTPException(
                status_code=400,
                detail=f"User with username {user.username} already exists.",
            )

    updated_user = await update_user_in_db(
        user_id=user_id, user=user, asession=asession
    )
    return UserRetrieve(
        user_id=updated_user.user_id,
        username=updated_user.username,
        content_quota=updated_user.content_quota,
        api_daily_quota=user_db.api_daily_quota,
        is_admin=user_db.is_admin,
        api_key_first_characters=updated_user.api_key_first_characters,
        api_key_updated_datetime_utc=updated_user.api_key_updated_datetime_utc,
        created_datetime_utc=updated_user.created_datetime_utc,
        updated_datetime_utc=updated_user.updated_datetime_utc,
    )


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
        api_daily_quota=user_db.api_daily_quota,
        is_admin=user_db.is_admin,
        api_key_first_characters=user_db.api_key_first_characters,
        api_key_updated_datetime_utc=user_db.api_key_updated_datetime_utc,
        created_datetime_utc=user_db.created_datetime_utc,
        updated_datetime_utc=user_db.updated_datetime_utc,
    )
