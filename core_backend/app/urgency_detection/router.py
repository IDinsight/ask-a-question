"""This module contains FastAPI routers for urgency detection endpoints."""

from fastapi import APIRouter, Depends
from langfuse.decorators import observe  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import authenticate_key, rate_limiter
from app.core.database import get_async_session
from app.urgency_detection.schemas import UrgencyQuery, UrgencyResponse
from app.urgency_detection.service import classify_urgency
from app.workspaces.models import WorkspaceDB

TAG_METADATA = {
    "name": "Urgency detection",
    "description": "_Requires API key._ Detect urgent messages according to "
    "urgency rules.",
}

router = APIRouter(
    dependencies=[Depends(authenticate_key), Depends(rate_limiter)],
    tags=[TAG_METADATA["name"]],
)


@router.post("/urgency-detect", response_model=UrgencyResponse)
@observe()
async def classify_text(
    urgency_query: UrgencyQuery,
    asession: AsyncSession = Depends(get_async_session),
    workspace_db: WorkspaceDB = Depends(authenticate_key),
) -> UrgencyResponse:
    """Classify the urgency of a text message.

    Parameters
    ----------
    urgency_query
        The urgency query to classify.
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_db
        The authenticated workspace object.

    Returns
    -------
    UrgencyResponse
        The urgency response object.

    Raises
    ------
    ValueError
        If the urgency classifier is invalid.
    """

    return await classify_urgency(
        asession=asession,
        urgency_query=urgency_query,
        workspace_id=workspace_db.workspace_id,
    )
