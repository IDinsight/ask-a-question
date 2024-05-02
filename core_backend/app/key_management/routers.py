from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..users.models import UserDB, update_user_retrieval_key
from ..utils import generate_key, setup_logger
from .schemas import KeyResponse

router = APIRouter(prefix="/key", tags=["Retrieval Key Management"])
logger = setup_logger()


@router.put("/", response_model=KeyResponse)
async def get_new_retrieval_key(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> KeyResponse | None:
    """
    Generate a new API key for the requester's account. Takes a user object,
    generates a new key, replaces the old one in the database, and returns
    a user object with the new key.
    """

    new_retrieval_key = generate_key()

    try:
        # this is neccesarry to attach the user_db to the session
        asession.add(user_db)
        await update_user_retrieval_key(
            user_db=user_db,
            new_retrieval_key=new_retrieval_key,
            asession=asession,
        )
        return KeyResponse(
            username=user_db.username,
            new_retrieval_key=new_retrieval_key,
        )
    except Exception as e:
        logger.error(f"Error updating user retrieval key: {e}")
        raise HTTPException(
            status_code=500, detail="Error updating user retrieval key"
        ) from e
