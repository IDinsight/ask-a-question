"""Security helpers: API keys, password hashing, JWT tokens, recovery codes and
Redis-backed daily API quotas."""

import hashlib
import os
import random
import secrets
import string
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from redis import asyncio as aioredis

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET,
)
from app.users.schemas import UserRoles

# ---- from core/security
# pylint: disable=global-statement



# To make 32-byte API keys (results in 43 characters).
SECRET_KEY_N_BYTES = 32


def generate_key() -> str:
    """Generate API key (default 32 byte = 43 characters).

    Returns
    -------
    str
        The generated API key.
    """

    return secrets.token_urlsafe(SECRET_KEY_N_BYTES)






def generate_secret_key() -> str:
    """Generate a secret key for the user query.

    Returns
    -------
    str
        The generated secret key.
    """

    return uuid4().hex








def get_key_hash(*, key: str) -> str:
    """Hash the API key using SHA256.

    Parameters
    ----------
    key
        The API key to hash.

    Returns
    -------
    str
        The hashed API key.
    """

    return hashlib.sha256(key.encode()).hexdigest()




def get_password_salted_hash(*, key: str) -> str:
    """Hash the password using SHA256 with a salt.

    Parameters
    ----------
    key
        The password to hash.

    Returns
    -------
    str
        The hashed salted password.
    """

    salt = os.urandom(16)
    key_salt_combo = salt + key.encode()
    hash_obj = hashlib.sha256(key_salt_combo)
    return salt.hex() + hash_obj.hexdigest()


def get_random_int32() -> int:
    """Generate a random 32-bit integer.

    Returns
    -------
    int
        The generated 32-bit integer.
    """

    return random.randint(-(2**31), 2**31 - 1)


def get_random_string(*, size: int) -> str:
    """Generate a random string of fixed length.

    Parameters
    ----------
    size
        The size of the random string to generate.

    Returns
    -------
    str
        The generated random string.
    """

    return "".join(random.choices(string.ascii_letters + string.digits, k=size))






def verify_password_salted_hash(*, key: str, stored_hash: str) -> bool:
    """Verify if the API key matches the hash.

    Parameters
    ----------
    key
        The API key to verify.
    stored_hash
        The stored hash to compare against.

    Returns
    -------
    bool
        Specifies if the API key matches the hash.
    """

    salt = bytes.fromhex(stored_hash[:32])
    original_hash = stored_hash[32:]
    key_salt_combo = salt + key.encode()
    hash_obj = hashlib.sha256(key_salt_combo)

    return hash_obj.hexdigest() == original_hash


def generate_recovery_codes(*, code_length: int = 20, num_codes: int = 5) -> list[str]:
    """Generate recovery codes for a user.

    Parameters
    ----------
    code_length
        The length of each recovery code, by default 20.
    num_codes
        The number of recovery codes to generate, by default 5.

    Returns
    -------
    list[str]
        A list of recovery codes.
    """

    chars = string.ascii_letters + string.digits
    return [
        "".join(secrets.choice(chars) for _ in range(code_length))
        for _ in range(num_codes)
    ]


def create_access_token(
    *, user_role: UserRoles, username: str, workspace_name: str
) -> str:
    """Create an access token for the user.

    Parameters
    ----------
    user_role
        The role of the user.
    username
        The username of the user to create the access token for.
    workspace_name
        The name of the workspace selected for the user.

    Returns
    -------
    str
        The access token.
    """

    payload: dict[str, str | datetime] = {}
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload["exp"] = expire
    payload["iat"] = datetime.now(timezone.utc)
    payload["type"] = "access_token"
    payload["user_role"] = user_role
    payload["username"] = username
    payload["workspace_name"] = workspace_name

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ---- from core/rate_limit
def encode_api_limit(*, api_limit: int | None) -> int | str:
    """Encode the API limit for Redis.

    Parameters
    ----------
    api_limit
        The API limit.

    Returns
    -------
    int | str
        The encoded API limit.
    """

    return int(api_limit) if api_limit is not None else "None"


async def update_api_limits(
    *, api_daily_quota: int | None, redis: aioredis.Redis, workspace_name: str
) -> None:
    """Update the API limits for the workspace in Redis.

    Parameters
    ----------
    api_daily_quota
        The daily API quota for the workspace.
    redis
        The Redis instance.
    workspace_name
        The name of the workspace.
    """

    now = datetime.now(timezone.utc)
    next_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    key = f"remaining-calls:{workspace_name}"
    expire_at = int(next_midnight.timestamp())
    await redis.set(key, encode_api_limit(api_limit=api_daily_quota))
    if api_daily_quota is not None:
        await redis.expireat(key, expire_at)
