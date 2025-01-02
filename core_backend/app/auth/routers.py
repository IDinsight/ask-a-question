from fastapi import APIRouter, Depends, HTTPException
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
    """
    Login route for users to authenticate and receive a JWT token.
    """
    user = await authenticate_credentials(
        username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    return AuthenticationDetails(
        access_token=create_access_token(user.username),
        token_type="bearer",
        access_level=user.access_level,
        username=user.username,
        is_admin=user.is_admin,
    )


@router.post("/login-google")
async def login_google(
    request: Request, login_data: GoogleLoginData
) -> AuthenticationDetails:
    """
    Verify google token, check if user exists. If user does not exist, create user
    Return JWT token for user
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
        raise HTTPException(status_code=401, detail="Invalid token") from e

    user = await authenticate_or_create_google_user(
        request=request, google_email=idinfo["email"]
    )
    if not user:
        raise HTTPException(
            status_code=500,
            detail="Unable to create new user",
        )

    return AuthenticationDetails(
        access_token=create_access_token(user.username),
        token_type="bearer",
        access_level=user.access_level,
        username=user.username,
        is_admin=user.is_admin,
    )
