"""This module contains the business logic for workspace endpoints: role checks,
workspace creation/update rules, API key rotation, and workspace switching.

Functions here never raise `HTTPException`; they raise the domain exceptions in
`app.core.exceptions`, which the global handler turns into the same HTTP responses.
"""

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import AuthenticationDetails
from app.auth.service import build_authentication_details
from app.core.config import (
    DEFAULT_API_QUOTA,
    DEFAULT_CONTENT_QUOTA,
    DEFAULT_DOC_LANGUAGE,
)
from app.core.exceptions import (
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
)
from app.core.observability import setup_logger
from app.core.security import generate_key
from app.question_answer.schemas import IdentifiedLanguage
from app.users.models import UserDB
from app.users.repository import (
    UserNotFoundError,
    add_existing_user_to_workspace,
    check_if_user_has_default_workspace,
    get_user_by_id,
    get_user_role_in_workspace,
    get_user_workspaces,
    get_workspaces_by_user_role,
    user_has_admin_role_in_any_workspace,
)
from app.users.schemas import UserCreate, UserRoles
from app.workspaces.models import WorkspaceDB
from app.workspaces.repository import (
    WorkspaceNotFoundError,
    create_workspace,
    get_workspace_by_workspace_id,
    get_workspace_by_workspace_name,
    is_workspace_name_valid,
    update_workspace_api_key,
    update_workspace_attrs,
)
from app.workspaces.schemas import (
    WorkspaceCreate,
    WorkspaceKeyResponse,
    WorkspaceRetrieve,
    WorkspaceUpdate,
)

logger = setup_logger()


def convert_workspace_db_to_schema(*, workspace_db: WorkspaceDB) -> WorkspaceRetrieve:
    """Convert a `WorkspaceDB` record into the `WorkspaceRetrieve` response model.

    Parameters
    ----------
    workspace_db
        The workspace record.

    Returns
    -------
    WorkspaceRetrieve
        The workspace response model.
    """

    return WorkspaceRetrieve(
        api_daily_quota=workspace_db.api_daily_quota,
        api_key_first_characters=workspace_db.api_key_first_characters,
        api_key_updated_datetime_utc=workspace_db.api_key_updated_datetime_utc,
        content_quota=workspace_db.content_quota,
        created_datetime_utc=workspace_db.created_datetime_utc,
        doc_language=workspace_db.doc_language,
        updated_datetime_utc=workspace_db.updated_datetime_utc,
        workspace_id=workspace_db.workspace_id,
        workspace_name=workspace_db.workspace_name,
    )


async def _check_user_is_admin_in_any_workspace(
    *, asession: AsyncSession, calling_user_db: UserDB
) -> None:
    """Ensure the calling user is an ADMIN in at least one workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the calling user.

    Raises
    ------
    ForbiddenError
        If the calling user does not have the correct role to retrieve workspaces.
    """

    if not await user_has_admin_role_in_any_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise ForbiddenError(
            "Calling user does not have the correct role to retrieve workspaces."
        )


async def create_workspaces(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    workspaces: WorkspaceCreate | list[WorkspaceCreate],
) -> list[WorkspaceRetrieve]:
    """Create workspaces on behalf of the calling user.

    NB: When a workspace is created, the API daily quota and content quota limits for
    the workspace is set to global defaults regardless of what the user specifies.

    The process is as follows:

    1. Create each workspace. If a workspace already exists during this process, an
        error is NOT thrown. Instead, the existing workspace object is NOT returned to
        the calling user. This avoids the need to iterate thru the list of workspaces
        first and does not give the calling user information on workspace existence.
    2. If a new workspace was created, then the calling user is automatically added as
        an ADMIN user to the workspace. Otherwise, the calling user is not added and
        they would have to contact the admin of the (existing) workspace to be added.
        2a. We do NOT assign the calling user to any of the newly created workspaces
        because existing users must already have a default workspace assigned and we
        don't want to override their current default workspace when creating new
        workspaces.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is creating the workspace(s).
    workspaces
        The workspace object (or list of workspace objects) to create.

    Returns
    -------
    list[WorkspaceRetrieve]
        A list of created workspace objects.

    Raises
    ------
    ForbiddenError
        If the calling user does not have a default workspace assigned.
    """

    if not await check_if_user_has_default_workspace(
        asession=asession, user_db=calling_user_db
    ):
        raise ForbiddenError(
            "Calling user must be assigned to a workspace first before creating "
            "workspaces."
        )

    if not isinstance(workspaces, list):
        workspaces = [workspaces]
    created_workspaces: list[WorkspaceRetrieve] = []

    for workspace in workspaces:
        # 1.
        workspace_db, is_new_workspace = await create_workspace(
            api_daily_quota=DEFAULT_API_QUOTA,  # workspace.api_daily_quota,
            asession=asession,
            content_quota=DEFAULT_CONTENT_QUOTA,  # workspace.content_quota,
            doc_language=DEFAULT_DOC_LANGUAGE,
            user=UserCreate(
                role=UserRoles.ADMIN,
                username=calling_user_db.username,
                workspace_name=workspace.workspace_name,
            ),
        )

        # 2.
        if is_new_workspace:
            await add_existing_user_to_workspace(
                asession=asession,
                user=UserCreate(
                    is_default_workspace=False,  # 2a.
                    role=UserRoles.ADMIN,
                    username=calling_user_db.username,
                    workspace_name=workspace_db.workspace_name,
                ),
                workspace_db=workspace_db,
            )
            created_workspaces.append(
                convert_workspace_db_to_schema(workspace_db=workspace_db)
            )

    return created_workspaces


async def retrieve_admin_workspaces(
    *, asession: AsyncSession, calling_user_db: UserDB
) -> list[WorkspaceRetrieve]:
    """Return the workspaces in which the calling user is an ADMIN.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user retrieving the workspaces.

    Returns
    -------
    list[WorkspaceRetrieve]
        A list of retrieved workspace objects.

    Raises
    ------
    ForbiddenError
        If the calling user does not have the correct role to retrieve workspaces.
    """

    await _check_user_is_admin_in_any_workspace(
        asession=asession, calling_user_db=calling_user_db
    )

    calling_user_admin_workspace_dbs = await get_workspaces_by_user_role(
        asession=asession, user_db=calling_user_db, user_role=UserRoles.ADMIN
    )

    return [
        convert_workspace_db_to_schema(workspace_db=workspace_db)
        for workspace_db in calling_user_admin_workspace_dbs
    ]


async def retrieve_workspace_by_name(
    *, asession: AsyncSession, workspace_name: str
) -> WorkspaceRetrieve:
    """Return the workspace with the given name.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    workspace_name
        The name of the workspace to retrieve.

    Returns
    -------
    WorkspaceRetrieve
        The workspace object.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    return convert_workspace_db_to_schema(workspace_db=workspace_db)


async def retrieve_admin_workspace_by_id(
    *, asession: AsyncSession, calling_user_db: UserDB, workspace_id: int
) -> WorkspaceRetrieve:
    """Return a workspace by ID, provided the calling user is an ADMIN in it.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user retrieving the workspace.
    workspace_id
        The workspace ID to retrieve.

    Returns
    -------
    WorkspaceRetrieve
        The retrieved workspace object.

    Raises
    ------
    ForbiddenError
        If the calling user does not have the correct role to retrieve workspaces.
        If the calling user is not an admin in the specified workspace.
    """

    await _check_user_is_admin_in_any_workspace(
        asession=asession, calling_user_db=calling_user_db
    )

    calling_user_admin_workspace_dbs = await get_workspaces_by_user_role(
        asession=asession, user_db=calling_user_db, user_role=UserRoles.ADMIN
    )
    matched_workspace_db = next(
        (
            workspace_db
            for workspace_db in calling_user_admin_workspace_dbs
            if workspace_db.workspace_id == workspace_id
        ),
        None,
    )

    if matched_workspace_db is None:
        raise ForbiddenError("Calling user is not an admin in the workspace.")

    return convert_workspace_db_to_schema(workspace_db=matched_workspace_db)


async def retrieve_user_workspaces_for_admin(
    *, asession: AsyncSession, calling_user_db: UserDB, user_id: int
) -> list[WorkspaceRetrieve]:
    """Return the workspaces of a user that the calling user is an ADMIN of.

    The process is as follows:

    1. Only retrieve workspaces for which the calling user has an ADMIN role.
    2. If the calling user is an admin in the same workspace as the user, then details
        for that workspace are returned.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user retrieving the workspaces.
    user_id
        The user ID to retrieve workspaces for.

    Returns
    -------
    list[WorkspaceRetrieve]
        A list of workspace objects that the user belongs to.

    Raises
    ------
    ForbiddenError
        If the calling user does not have the correct role to retrieve workspaces.
        If the calling user is not an admin in the same workspace as the user.
    NotFoundError
        If the user ID does not exist.
    """

    await _check_user_is_admin_in_any_workspace(
        asession=asession, calling_user_db=calling_user_db
    )

    try:
        user_db = await get_user_by_id(asession=asession, user_id=user_id)
    except UserNotFoundError as e:
        raise NotFoundError(f"User ID {user_id} not found.") from e

    # 1.
    calling_user_admin_workspace_dbs = await get_workspaces_by_user_role(
        asession=asession, user_db=calling_user_db, user_role=UserRoles.ADMIN
    )

    # 2.
    user_workspace_dbs = await get_user_workspaces(asession=asession, user_db=user_db)
    calling_user_admin_workspace_ids = [
        db.workspace_id for db in calling_user_admin_workspace_dbs
    ]

    retrieved_workspaces: list[WorkspaceRetrieve] = [
        convert_workspace_db_to_schema(workspace_db=db)
        for db in user_workspace_dbs
        if db.workspace_id in calling_user_admin_workspace_ids
    ]
    if retrieved_workspaces:
        return retrieved_workspaces

    raise ForbiddenError(
        "Calling user is not an admin in the same workspace as the user."
    )


async def rotate_workspace_api_key(
    *, asession: AsyncSession, calling_user_db: UserDB, workspace_name: str
) -> WorkspaceKeyResponse:
    """Generate a new API key for the workspace and store its hash, replacing the old
    key. Only ADMIN users of the workspace may do this.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user requesting the new API key.
    workspace_name
        The name of the workspace requesting the new API key.

    Returns
    -------
    WorkspaceKeyResponse
        The response object containing the new API key.

    Raises
    ------
    ForbiddenError
        If the calling user does not have the correct role to request a new API key for
        the workspace.
    InternalServerError
        If there is an error updating the workspace API key.
    """

    workspace_db = await get_workspace_by_workspace_name(
        asession=asession, workspace_name=workspace_name
    )
    calling_user_workspace_role = await get_user_role_in_workspace(
        asession=asession, user_db=calling_user_db, workspace_db=workspace_db
    )

    if calling_user_workspace_role != UserRoles.ADMIN:
        raise ForbiddenError(
            "Calling user does not have the correct role to request a new API "
            "key for the workspace."
        )

    new_api_key = generate_key()

    try:
        # This is necessary to attach the `workspace_db` object to the session.
        asession.add(workspace_db)
        await asession.flush()
        workspace_db_updated = await update_workspace_api_key(
            asession=asession, new_api_key=new_api_key, workspace_db=workspace_db
        )
        return WorkspaceKeyResponse(
            new_api_key=new_api_key, workspace_name=workspace_db_updated.workspace_name
        )
    except SQLAlchemyError as e:
        logger.error(f"Error updating workspace API key: {e}")
        raise InternalServerError("Error updating workspace API key.") from e


async def switch_user_workspace(
    *, asession: AsyncSession, calling_user_db: UserDB, workspace_name: str
) -> AuthenticationDetails:
    """Issue a new access token scoped to another workspace the user belongs to.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user switching workspaces.
    workspace_name
        The name of the workspace to switch into.

    Returns
    -------
    AuthenticationDetails
        The authentication details object containing the new access token.

    Raises
    ------
    BadRequestError
        If the workspace to switch into does not exist (for this user).
    InternalServerError
        If the calling user's role in the workspace to switch into is not valid.
    """

    username = calling_user_db.username
    user_workspace_dbs = await get_user_workspaces(
        asession=asession, user_db=calling_user_db
    )
    user_workspace_db = next(
        (db for db in user_workspace_dbs if db.workspace_name == workspace_name), None
    )

    if user_workspace_db is None:
        raise BadRequestError(
            f"Workspace with workspace name '{workspace_name}' not found."
        )

    user_role = await get_user_role_in_workspace(
        asession=asession, user_db=calling_user_db, workspace_db=user_workspace_db
    )

    if user_role is None or user_role not in UserRoles:
        raise InternalServerError("Invalid user role when switching to workspace.")

    # Hardcode "fullaccess" now, but may use it in the future.
    return build_authentication_details(
        access_level="fullaccess",
        user_role=user_role,
        username=username,
        workspace_name=workspace_name,
    )


async def update_workspace(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    workspace: WorkspaceUpdate,
    workspace_id: int,
) -> WorkspaceUpdate:
    """Validate and apply an update to an existing workspace.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user updating the workspace.
    workspace
        The workspace object with the updated information.
    workspace_id
        The workspace ID to update.

    Returns
    -------
    WorkspaceUpdate
        The updated workspace object.

    Raises
    ------
    BadRequestError
        If no valid updates are provided or the new workspace name already exists.
    NotFoundError
        If the workspace to update does not exist.
    ForbiddenError
        If the calling user is not an admin in the workspace.
    InternalServerError
        If there is an error updating the workspace.
    """

    workspace_db_checked = await check_update_workspace_call(
        asession=asession,
        calling_user_db=calling_user_db,
        workspace=workspace,
        workspace_id=workspace_id,
    )

    try:
        # This is necessary to attach the `workspace_db` object to the session.
        asession.add(workspace_db_checked)
        await asession.flush()
        workspace_db_updated = await update_workspace_attrs(
            asession=asession, workspace=workspace, workspace_db=workspace_db_checked
        )
        new_api_daily_quota = (
            workspace_db_checked.api_daily_quota
            if workspace_db_updated.api_daily_quota
            == workspace_db_checked.api_daily_quota
            else workspace_db_updated.api_daily_quota
        )
        new_content_quota = (
            workspace_db_checked.content_quota
            if workspace_db_updated.content_quota == workspace_db_checked.content_quota
            else workspace_db_updated.content_quota
        )
        new_doc_language = (
            workspace_db_checked.doc_language
            if workspace_db_updated.doc_language == workspace_db_checked.doc_language
            else workspace_db_updated.doc_language
        )
        new_workspace_name = (
            workspace_db_checked.workspace_name
            if workspace_db_updated.workspace_name
            == workspace_db_checked.workspace_name
            else workspace_db_updated.workspace_name
        )
        return WorkspaceUpdate(
            api_daily_quota=new_api_daily_quota,
            content_quota=new_content_quota,
            doc_language=new_doc_language,
            workspace_name=new_workspace_name,
        )
    except SQLAlchemyError as e:
        logger.error(f"Error updating workspace information: {e}")
        raise InternalServerError("Error updating workspace information.") from e


async def check_update_workspace_call(
    *,
    asession: AsyncSession,
    calling_user_db: UserDB,
    workspace: WorkspaceUpdate,
    workspace_id: int,
) -> WorkspaceDB:
    """Check the workspace update call to ensure the action is allowed.

    Parameters
    ----------
    asession
        The SQLAlchemy async session to use for all database connections.
    calling_user_db
        The user object associated with the user that is updating the workspace.
    workspace
        The workspace object with the updated information.
    workspace_id
        The workspace ID to update.

    Returns
    -------
    WorkspaceDB
        The workspace object to update.

    Raises
    ------
    BadRequestError
        If no valid updates are provided for the workspace.
        If the workspace name is not valid.
    NotFoundError
        If the workspace to update does not exist.
    ForbiddenError
        If the calling user is not an admin in the workspace.
    """

    api_daily_quota = workspace.api_daily_quota
    content_quota = workspace.content_quota
    doc_language = workspace.doc_language
    workspace_name = workspace.workspace_name

    updating_api_daily_quota = api_daily_quota is None or api_daily_quota >= 0
    updating_content_quota = content_quota is None or content_quota >= 0
    updating_doc_language = doc_language in IdentifiedLanguage.get_supported_languages()

    if not any(
        [
            updating_api_daily_quota,
            updating_content_quota,
            updating_doc_language,
            workspace_name is not None,
        ]
    ):
        raise BadRequestError("No valid updates provided for the workspace.")

    try:
        workspace_db = await get_workspace_by_workspace_id(
            asession=asession, workspace_id=workspace_id
        )
    except WorkspaceNotFoundError as e:
        raise NotFoundError(f"Workspace ID {workspace_id} not found.") from e

    if (
        workspace_name is not None
        and workspace_name != workspace_db.workspace_name
        and not await is_workspace_name_valid(
            asession=asession, workspace_name=workspace_name
        )
    ):
        raise BadRequestError(
            f"Workspace with workspace name {workspace_name} already exists."
        )

    calling_user_workspace_role = await get_user_role_in_workspace(
        asession=asession, user_db=calling_user_db, workspace_db=workspace_db
    )

    if calling_user_workspace_role != UserRoles.ADMIN:
        raise ForbiddenError("Calling user is not an admin in the workspace.")

    return workspace_db
