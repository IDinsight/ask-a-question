"""This module contains FastAPI routers for user authentication endpoints and the
authentication dependencies (used via `Depends`) shared by the other features.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)

from app.auth import service
from app.auth.schemas import AuthenticationDetails, GoogleLoginData
from app.users.models import UserDB
from app.workspaces.models import WorkspaceDB

TAG_METADATA = {
    "name": "Authentication",
    "description": "_Requires user login._ Endpoints for authenticating user and "
    "workspace logins.",
}

router = APIRouter(tags=[TAG_METADATA["name"]])

bearer = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# ---------------------------------------------------------------------------
# Dependencies (used via `Depends` by the routers of other features).
# ---------------------------------------------------------------------------


async def authenticate_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> WorkspaceDB:
    """Authenticate using basic bearer token. This is used by endpoints such as:

    1. Data API
    2. Question answering
    3. Urgency detection

    In case the JWT token is provided instead of the API key, it will fall back to the
    JWT token authentication.

    Parameters
    ----------
    credentials
        The bearer token.

    Returns
    -------
    WorkspaceDB
        The workspace object.

    Raises
    ------
    UnauthorizedError
        If the credentials are invalid.
    """

    return await service.get_workspace_by_api_key_or_jwt(token=credentials.credentials)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserDB:
    """Get the current user from the access token.

    NB: We have to check that both the username and workspace name are present in the
    payload. If either one is missing, then this corresponds to the situation where
    there are neither users nor workspaces present.

    Parameters
    ----------
    token
        The access token.

    Returns
    -------
    UserDB
        The user object.

    Raises
    ------
    UnauthorizedError
        If the credentials are invalid.
    """

    return await service.get_user_by_access_token(token=token)


async def get_current_workspace_name(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> str:
    """Get the current workspace name from the access token.

    NB: We have to check that both the username and workspace name are present in the
    payload. If either one is missing, then this corresponds to the situation where
    there are neither users nor workspaces present.

    NB: The workspace object cannot be retrieved in this module due to circular imports.
    Instead, the workspace name is retrieved from the payload and the caller is
    responsible for retrieving the workspace object.

    Parameters
    ----------
    token
        The access token.

    Returns
    -------
    str
        The workspace name.

    Raises
    ------
    UnauthorizedError
        If the credentials are invalid, or the user no longer exists or no longer
        belongs to the workspace in the token.
    """

    return await service.get_workspace_name_for_access_token(token=token)


async def rate_limiter(
    request: Request, workspace_db: WorkspaceDB = Depends(authenticate_key)
) -> None:
    """Rate limiter for the API calls. Gets daily quota and decrement it.

    This is used by the following packages:

    1. Question answering
    2. Urgency detection

    Parameters
    ----------
    request
        The request object.
    workspace_db
        The workspace object.

    Raises
    ------
    TooManyRequestsError
        If the API call limit is reached.
    """

    await service.consume_api_quota(
        redis=request.app.state.redis, workspace_db=workspace_db
    )


# ---------------------------------------------------------------------------
# Endpoints.
# ---------------------------------------------------------------------------


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

    return await service.login_with_credentials(
        password=form_data.password, username=form_data.username
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

    return await service.login_with_google(
        credential=login_data.credential, redis=request.app.state.redis
    )
