"""This module contains the FastAPI router for user authentication endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.requests import Request
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests
from google.oauth2 import id_token

from ..users.schemas import UserRoles
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
            detail="Incorrect username or password",
        )
    return AuthenticationDetails(
        access_level=user.access_level,
        access_token=create_access_token(user.username),
        token_type="bearer",
        username=user.username,
        is_admin=True,  # Hack fix for frontend
    )


@router.post("/login-google")
async def login_google(
    request: Request,
    login_data: GoogleLoginData,
    user_role: UserRoles = UserRoles.ADMIN,
    workspace_name: Optional[str] = None,
) -> AuthenticationDetails:
    """Verify Google token and check if user exists. If user does not exist, create
    user and return JWT token for user

    Parameters
    ----------
    request
        The request object.
    login_data
        A Pydantic model containing the Google token.
    user_role
        The user role to assign to the Google login user. If not specified, the default
        user role is ADMIN.
    workspace_name
        The workspace name to create for the Google login user. If not specified, then
        the default workspace name is the next available workspace ID.

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
        If the Google token is invalid or if a new user cannot be created.
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
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from e

    user = await authenticate_or_create_google_user(
        google_email=idinfo["email"],
        request=request,
        user_role=user_role,
        workspace_name=workspace_name,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create new user",
        )

    return AuthenticationDetails(
        access_level=user.access_level,
        access_token=create_access_token(user.username),
        token_type="bearer",
        username=user.username,
        is_admin=True,  # Hack fix for frontend
    )
