from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests
from google.oauth2 import id_token

from .dependencies import (
    authenticate_credentials,
    authenticate_or_create_google_user,
    create_access_token,
)
from .schemas import GoogleLoginData

router = APIRouter(tags=["Authentication"])

CLIENT_ID = "546420096809-5n9dinjpofivh6m54pm5hmki7vbtec3u.apps.googleusercontent.com"


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    """
    Login route for users to authenticate and receive a JWT token.
    """
    user = await authenticate_credentials(
        username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password",
        )

    return {
        "access_token": create_access_token(user.username),
        "token_type": "bearer",
        "access_level": user.access_level,
        "username": user.username,
    }


@router.post("/login-google")
async def login_google(login_data: GoogleLoginData) -> dict:
    """
    Verify google token, check if user exists. If user does not exist, create user
    Return JWT token for user
    """

    try:
        idinfo = id_token.verify_oauth2_token(
            login_data.credential, requests.Request(), CLIENT_ID
        )
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid token") from e

    user = await authenticate_or_create_google_user(google_email=idinfo["email"])
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Unable to create new user",
        )

    return {
        "access_token": create_access_token(user.username),
        "token_type": "bearer",
        "access_level": user.access_level,
        "username": user.username,
    }
