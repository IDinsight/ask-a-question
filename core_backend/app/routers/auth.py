from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import authenticate_user, create_access_token

router = APIRouter()


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    """
    Login route for users to authenticate and receive a JWT token.
    """
    user = authenticate_user(username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(user.username),
        "token_type": "bearer",
        "access_level": user.access_level,
    }
