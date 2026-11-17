"""Security helpers: startup checks, API keys, password hashing, JWT tokens, recovery
codes, HTTP security headers, the /metrics guard and Redis-backed daily API quotas."""

import hashlib
import hmac
import re
import secrets
import string
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from redis import asyncio as aioredis
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET,
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_STORAGE_URI,
    RATE_LIMIT_TRUSTED_PROXY_HOPS,
    REFRESH_TOKEN_EXPIRE_MINUTES,
)
from app.users.schemas import UserRoles

# To make 32-byte API keys (results in 43 characters).
SECRET_KEY_N_BYTES = 32

# ---------------------------------------------------------------------------
# Startup configuration checks.
# ---------------------------------------------------------------------------

# Secrets that have been published in this repository (old default and env template).
# A deployment using any of them lets anyone forge access tokens.
KNOWN_INSECURE_JWT_SECRETS = frozenset({"", "jwt-secret"})
MIN_JWT_SECRET_LENGTH = 32
# Tokens are signed with a shared secret, so only HMAC algorithms make sense. Pinning
# the list also stops `JWT_ALGORITHM=none` or an asymmetric algorithm being configured.
ALLOWED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})


class InsecureConfigurationError(RuntimeError):
    """Raised at startup when a security-critical setting is missing or unsafe."""


def validate_security_settings(
    *,
    jwt_algorithm: str = JWT_ALGORITHM,
    jwt_secret: str = JWT_SECRET,
) -> None:
    """Refuse to start the app with settings that would let anyone forge tokens.

    Called once from `app.main` while the app is built, so a misconfigured deployment
    fails loudly at boot instead of running with a guessable signing key. There is
    deliberately no bypass flag: every environment, dev and tests included, must set
    a real secret.

    Parameters
    ----------
    jwt_algorithm
        The configured JWT signing algorithm.
    jwt_secret
        The configured JWT signing secret.

    Raises
    ------
    InsecureConfigurationError
        If the algorithm is not an allowed HMAC algorithm, or the secret is empty,
        published in this repository, or shorter than `MIN_JWT_SECRET_LENGTH`.
    """

    if jwt_algorithm not in ALLOWED_JWT_ALGORITHMS:
        raise InsecureConfigurationError(
            f"JWT_ALGORITHM must be one of {sorted(ALLOWED_JWT_ALGORITHMS)}."
        )

    if (
        jwt_secret in KNOWN_INSECURE_JWT_SECRETS
        or len(jwt_secret) < MIN_JWT_SECRET_LENGTH
    ):
        raise InsecureConfigurationError(
            "JWT_SECRET is missing, a known default, or shorter than "
            f"{MIN_JWT_SECRET_LENGTH} characters. Generate one with "
            "`openssl rand -hex 32` and set it in the environment."
        )


# ---------------------------------------------------------------------------
# Random values and API keys.
# ---------------------------------------------------------------------------


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

    A single unsalted SHA-256 is fine here (unlike for passwords) because API keys and
    recovery codes are long, machine-generated random strings, so they cannot be
    brute-forced from the hash.

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


def get_random_int32() -> int:
    """Generate a random 32-bit integer.

    Returns
    -------
    int
        The generated 32-bit integer.
    """

    # `secrets` (not `random`) so session IDs cannot be predicted from earlier ones.
    return secrets.randbelow(2**32) - 2**31


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

    # Used for throwaway passwords, so it must come from a CSPRNG.
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(size))


# ---------------------------------------------------------------------------
# Passwords.
# ---------------------------------------------------------------------------


class LegacySha256Hasher:
    """Verifier for the pre-Argon2 password hashes: `salt.hex() + sha256(salt + pw)`.

    It exists only so accounts created before the Argon2 switch can still log in.
    `PasswordHash` lists it as a fallback, so a successful login with a legacy hash
    returns an Argon2 replacement hash, which the auth service saves. Remove it once
    no `user.hashed_password` row matches `LEGACY_HASH_PATTERN`.
    """

    # 16-byte salt (32 hex chars) followed by a SHA-256 digest (64 hex chars).
    LEGACY_HASH_PATTERN = re.compile(r"^[0-9a-f]{96}$")

    @classmethod
    def identify(cls, hash: str | bytes) -> bool:  # noqa: A002 (pwdlib protocol)
        """Return whether `hash` is in the legacy format.

        Parameters
        ----------
        hash
            The stored hash.

        Returns
        -------
        bool
            `True` for a legacy salted SHA-256 hash.
        """

        if isinstance(hash, bytes):
            hash = hash.decode()
        return bool(cls.LEGACY_HASH_PATTERN.match(hash))

    def hash(self, password: str | bytes, *, salt: bytes | None = None) -> str:
        """Create a legacy hash. Only tests use this, to build pre-migration users.

        Parameters
        ----------
        password
            The plaintext password.
        salt
            Optional 16-byte salt; random when omitted.

        Returns
        -------
        str
            The legacy hash.
        """

        if isinstance(password, str):
            password = password.encode()
        salt = salt or secrets.token_bytes(16)
        return salt.hex() + hashlib.sha256(salt + password).hexdigest()

    def verify(self, password: str | bytes, hash: str | bytes) -> bool:  # noqa: A002
        """Check a password against a legacy hash in constant time.

        Parameters
        ----------
        password
            The plaintext password.
        hash
            The stored legacy hash.

        Returns
        -------
        bool
            `True` if the password matches.
        """

        if isinstance(password, str):
            password = password.encode()
        if isinstance(hash, bytes):
            hash = hash.decode()
        salt = bytes.fromhex(hash[:32])
        expected = hashlib.sha256(salt + password).hexdigest()
        return hmac.compare_digest(expected, hash[32:])

    def check_needs_rehash(self, hash: str | bytes) -> bool:  # noqa: A002
        """Legacy hashes always need replacing.

        Parameters
        ----------
        hash
            The stored hash.

        Returns
        -------
        bool
            Always `True`.
        """

        return True


# Argon2 (pwdlib's recommended parameters) for every new hash; the legacy hasher only
# verifies old hashes. The first hasher in the tuple is the "current" one.
password_hash = PasswordHash((Argon2Hasher(), LegacySha256Hasher()))

# Verified against when the username does not exist, so a login for an unknown user
# costs the same Argon2 work as one for a real user (no timing-based enumeration).
_DUMMY_PASSWORD_HASH = password_hash.hash(secrets.token_urlsafe(16))


def hash_password(*, password: str) -> str:
    """Hash a password with Argon2.

    Parameters
    ----------
    password
        The plaintext password.

    Returns
    -------
    str
        The Argon2 hash string to store in `user.hashed_password`.
    """

    return password_hash.hash(password)


def verify_password(*, password: str, stored_hash: str) -> tuple[bool, str | None]:
    """Verify a password and say whether the stored hash should be replaced.

    Parameters
    ----------
    password
        The plaintext password.
    stored_hash
        The hash stored in the database (Argon2 or legacy).

    Returns
    -------
    tuple[bool, str | None]
        `(is_valid, new_hash)`. `new_hash` is not `None` when the password is valid
        but the stored hash uses a legacy scheme or outdated Argon2 parameters; the
        caller must save it.
    """

    return password_hash.verify_and_update(password, stored_hash)


def verify_dummy_password(*, password: str) -> None:
    """Spend the same time as a real verification, for unknown usernames.

    Parameters
    ----------
    password
        The submitted password (its value does not matter).
    """

    password_hash.verify(password, _DUMMY_PASSWORD_HASH)


# ---------------------------------------------------------------------------
# Recovery codes.
# ---------------------------------------------------------------------------


def generate_recovery_codes(*, code_length: int = 20, num_codes: int = 5) -> list[str]:
    """Generate recovery codes for a user.

    The plaintext codes are shown to the user once. Only `hash_recovery_code` output
    is stored.

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


def hash_recovery_code(*, code: str) -> str:
    """Hash a recovery code for storage or lookup.

    Recovery codes are ~119 bits of CSPRNG output, so a fast hash is enough (same
    reasoning as `get_key_hash`).

    Parameters
    ----------
    code
        The plaintext recovery code.

    Returns
    -------
    str
        The SHA-256 hex digest of the code.
    """

    return get_key_hash(key=code)


# ---------------------------------------------------------------------------
# Access tokens.
# ---------------------------------------------------------------------------


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
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))

    payload["exp"] = expire
    payload["iat"] = now
    payload["sub"] = username
    payload["type"] = "access_token"
    payload["user_role"] = user_role
    payload["username"] = username
    payload["workspace_name"] = workspace_name

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    *, family_id: str, token_id: str, username: str, workspace_name: str
) -> str:
    """Create a refresh token for the user.

    The token is a signed JWT, but signature and expiry alone do not make it usable:
    `app.auth.service` also requires its `jti` to still be registered in Redis. That
    is what makes refresh tokens single-use and revocable.

    The role is deliberately left out. It is re-read from the database on every
    refresh, so a role change takes effect at the next refresh.

    Parameters
    ----------
    family_id
        ID shared by every token issued from one login. Reusing an already-rotated
        token revokes the whole family.
    token_id
        Unique ID of this token (the `jti` claim).
    username
        The username of the user to create the refresh token for.
    workspace_name
        The name of the workspace the token is scoped to.

    Returns
    -------
    str
        The refresh token.
    """

    now = datetime.now(timezone.utc)
    payload: dict[str, str | datetime] = {
        "exp": now + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
        "fam": family_id,
        "iat": now,
        "jti": token_id,
        "sub": username,
        "type": "refresh_token",
        "username": username,
        "workspace_name": workspace_name,
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Request rate limiting (slowapi).
# ---------------------------------------------------------------------------


def get_client_ip(request: Request) -> str:
    """Return the client IP to rate limit on.

    The backend sits behind proxies (Caddy, and for admin app calls also the Next.js
    /bff proxy), so the socket peer is a proxy, not the user. The real client IP is
    read from X-Forwarded-For, counting `RATE_LIMIT_TRUSTED_PROXY_HOPS` entries from
    the right. Entries further left were written by the client and could be spoofed.

    Parameters
    ----------
    request
        The incoming request.

    Returns
    -------
    str
        The client IP address (or "unknown" if there is none).
    """

    if RATE_LIMIT_TRUSTED_PROXY_HOPS > 0:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        hops = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
        if hops:
            # With fewer entries than trusted hops, the leftmost entry is still one
            # that a trusted proxy wrote.
            return hops[-min(RATE_LIMIT_TRUSTED_PROXY_HOPS, len(hops))]
    return request.client.host if request.client else "unknown"


def get_rate_limit_key(request: Request) -> str:
    """Key for the default per-endpoint limit: who is calling.

    - A valid user JWT is keyed on the username, so refreshing the token does not
      reset the counter and colleagues behind one NAT do not share a bucket.
    - Any other bearer token (a workspace API key) is keyed on its hash, so the raw
      key never reaches the limiter storage.
    - Anonymous requests are keyed on the client IP.

    Parameters
    ----------
    request
        The incoming request.

    Returns
    -------
    str
        The rate limit key.
    """

    scheme, _, credentials = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and credentials:
        try:
            payload = jwt.decode(
                credentials,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"require": ["exp", "iat"]},
            )
            username = payload.get("username")
            if isinstance(username, str) and username:
                return f"user:{username}"
        except jwt.InvalidTokenError:
            pass
        return f"key:{get_key_hash(key=credentials)}"
    return f"ip:{get_client_ip(request)}"


# One limiter for the whole app. `default_limits` is applied to every route by
# `SlowAPIMiddleware` (added in `app.main`); credential endpoints add a stricter
# per-IP limit with `@limiter.limit(RATE_LIMIT_AUTH, key_func=get_client_ip)`.
# `swallow_errors` keeps the API up (unlimited) if Redis is briefly unreachable.
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[RATE_LIMIT_DEFAULT],
    enabled=RATE_LIMIT_ENABLED,
    key_prefix="rate-limit",
    storage_uri=RATE_LIMIT_STORAGE_URI,
    swallow_errors=True,
)


def enforce_default_rate_limit(request: Request) -> None:
    """App-wide dependency that applies `RATE_LIMIT_DEFAULT` to every route that has
    no `@limiter.limit` of its own.

    Why not slowapi's middleware: it finds the endpoint by scanning `app.routes`, but
    FastAPI >= 0.16x nests included routers there, so it finds nothing and silently
    limits nothing. A dependency runs after routing, when the endpoint is in the
    request scope. `tests/core/test_security.py` checks this keeps working.

    It is a sync function on purpose: slowapi talks to Redis synchronously, and
    FastAPI runs sync dependencies in its threadpool, off the event loop.

    Parameters
    ----------
    request
        The incoming request.

    Raises
    ------
    RateLimitExceeded
        If the caller is over the default limit (turned into a 429 by
        `rate_limit_exceeded_handler`).
    """

    # Read from app state (not the module global) so tests can swap the limiter.
    app_limiter: Limiter = request.app.state.limiter
    endpoint = request.scope.get("endpoint")
    if not app_limiter.enabled or endpoint is None:
        return

    # Routes with their own `@limiter.limit` are checked by that decorator instead.
    # slowapi registers them under "<module>.<function name>".
    name = f"{endpoint.__module__}.{endpoint.__name__}"
    # pylint: disable=protected-access
    if name in app_limiter._route_limits or name in app_limiter._exempt_routes:
        return
    # `in_middleware=True` makes slowapi apply its default (and application) limits.
    app_limiter._check_request_limit(request, endpoint, in_middleware=True)
    # pylint: enable=protected-access


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    """Turn slowapi's `RateLimitExceeded` into a 429 shaped like the app's other
    errors (`{"detail": ...}`), with a `Retry-After` header.

    Parameters
    ----------
    request
        The request that went over the limit.
    exc
        The `RateLimitExceeded` raised by slowapi.

    Returns
    -------
    Response
        The 429 response.
    """

    assert isinstance(exc, RateLimitExceeded)
    headers: dict[str, str] = {}
    # `view_rate_limit` is (limit item, keys) for the limit that was hit.
    current_limit = getattr(request.state, "view_rate_limit", None)
    if current_limit is not None:
        reset_at, _ = limiter.limiter.get_window_stats(
            current_limit[0], *current_limit[1]
        )
        headers["Retry-After"] = str(max(1, int(reset_at - time.time())))
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}. Try again later."},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# HTTP hardening.
# ---------------------------------------------------------------------------

# Sent on every response. This is a JSON API, so the CSP blocks everything: nothing
# the API returns should ever be rendered as a page, run as script or framed.
SECURITY_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}
# Swagger UI and ReDoc load scripts and styles from a CDN, so the strict CSP and
# `no-store` would break them. They still get the other headers.
DOCS_PATH_SUFFIXES = ("/docs", "/docs/oauth2-redirect", "/redoc")
DOCS_EXEMPT_HEADERS = frozenset({"Cache-Control", "Content-Security-Policy"})


class SecurityHeadersMiddleware:
    """Pure ASGI middleware that adds `SECURITY_HEADERS` to every HTTP response.

    Headers an endpoint sets itself are left alone (`setdefault`). Written as raw ASGI
    rather than `BaseHTTPMiddleware` so streaming responses are not buffered.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the downstream ASGI app.

        Parameters
        ----------
        app
            The downstream ASGI application.
        """

        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Add the security headers to the response start message.

        Parameters
        ----------
        scope
            The ASGI connection scope.
        receive
            The ASGI receive callable.
        send
            The ASGI send callable.
        """

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_docs = scope.get("path", "").endswith(DOCS_PATH_SUFFIXES)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    if is_docs and name in DOCS_EXEMPT_HEADERS:
                        continue
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)


def protect_metrics_app(metrics_app: ASGIApp, *, token: str) -> ASGIApp:
    """Wrap the Prometheus app so only a scraper holding `token` can read it.

    Parameters
    ----------
    metrics_app
        The Prometheus ASGI app.
    token
        The expected bearer token (`METRICS_TOKEN`). When empty, /metrics is disabled
        and answers 404, so an unconfigured deployment exposes nothing.

    Returns
    -------
    ASGIApp
        The guarded ASGI app.
    """

    expected = f"Bearer {token}".encode()

    async def guarded(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await metrics_app(scope, receive, send)
            return

        if not token:
            await PlainTextResponse("Not Found", status_code=404)(scope, receive, send)
            return

        supplied = Headers(scope=scope).get("authorization", "").encode()
        # Constant-time comparison so the token cannot be guessed byte by byte.
        if not hmac.compare_digest(supplied, expected):
            response = PlainTextResponse(
                "Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await metrics_app(scope, receive, send)

    return guarded


# ---------------------------------------------------------------------------
# Daily API quotas (moved from core/rate_limit).
# ---------------------------------------------------------------------------


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
