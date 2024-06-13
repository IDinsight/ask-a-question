from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
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
from ..users.schemas import UserCreateWithPassword, UserRetrieve
from ..utils import generate_key, setup_logger
from .schemas import KeyResponse

router = APIRouter(prefix="/user", tags=["User Tools"])
logger = setup_logger()


@router.post("/", response_model=UserRetrieve)
async def create_user(
    user: UserCreateWithPassword,
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> UserRetrieve | None:
    """
    Create user endpoint. Can only be used by user with ID 1.
    """

    if user_db.user_id != 1:
        raise HTTPException(
            status_code=403,
            detail="This user does not have permission to create new users.",
        )

    try:
        user_db = await save_user_to_db(
            user=user,
            asession=asession,
        )
        return UserRetrieve(
            user_id=user_db.user_id,
            username=user_db.username,
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
