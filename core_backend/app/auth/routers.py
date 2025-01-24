"""This module contains FastAPI routers for user authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.requests import Request
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests
from google.oauth2 import id_token

from .config import NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID
from .dependencies import (
    authenticate_credentials,
    authenticate_or_create_google_user,
    create_access_token,
)
from .schemas import AuthenticationDetails, GoogleLoginData

TAG_METADATA = {
    "name": "Authentication",
    "description": "_Requires user login._ Endpoints for authenticating user logins.",
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
        If the username or password is incorrect.
    """

    user = await authenticate_credentials(
        password=form_data.password, username=form_data.username
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    return AuthenticationDetails(
        access_level=user.access_level,
        access_token=create_access_token(
            username=user.username, workspace_name=user.workspace_name
        ),
        token_type="bearer",
        username=user.username,
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
        If the workspace requested by the Google user already exists or if the Google
        token is invalid.
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

    gmail = idinfo["email"]
    user = await authenticate_or_create_google_user(google_email=gmail, request=request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workspace for '{gmail}' already exists. Contact the admin of that "
            f"workspace to create an account for you."
        )

    return AuthenticationDetails(
        access_level=user.access_level,
        access_token=create_access_token(
            username=user.username, workspace_name=user.workspace_name
        ),
        token_type="bearer",
        username=user.username,
    )
