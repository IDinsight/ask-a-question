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
    get_user_default_workspace,
    get_user_role_in_workspace,
    save_user_to_db,
)
from ..users.schemas import UserCreate, UserRoles
from ..utils import update_api_limits
from ..workspaces.utils import create_workspace
from .config import NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID
from .dependencies import authenticate_credentials, create_access_token
from .schemas import AuthenticatedUser, AuthenticationDetails, GoogleLoginData

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

    authenticated_user = await authenticate_credentials(
        password=form_data.password, username=form_data.username
    )

    if authenticated_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials."
        )

    user_role = authenticated_user.user_role
    username = authenticated_user.username
    workspace_name = authenticated_user.workspace_name
    return AuthenticationDetails(
        access_level=authenticated_user.access_level,
        access_token=create_access_token(
            user_role=user_role, username=username, workspace_name=workspace_name
        ),
        token_type="bearer",
        user_role=user_role,
        username=username,
        workspace_name=workspace_name,
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

    authenticated_user = await authenticate_or_create_google_user(
        gmail=idinfo["email"], request=request
    )

    user_role = authenticated_user.user_role
    username = authenticated_user.username
    workspace_name = authenticated_user.workspace_name
    return AuthenticationDetails(
        access_level=authenticated_user.access_level,
        access_token=create_access_token(
            user_role=user_role,
            username=username,
            workspace_name=workspace_name,
        ),
        token_type="bearer",
        user_role=user_role,
        username=username,
        workspace_name=workspace_name,
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

    The process is as follows:

    1. The default workspace name for Google users is f"{gmail}'s Workspace" (and the
        default username is the gmail, and the default role is ADMIN).
    2. Check if the user exists in `UserDB`.
    3. If the username already exists in `UserDB`, then a default workspace should
        have already been associated with the user.
    4. Check the user role in the workspace. If the authenticating user exists in the
       workspace, then we return the`AuthenticatedUser` model with the correct user's
       role in the workspace.
    5. If the user does not exist in `UserDB`, then this is the first time that the
        Google user is authenticating.
    6. We try to create the workspace using the default workspace name for the new
        user. If the default workspace name already exists, then we raise an exception.
        This corresponds to the situation where another user has already created a
        workspace under the same name and the Google user is signing in for the very
        time.
    7. Finally, we update the API limits for the new workspace, create the user in
        `UserDB`, and assign the user to the workspace with the role of ADMIN.

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

    Raises
    ------
    HTTPException
        If the workspace requested by the Google user already exists.
        If the Google token is invalid.
    """

    # 1.
    workspace_name = f"{gmail}'s Workspace"

    async with AsyncSession(
        get_sqlalchemy_async_engine(), expire_on_commit=False
    ) as asession:
        # 2.
        try:
            user_db = await get_user_by_username(asession=asession, username=gmail)
        except UserNotFoundError:
            user_db = None

        if user_db is not None:
            # 3.
            workspace_db = await get_user_default_workspace(
                asession=asession, user_db=user_db
            )

            # 4.
            user_role = await get_user_role_in_workspace(
                asession=asession, user_db=user_db, workspace_db=workspace_db
            )
            assert user_role is not None and user_role in UserRoles, f"{user_role = }"
            return AuthenticatedUser(
                access_level="fullaccess",
                user_role=user_role,
                username=user_db.username,
                workspace_name=workspace_db.workspace_name,
            )

        # 5.
        user = UserCreate(
            role=UserRoles.ADMIN, username=gmail, workspace_name=workspace_name
        )
        user_role = user.role
        assert user_role is not None and user_role in UserRoles

        # 6.
        workspace_db, is_new_workspace = await create_workspace(
            api_daily_quota=DEFAULT_API_QUOTA,
            asession=asession,
            content_quota=DEFAULT_CONTENT_QUOTA,
            user=user,
        )
        if not is_new_workspace:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workspace for '{gmail}' already exists. Contact the admin of "
                f"that workspace to create an account for you.",
            )

        # 7.
        await update_api_limits(
            api_daily_quota=workspace_db.api_daily_quota,
            redis=request.app.state.redis,
            workspace_name=workspace_db.workspace_name,
        )
        user_db = await save_user_to_db(asession=asession, user=user)
        _ = await create_user_workspace_role(
            asession=asession,
            is_default_workspace=True,
            user_db=user_db,
            user_role=user_role,
            workspace_db=workspace_db,
        )

        return AuthenticatedUser(
            access_level="fullaccess",
            user_role=user_role,
            username=user_db.username,
            workspace_name=workspace_name,
        )
