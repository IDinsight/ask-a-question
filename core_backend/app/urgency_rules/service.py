"""Business logic for managing urgency rules."""

from http import HTTPStatus

from langfuse.decorators import langfuse_context  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.core.utils import EmbeddingCallException
from app.urgency_rules.models import UrgencyRuleDB
from app.urgency_rules.repository import (
    delete_urgency_rule_from_db,
    get_urgency_rule_by_id_from_db,
    get_urgency_rules_from_db,
    save_urgency_rule_to_db,
    update_urgency_rule_in_db,
)
from app.urgency_rules.schemas import UrgencyRuleCreate, UrgencyRuleRetrieve
from app.users.models import UserDB
from app.users.repository import user_has_required_role_in_workspace
from app.users.schemas import UserRoles
from app.workspaces.models import WorkspaceDB
from app.workspaces.repository import get_workspace_by_workspace_name

# HTTP 502 has no dedicated domain exception, so `AppError` is raised with it.
_HTTP_502_BAD_GATEWAY = HTTPStatus.BAD_GATEWAY.value
_EMBEDDING_ERROR_DETAIL = "Error embedding rule. Please check embedding service."


async def _get_workspace_as_admin(
    *,
    action: str,
    asession: AsyncSession,
    calling_user_db: UserDB,
    workspace_name: str,
) -> WorkspaceDB:
    """Load a workspace and check that the calling user is an admin in it.

    Parameters
    ----------
    action
        The verb used in the error message (e.g. "create", "delete", "update").
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user making the request.
    workspace_name
        The name of the workspace.

    Returns
    -------
    WorkspaceDB
        The workspace.

    Raises
    ------
    ForbiddenError
        If the user is not an admin in the workspace.
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
        raise ForbiddenError(
            f"User does not have the required role to {action} urgency rules in "
            "the workspace."
        )
    return workspace_db


async def _get_existing_urgency_rule(
    *, asession: AsyncSession, urgency_rule_id: int, workspace_id: int
) -> UrgencyRuleDB:
    """Get an urgency rule, raising if it does not exist in the workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    urgency_rule_id
        The ID of the urgency rule.
    workspace_id
        The ID of the workspace the rule must belong to.

    Returns
    -------
    UrgencyRuleDB
        The urgency rule.

    Raises
    ------
    NotFoundError
        If the urgency rule does not exist in the workspace.
    """

    urgency_rule_db = await get_urgency_rule_by_id_from_db(
        asession=asession, urgency_rule_id=urgency_rule_id, workspace_id=workspace_id
    )

    if not urgency_rule_db:
        raise NotFoundError(f"Urgency Rule ID `{urgency_rule_id}` not found")
    return urgency_rule_db


async def create_urgency_rule(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    urgency_rule: UrgencyRuleCreate,
    workspace_name: str,
) -> UrgencyRuleRetrieve:
    """Create a new urgency rule. Only workspace admins may do this.

    Must run inside a Langfuse-observed call: it tags the current trace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user creating the urgency rule.
    urgency_rule
        The urgency rule to create.
    workspace_name
        The name of the workspace to create the urgency rule in.

    Returns
    -------
    UrgencyRuleRetrieve
        The created urgency rule.

    Raises
    ------
    ForbiddenError
        If the user is not an admin in the workspace.
    AppError
        (502) If embedding the rule text fails.
    """

    workspace_db = await _get_workspace_as_admin(
        action="create",
        asession=asession,
        calling_user_db=calling_user_db,
        workspace_name=workspace_name,
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
        raise AppError(
            _EMBEDDING_ERROR_DETAIL, status_code=_HTTP_502_BAD_GATEWAY
        ) from e
    return _convert_record_to_schema(urgency_rule_db=urgency_rule_db)


async def get_urgency_rule(
    *, asession: AsyncSession, urgency_rule_id: int, workspace_name: str
) -> UrgencyRuleRetrieve:
    """Get a single urgency rule by ID.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    urgency_rule_id
        The ID of the urgency rule to retrieve.
    workspace_name
        The name of the workspace to retrieve the urgency rule from.

    Returns
    -------
    UrgencyRuleRetrieve
        The urgency rule.

    Raises
    ------
    NotFoundError
        If the urgency rule with the given ID does not exist.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    urgency_rule_db = await _get_existing_urgency_rule(
        asession=asession,
        urgency_rule_id=urgency_rule_id,
        workspace_id=workspace_db.workspace_id,
    )
    return _convert_record_to_schema(urgency_rule_db=urgency_rule_db)


async def delete_urgency_rule(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    urgency_rule_id: int,
    workspace_name: str,
) -> None:
    """Delete a single urgency rule by ID. Only workspace admins may do this.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user deleting the urgency rule.
    urgency_rule_id
        The ID of the urgency rule to delete.
    workspace_name
        The name of the workspace to delete the urgency rule from.

    Raises
    ------
    ForbiddenError
        If the user is not an admin in the workspace.
    NotFoundError
        If the urgency rule with the given ID does not exist.
    """

    workspace_db = await _get_workspace_as_admin(
        action="delete",
        asession=asession,
        calling_user_db=calling_user_db,
        workspace_name=workspace_name,
    )
    workspace_id = workspace_db.workspace_id
    await _get_existing_urgency_rule(
        asession=asession, urgency_rule_id=urgency_rule_id, workspace_id=workspace_id
    )
    await delete_urgency_rule_from_db(
        asession=asession, urgency_rule_id=urgency_rule_id, workspace_id=workspace_id
    )


async def update_urgency_rule(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    urgency_rule: UrgencyRuleCreate,
    urgency_rule_id: int,
    workspace_name: str,
) -> UrgencyRuleRetrieve:
    """Update a single urgency rule by ID. Only workspace admins may do this.

    Must run inside a Langfuse-observed call: it tags the current trace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user updating the urgency rule.
    urgency_rule
        The updated urgency rule object.
    urgency_rule_id
        The ID of the urgency rule to update.
    workspace_name
        The name of the workspace to update the urgency rule in.

    Returns
    -------
    UrgencyRuleRetrieve
        The updated urgency rule.

    Raises
    ------
    ForbiddenError
        If the user is not an admin in the workspace.
    NotFoundError
        If the urgency rule with the given ID does not exist.
    AppError
        (502) If embedding the rule text fails.
    """

    workspace_db = await _get_workspace_as_admin(
        action="update",
        asession=asession,
        calling_user_db=calling_user_db,
        workspace_name=workspace_name,
    )
    workspace_id = workspace_db.workspace_id
    await _get_existing_urgency_rule(
        asession=asession, urgency_rule_id=urgency_rule_id, workspace_id=workspace_id
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
        raise AppError(
            _EMBEDDING_ERROR_DETAIL, status_code=_HTTP_502_BAD_GATEWAY
        ) from e
    return _convert_record_to_schema(urgency_rule_db=urgency_rule_db)


async def get_urgency_rules(
    *, asession: AsyncSession, workspace_name: str
) -> list[UrgencyRuleRetrieve]:
    """Get all urgency rules in a workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_name
        The name of the workspace to retrieve urgency rules from.

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
