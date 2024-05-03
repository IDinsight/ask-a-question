from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_readonly_user
from ..auth.schemas import AuthenticatedUser
from ..database import get_async_session
from ..utils import setup_logger
from .models import get_dashboard_stats
from .schemas import QuestionDashBoard

router = APIRouter(prefix="/dashboard")
logger = setup_logger()


@router.get("/question_stats", response_model=QuestionDashBoard)
async def retrieve_questions_stats(
    readonly_access_user: Annotated[
        AuthenticatedUser, Depends(get_current_readonly_user)
    ],
    asession: AsyncSession = Depends(get_async_session),
) -> QuestionDashBoard:
    """
    Retrieve all question answer statistics
    """
    stats = await get_dashboard_stats(asession=asession)

    return stats
