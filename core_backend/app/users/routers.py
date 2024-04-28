from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_fullaccess_user
from ..auth.schemas import AuthenticatedUser
from ..database import get_async_session
from ..users.models import get_user_by_username
from ..utils import generate_key, setup_logger
from .models import update_user_retrieval_key
from .schemas import KeyResponse

router = APIRouter(prefix="/key", tags=["Retrieval Key Management"])
logger = setup_logger()


@router.put("/", response_model=KeyResponse)
async def get_new_retrieval_key(
    full_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_fullaccess_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> KeyResponse | None:
    """
    Generate a new API key for the requester's account. Takes a user object,
    generates a new key, replaces the old one in the database, and returns
    a user object with the new key.
    """

    user_db = await get_user_by_username(full_access_user.username, asession)
    if user_db is None:
        raise HTTPException(status_code=404, detail="User not found")

    new_retrieval_key = generate_key()

    try:
        await update_user_retrieval_key(
            user_db=user_db,
            new_retrieval_key=new_retrieval_key,
            asession=asession,
        )
    except Exception as e:
        logger.error(f"Error updating user retrieval key: {e}")
        raise HTTPException(
            status_code=500, detail="Error updating user retrieval key"
        ) from e

    return KeyResponse(
        user_id=user_db.user_id,
        username=user_db.username,
        retrieval_key=new_retrieval_key,
    )
