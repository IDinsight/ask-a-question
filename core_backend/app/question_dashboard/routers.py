from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_async_session
from ..users.models import UserDB
from ..utils import setup_logger
from .models import get_dashboard_stats
from .schemas import QuestionDashBoard

router = APIRouter(prefix="/dashboard")
logger = setup_logger()


@router.get("/question_stats", response_model=QuestionDashBoard)
async def retrieve_questions_stats(
    user_db: Annotated[UserDB, Depends(get_current_user)],
    asession: AsyncSession = Depends(get_async_session),
) -> QuestionDashBoard:
    """
    Retrieve all question answer statistics
    """
    stats = await get_dashboard_stats(user_id=user_db.user_id, asession=asession)

    return stats
