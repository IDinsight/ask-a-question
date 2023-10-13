from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .configs.app_config import QUESTION_ANSWER_SECRET

bearer = HTTPBearer()


def auth_bearer_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> None:
    """
    Authenticate using basic bearer token
    """
    token = credentials.credentials
    if token != QUESTION_ANSWER_SECRET:
        raise HTTPException(status_code=401, detail="Invalid bearer token")
