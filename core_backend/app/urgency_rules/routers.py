"""This module contains FastAPI routers for urgency rule endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from langfuse.decorators import langfuse_context, observe  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_workspace_name
from ..database import get_async_session
from ..users.models import UserDB, user_has_required_role_in_workspace
from ..users.schemas import UserRoles
from ..utils import EmbeddingCallException, setup_logger
from ..workspaces.utils import get_workspace_by_workspace_name
from .models import (
    UrgencyRuleDB,
    delete_urgency_rule_from_db,
    get_urgency_rule_by_id_from_db,
    get_urgency_rules_from_db,
    save_urgency_rule_to_db,
    update_urgency_rule_in_db,
)
from .schemas import UrgencyRuleCreate, UrgencyRuleRetrieve

TAG_METADATA = {
    "name": "Urgency rules management",
    "description": "_Requires user login._ Manage urgency rules for urgency detection.",
}

router = APIRouter(prefix="/urgency-rules", tags=[TAG_METADATA["name"]])
logger = setup_logger(name=__name__)


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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to create urgency rules in "
            "the workspace.",
        )
    try:

        urgency_rule_db = await save_urgency_rule_to_db(
            asession=asession,
            urgency_rule=urgency_rule,
            workspace_id=workspace_db.workspace_id,
        )
        langfuse_context.update_current_trace(
            name="create_urgency_rule",
            metadata={
                "urgency_rule_id": urgency_rule_db.urgency_rule_id,
                "workspace_id": workspace_db.workspace_id,
            },
        )
    except EmbeddingCallException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error embedding rule. Please check embedding service.",
        ) from e
    return _convert_record_to_schema(urgency_rule_db=urgency_rule_db)


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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    urgency_rule_db = await get_urgency_rule_by_id_from_db(
        asession=asession,
        urgency_rule_id=urgency_rule_id,
        workspace_id=workspace_db.workspace_id,
    )

    if not urgency_rule_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Urgency Rule ID `{urgency_rule_id}` not found",
        )

    return _convert_record_to_schema(urgency_rule_db=urgency_rule_db)


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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to delete urgency rules in "
            "the workspace.",
        )

    workspace_id = workspace_db.workspace_id
    urgency_rule_db = await get_urgency_rule_by_id_from_db(
        asession=asession, urgency_rule_id=urgency_rule_id, workspace_id=workspace_id
    )

    if not urgency_rule_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Urgency Rule ID `{urgency_rule_id}` not found",
        )

    await delete_urgency_rule_from_db(
        asession=asession, urgency_rule_id=urgency_rule_id, workspace_id=workspace_id
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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )

    if not await user_has_required_role_in_workspace(
        allowed_user_roles=[UserRoles.ADMIN],
        asession=asession,
        user_db=calling_user_db,
        workspace_db=workspace_db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have the required role to update urgency rules in "
            "the workspace.",
        )

    workspace_id = workspace_db.workspace_id
    old_urgency_rule = await get_urgency_rule_by_id_from_db(
        asession=asession, urgency_rule_id=urgency_rule_id, workspace_id=workspace_id
    )

    if not old_urgency_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Urgency Rule ID `{urgency_rule_id}` not found",
        )
    try:
        urgency_rule_db = await update_urgency_rule_in_db(
            asession=asession,
            urgency_rule=urgency_rule,
            urgency_rule_id=urgency_rule_id,
            workspace_id=workspace_id,
        )
        langfuse_context.update_current_trace(
            name="update_urgency_rule",
            metadata={
                "urgency_rule_id": urgency_rule_db.urgency_rule_id,
                "workspace_id": workspace_db.workspace_id,
            },
        )
    except EmbeddingCallException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error embedding rule. Please check embedding service.",
        ) from e
    return _convert_record_to_schema(urgency_rule_db=urgency_rule_db)


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

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    urgency_rules_db = await get_urgency_rules_from_db(
        asession=asession, workspace_id=workspace_db.workspace_id
    )
    return [
        _convert_record_to_schema(urgency_rule_db=urgency_rule_db)
        for urgency_rule_db in urgency_rules_db
    ]


def _convert_record_to_schema(*, urgency_rule_db: UrgencyRuleDB) -> UrgencyRuleRetrieve:
    """Convert a `UrgencyRuleDB` record to a `UrgencyRuleRetrieve` schema.

    Parameters
    ----------
    urgency_rule_db
        The urgency rule record from the database.

    Returns
    -------
    UrgencyRuleRetrieve
        The urgency rule retrieval schema.
    """

    return UrgencyRuleRetrieve(
        created_datetime_utc=urgency_rule_db.created_datetime_utc,
        updated_datetime_utc=urgency_rule_db.updated_datetime_utc,
        urgency_rule_id=urgency_rule_db.urgency_rule_id,
        urgency_rule_metadata=urgency_rule_db.urgency_rule_metadata,
        urgency_rule_text=urgency_rule_db.urgency_rule_text,
        workspace_id=urgency_rule_db.workspace_id,
    )
