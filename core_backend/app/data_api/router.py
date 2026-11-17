"""This module contains FastAPI routers for data API endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import authenticate_key
from app.contents.schemas import ContentRetrieve
from app.core.database import get_async_session
from app.data_api.schemas import QueryExtract, UrgencyQueryExtract
from app.data_api.service import (
    get_workspace_contents,
    get_workspace_queries,
    get_workspace_urgency_queries,
    get_workspace_urgency_rules,
)
from app.urgency_rules.schemas import UrgencyRuleRetrieve
from app.workspaces.models import WorkspaceDB

TAG_METADATA = {
    "name": "Data API",
    "description": "_Requires API key._ Endpoints for managing data.",
}

router = APIRouter(
    prefix="/data-api",
    dependencies=[Depends(authenticate_key)],
    tags=[TAG_METADATA["name"]],
)


@router.get("/contents", response_model=list[ContentRetrieve])
async def get_contents(
    workspace_db: Annotated[WorkspaceDB, Depends(authenticate_key)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[ContentRetrieve]:
    """Get all contents for a workspace.

    Parameters
    ----------
    workspace_db
        The authenticated workspace object.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[ContentRetrieve]
        A list of ContentRetrieve objects containing all contents for the user.
    """

    return await get_workspace_contents(
        asession=asession, workspace_id=workspace_db.workspace_id
    )


@router.get(
    "/urgency-rules",
    response_model=list[UrgencyRuleRetrieve],
    # Explicit ID: the function name clashes with the /urgency-rules/ router's
    # `get_urgency_rules`, and operationIds must be unique (see app/main.py).
    operation_id="get_data_api_urgency_rules",
)
async def get_urgency_rules(
    workspace_db: Annotated[WorkspaceDB, Depends(authenticate_key)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[UrgencyRuleRetrieve]:
    """Get all urgency rules for a workspace.

    Parameters
    ----------
    workspace_db
        The authenticated workspace object.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[UrgencyRuleRetrieve]
        A list of `UrgencyRuleRetrieve` objects containing all urgency rules for the
        workspace.
    """

    return await get_workspace_urgency_rules(
        asession=asession, workspace_id=workspace_db.workspace_id
    )


@router.get("/queries", response_model=list[QueryExtract])
async def get_queries(
    start_date: Annotated[
        datetime,
        Query(
            description=("A UTC datetime.Example: `2021-01-01T00:00:00`"),
        ),
    ],
    end_date: Annotated[
        datetime,
        Query(
            description=("A UTC datetime.Example: `2021-01-01T00:00:00`"),
        ),
    ],
    workspace_db: Annotated[WorkspaceDB, Depends(authenticate_key)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[QueryExtract]:
    """Get all queries including child records for a workspace between a start and end
    date.

    Parameters
    ----------
    start_date
        The start date to filter queries by.
    end_date
        The end date to filter queries by.
    workspace_db
        The authenticated workspace object.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[QueryExtract]
        A list of QueryExtract objects containing all queries for the user.
    """

    return await get_workspace_queries(
        asession=asession,
        end_date=end_date,
        start_date=start_date,
        workspace_id=workspace_db.workspace_id,
    )


@router.get("/urgency-queries", response_model=list[UrgencyQueryExtract])
async def get_urgency_queries(
    start_date: Annotated[
        datetime,
        Query(
            description=("A UTC datetime.Example: `2021-01-01T00:00:00`"),
        ),
    ],
    end_date: Annotated[
        datetime,
        Query(
            description=("A UTC datetime.Example: `2021-01-01T00:00:00`"),
        ),
    ],
    workspace_db: Annotated[WorkspaceDB, Depends(authenticate_key)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[UrgencyQueryExtract]:
    """Get all urgency queries including child records for a workspace between a start
    and end date.

    Parameters
    ----------
    start_date
        The start date to filter queries by.
    end_date
        The end date to filter queries by.
    workspace_db
        The authenticated workspace object.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[UrgencyQueryExtract]
        A list of `UrgencyQueryExtract` objects containing all urgent queries for the
        workspace.
    """

    return await get_workspace_urgency_queries(
        asession=asession,
        end_date=end_date,
        start_date=start_date,
        workspace_id=workspace_db.workspace_id,
    )
