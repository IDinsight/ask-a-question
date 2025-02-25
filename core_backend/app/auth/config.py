"""This module contains configuration settings for the auth package."""

import os

ACCESS_TOKEN_EXPIRE_MINUTES = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-secret")
NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID = os.environ.get(
    "NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID",
    "update-me",
)
REDIS_KEY_EXPIRED = -2
