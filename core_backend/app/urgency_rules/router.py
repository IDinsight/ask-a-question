"""This module contains FastAPI routers for urgency rule endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from langfuse.decorators import observe  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user, get_current_workspace_name
from app.core.database import get_async_session
from app.urgency_rules import service
from app.urgency_rules.schemas import UrgencyRuleCreate, UrgencyRuleRetrieve
from app.users.models import UserDB

TAG_METADATA = {
    "name": "Urgency rules management",
    "description": "_Requires user login._ Manage urgency rules for urgency detection.",
}

router = APIRouter(prefix="/urgency-rules", tags=[TAG_METADATA["name"]])


@router.post("/", response_model=UrgencyRuleRetrieve)
@observe()
async def create_urgency_rule(
    urgency_rule: UrgencyRuleCreate,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> UrgencyRuleRetrieve:
    """Create a new urgency rule.

    Parameters
    ----------
    urgency_rule
        The urgency rule to create.
    calling_user_db
        The user object associated with the user that is creating the urgency rule.
    workspace_name
        The name of the workspace to create the urgency rule in.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    UrgencyRuleRetrieve
        The created urgency rule.

    Raises
    ------
    HTTPException
        If the user does not have the required role to create urgency rules in the
        workspace.
    """

    return await service.create_urgency_rule(
        asession=asession,
        calling_user_db=calling_user_db,
        urgency_rule=urgency_rule,
        workspace_name=workspace_name,
    )


@router.get("/{urgency_rule_id}", response_model=UrgencyRuleRetrieve)
async def get_urgency_rule(
    urgency_rule_id: int,
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> UrgencyRuleRetrieve:
    """Get a single urgency rule by ID.

    Parameters
    ----------
    urgency_rule_id
        The ID of the urgency rule to retrieve.
    workspace_name
        The name of the workspace to retrieve the urgency rule from.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    UrgencyRuleRetrieve
        The urgency rule.

    Raises
    ------
    HTTPException
        If the urgency rule with the given ID does not exist.
    """

    return await service.get_urgency_rule(
        asession=asession,
        urgency_rule_id=urgency_rule_id,
        workspace_name=workspace_name,
    )


@router.delete("/{urgency_rule_id}")
async def delete_urgency_rule(
    urgency_rule_id: int,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a single urgency rule by ID.

    Parameters
    ----------
    urgency_rule_id
        The ID of the urgency rule to delete.
    calling_user_db
        The user object associated with the user that is deleting the urgency rule.
    workspace_name
        The name of the workspace to delete the urgency rule from.
    asession
        The SQLAlchemy async session to use for all database connections.

    Raises
    ------
    HTTPException
        If the user does not have the required role to delete urgency rules in the
        workspace.
        If the urgency rule with the given ID does not exist.
    """

    await service.delete_urgency_rule(
        asession=asession,
        calling_user_db=calling_user_db,
        urgency_rule_id=urgency_rule_id,
        workspace_name=workspace_name,
    )


@router.put("/{urgency_rule_id}", response_model=UrgencyRuleRetrieve)
@observe()
async def update_urgency_rule(
    urgency_rule_id: int,
    urgency_rule: UrgencyRuleCreate,
    calling_user_db: Annotated[UserDB, Depends(get_current_user)],
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> UrgencyRuleRetrieve:
    """Update a single urgency rule by ID.

    Parameters
    ----------
    urgency_rule_id
        The ID of the urgency rule to update.
    urgency_rule
        The updated urgency rule object.
    calling_user_db
        The user object associated with the user that is updating the urgency rule.
    workspace_name
        The name of the workspace to update the urgency rule in.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    UrgencyRuleRetrieve
        The updated urgency rule.

    Raises
    ------
    HTTPException
        If the user does not have the required role to update urgency rules in the
        workspace.
        If the urgency rule with the given ID does not exist.
    """

    return await service.update_urgency_rule(
        asession=asession,
        calling_user_db=calling_user_db,
        urgency_rule=urgency_rule,
        urgency_rule_id=urgency_rule_id,
        workspace_name=workspace_name,
    )


@router.get("/", response_model=list[UrgencyRuleRetrieve])
async def get_urgency_rules(
    workspace_name: Annotated[str, Depends(get_current_workspace_name)],
    asession: AsyncSession = Depends(get_async_session),
) -> list[UrgencyRuleRetrieve]:
    """Get all urgency rules.

    Parameters
    ----------
    workspace_name
        The name of the workspace to retrieve urgency rules from.
    asession
        The SQLAlchemy async session to use for all database connections.

    Returns
    -------
    list[UrgencyRuleRetrieve]
        A list of urgency rules.
    """

    return await service.get_urgency_rules(
        asession=asession, workspace_name=workspace_name
    )
