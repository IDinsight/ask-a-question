"""This module contains FastAPI routers for user authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.requests import Request
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import DEFAULT_API_QUOTA, DEFAULT_CONTENT_QUOTA
from ..database import get_sqlalchemy_async_engine
from ..users.models import (
    UserNotFoundError,
    create_user_workspace_role,
    get_user_by_username,
    save_user_to_db,
)
from ..users.schemas import UserCreate, UserRoles
from ..utils import update_api_limits
from ..workspaces.utils import (
    WorkspaceNotFoundError,
    create_workspace,
    get_workspace_by_workspace_name,
)
from .config import NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID
from .dependencies import (
    authenticate_credentials,
    authenticate_workspace,
    create_access_token,
)
from .schemas import (
    AuthenticatedUser,
    AuthenticationDetails,
    GoogleLoginData,
    WorkspaceLogin,
)

TAG_METADATA = {
    "name": "Authentication",
    "description": "_Requires user login._ Endpoints for authenticating user and "
    "workspace logins.",
}

router = APIRouter(tags=[TAG_METADATA["name"]])


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> AuthenticationDetails:
    """Login route for users to authenticate and receive a JWT token.

    Parameters
    ----------
    form_data
        Form data containing username and password.

    Returns
    -------
    AuthenticationDetails
        A Pydantic model containing the JWT token, token type, access level, and
        username.

    Raises
    ------
    HTTPException
        If the user credentials are invalid.
    """

    authenticate_user = await authenticate_credentials(
        password=form_data.password, username=form_data.username
    )

    if authenticate_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials."
        )

    return AuthenticationDetails(
        access_level=authenticate_user.access_level,
        access_token=create_access_token(
            username=authenticate_user.username,
            workspace_name=authenticate_user.workspace_name,
        ),
        token_type="bearer",
        username=authenticate_user.username,
        workspace_name=authenticate_user.workspace_name,
    )


@router.post("/login-google")
async def login_google(
    request: Request, login_data: GoogleLoginData
) -> AuthenticationDetails:
    """Verify Google token and check if user exists. If user does not exist, create
    user and return JWT token for the user.

    NB: When a user logs in with Google, the user is assigned the role of ADMIN by
    default. Otherwise, the user should be created by an admin of an existing workspace
    and assigned a role within that workspace.

    Parameters
    ----------
    request
        The request object.
    login_data
        A Pydantic model containing the Google token.

    Returns
    -------
    AuthenticationDetails
        A Pydantic model containing the JWT token, token type, access level, and
        username.

    Raises
    ------
    ValueError
        If the Google token is invalid.
    HTTPException
        If the workspace requested by the Google user already exists.
        If the Google token is invalid.
        If the Google user belongs to multiple workspaces.
    """

    try:
        idinfo = id_token.verify_oauth2_token(
            login_data.credential,
            requests.Request(),
            NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID,
        )
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        ) from e

    authenticate_user = await authenticate_or_create_google_user(
        gmail=idinfo["email"], request=request
    )
    return AuthenticationDetails(
        access_level=authenticate_user.access_level,
        access_token=create_access_token(
            username=authenticate_user.username,
            workspace_name=authenticate_user.workspace_name,
        ),
        token_type="bearer",
        username=authenticate_user.username,
    )


async def authenticate_or_create_google_user(
    *, gmail: str, request: Request
) -> AuthenticatedUser:
    """Authenticate or create a Google user. A Google user can belong to multiple
    workspaces (e.g., if the admin of a workspace adds the Google user to their
    workspace with the gmail as the username). However, if a Google user registers,
    then a unique workspace is created for the Google user using their gmail.

    NB: Creating workspaces for Google users must happen in this module instead of
    `auth.dependencies` due to circular imports.

    Parameters
    ----------
    gmail
        The Gmail address of the Google user.
    request
        The request object.

    Returns
    -------
    AuthenticatedUser
        A Pydantic model containing the access level, username, and workspace name.
    """

    workspace_name = f"Workspace_{gmail}"

    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        try:
            # If the workspace already exists, then the Google user should have already
            # been created.
            _ = await get_workspace_by_workspace_name(
                asession=asession, workspace_name=workspace_name
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workspace for '{gmail}' already exists. Contact the admin of "
                f"that workspace to create an account for you.",
            )
        except WorkspaceNotFoundError:
            # Create the new user object with an ADMIN role and the specified workspace
            # name.
            user = UserCreate(
                role=UserRoles.ADMIN,
                username=gmail,
                workspace_name=workspace_name,
            )

            # Create the workspace for the Google user.
            workspace_db, _ = await create_workspace(
                api_daily_quota=DEFAULT_API_QUOTA,
                asession=asession,
                content_quota=DEFAULT_CONTENT_QUOTA,
                user=user,
            )

            # Update API limits for the Google user's workspace.
            await update_api_limits(
                api_daily_quota=workspace_db.api_daily_quota,
                redis=request.app.state.redis,
                workspace_name=workspace_db.workspace_name,
            )

            try:
                # Check if the user already exists.
                user_db = await get_user_by_username(
                    asession=asession, username=user.username
                )
            except UserNotFoundError:
                # Save the user to the `UserDB` database.
                user_db = await save_user_to_db(asession=asession, user=user)

            # Assign user to the specified workspace with the specified role.
            assert user.role is not None
            _ = await create_user_workspace_role(
                asession=asession,
                is_default_workspace=True,
                user_db=user_db,
                user_role=user.role,
                workspace_db=workspace_db,
            )

            return AuthenticatedUser(
                access_level="fullaccess",
                username=user_db.username,
                workspace_name=workspace_name,
            )


@router.post("/login-workspace")
async def login_workspace(workspace_login: WorkspaceLogin) -> AuthenticationDetails:
    """Login route for users to authenticate into a workspace and receive a JWT token.

    NB: This endpoint does NOT take the user's password for authentication. This is
    because a user should first be authenticated using username and password before
    they are allowed to log into a workspace.

    Parameters
    ----------
    workspace_login
        The workspace login object containing the username and workspace name to log
        into.

    Returns
    -------
    AuthenticationDetails
        A Pydantic model containing the JWT token, token type, access level, and
        username.

    Raises
    ------
    HTTPException
        If the user credentials are invalid.
    """

    authenticate_user = await authenticate_workspace(workspace_login=workspace_login)

    if authenticate_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials."
        )

    return AuthenticationDetails(
        access_level=authenticate_user.access_level,
        access_token=create_access_token(
            username=authenticate_user.username,
            workspace_name=authenticate_user.workspace_name,
        ),
        workspace_name=authenticate_user.workspace_name,
        token_type="bearer",
        username=authenticate_user.username,
    )
