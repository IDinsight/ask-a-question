---
name: security
description: >
  DEPRECATED. This reference is superseded by the dedicated security skill.
  Do not load this file from the api-setup skill.
---

# Security Reference

> **Deprecated.** Security hardening is handled by the dedicated security skill at `.agents/skills/security/`. Do not load this file from `api-setup`. For baseline security headers at Level 3+, follow the stack reference (`references/stacks/<framework>.md`).

---

_Original content preserved below for historical reference only._

---

These rules apply to every project regardless of stack. The FastAPI
implementations below are concrete starting points; adapt signatures and
middleware registration to match the active stack reference.

---

## Table of Contents

1. [Security Headers](#1-security-headers)
2. [Refresh Token Pattern](#2-refresh-token-pattern)
3. [Account Lockout](#3-account-lockout)
4. [Audit Logging](#4-audit-logging)
5. [General Rules](#5-general-rules)
6. [Production Checklist](#production-checklist)

---

## 1. Security Headers

Add a middleware that injects security headers on every response. No library
required — a single middleware class covers all cases.

### Implementation — `app/utils/security_headers.py`

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: any) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"          # modern browsers ignore it; disable to avoid quirks
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Cache-Control"] = "no-store"       # default; override per-route for cacheable resources
        response.headers.pop("Server", None)                 # do not advertise the server stack
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response
```

### Registration in `app/main.py`

Add after the CORS middleware (order matters — CORS must run first):

```python
from app.utils.security_headers import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
```

### Rules

- Never set `X-Powered-By` or `Server` headers — they enumerate the stack.
- HSTS only in production — local dev with self-signed certs breaks with it.
- Add `Content-Security-Policy` once the allowed origins are known. Start with
  `default-src 'self'` and loosen only what the UI requires.

---

## 2. Refresh Token Pattern

Short-lived access tokens (15–30 min) reduce exposure if a token leaks, but
force users to re-login frequently. Refresh tokens solve this: a long-lived
token exchanges for a new access token without re-authentication.

### Rules

- Refresh tokens are stored hashed (same approach as passwords) — if the
  token store is compromised, raw tokens are not exposed.
- Each use rotates the refresh token — the old one is invalidated immediately.
  Reuse of an old token signals a stolen token; revoke all tokens for that user.
- Logout deletes the refresh token from the store — the access token expires
  naturally (keep it short so this window is small).
- Refresh tokens are sent via `HttpOnly; Secure; SameSite=Strict` cookie
  only — never in a response body that JavaScript can read.

### Model — `app/models/refresh_token_model.py`

```python
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True)          # SHA-256 of the raw token
    expires_at: datetime
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
```

Register in `app/models/__init__.py` and generate a migration.

### Service helpers — `app/services/token_service.py`

```python
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.utils.config import settings
from app.models.refresh_token_model import RefreshToken


REFRESH_TOKEN_BYTES = 64
REFRESH_TOKEN_EXPIRE_DAYS = 30


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def issue_refresh_token(session: Session, user_id: int) -> str:
    raw = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    token = RefreshToken(
        user_id=user_id,
        token_hash=_hash(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(token)
    session.commit()
    return raw


def rotate_refresh_token(
    session: Session, raw_token: str
) -> tuple[int, str] | None:
    """
    Validate raw_token, delete it, issue a new one.
    Returns (user_id, new_raw_token) or None if invalid/expired.
    Reuse of a previously rotated token is logged as a possible theft.
    """
    record = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == _hash(raw_token))
    ).first()

    if record is None:
        return None                         # unknown token — possible reuse attack
    if record.expires_at < datetime.now(timezone.utc):
        session.delete(record)
        session.commit()
        return None                         # expired

    user_id = record.user_id
    session.delete(record)
    session.commit()

    new_raw = issue_refresh_token(session, user_id)
    return user_id, new_raw


def revoke_all_tokens(session: Session, user_id: int) -> None:
    """Called on logout or detected token reuse."""
    tokens = session.exec(
        select(RefreshToken).where(RefreshToken.user_id == user_id)
    ).all()
    for token in tokens:
        session.delete(token)
    session.commit()
```

### Router endpoints — add to `app/routers/auth_router.py`

```python
from fastapi import Cookie, Response

COOKIE_NAME = "refresh_token"
COOKIE_OPTS = dict(httponly=True, secure=True, samesite="strict", path="/auth/refresh")


@router.post("/login", response_model=TokenResponse)
def login(response: Response, ...):
    # existing login logic ...
    raw_refresh = issue_refresh_token(session, user.id)
    response.set_cookie(COOKIE_NAME, raw_refresh, max_age=30 * 86400, **COOKIE_OPTS)
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    session: Session = Depends(get_session),
) -> TokenResponse:
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    result = rotate_refresh_token(session, refresh_token)
    if result is None:
        response.delete_cookie(COOKIE_NAME, path="/auth/refresh")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user_id, new_raw = result
    response.set_cookie(COOKIE_NAME, new_raw, max_age=30 * 86400, **COOKIE_OPTS)
    return TokenResponse(access_token=create_access_token(str(user_id)))


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    revoke_all_tokens(session, current_user.id)
    response.delete_cookie(COOKIE_NAME, path="/auth/refresh")
```

### Migration

After adding the model, generate and apply a migration:

```bash
uv run alembic revision --autogenerate -m "create refresh_tokens table"
uv run alembic upgrade head
```

---

## 3. Account Lockout

Rate limiting reduces the speed of brute-force attacks but does not lock
accounts. A separate lockout mechanism is required.

**Default thresholds (add to `.env.example`):**

```
AUTH_LOCKOUT_MAX_ATTEMPTS=5
AUTH_LOCKOUT_WINDOW_SECONDS=900
```

### Implementation — `app/utils/lockout.py`

Store attempt counters in Redis if available (preferred — fast, auto-expiry,
works across instances). Fall back to the primary database if Redis is not
configured.

```python
import logging

from app.utils.config import settings

logger = logging.getLogger(__name__)


# --- Redis-backed (preferred when Redis is configured) ---

async def is_locked_redis(redis: any, key: str) -> bool:
    from redis.exceptions import RedisError
    try:
        count = await redis.get(f"lockout:{key}")
        return int(count or 0) >= settings.auth_lockout_max_attempts
    except RedisError:
        logger.warning("Lockout check failed (Redis error) — allowing request")
        return False


async def record_failure_redis(redis: any, key: str) -> None:
    from redis.exceptions import RedisError
    try:
        pipe = redis.pipeline()
        await pipe.incr(f"lockout:{key}")
        await pipe.expire(f"lockout:{key}", settings.auth_lockout_window_seconds)
        await pipe.execute()
    except RedisError:
        logger.warning("Lockout increment failed (Redis error)")


async def clear_lockout_redis(redis: any, key: str) -> None:
    from redis.exceptions import RedisError
    try:
        await redis.delete(f"lockout:{key}")
    except RedisError:
        pass
```

### Usage in auth service

```python
# app/services/auth_service.py

async def authenticate_user(
    session: Session,
    email: str,
    password: str,
    redis: any = None,
) -> TokenResponse | None:
    key = f"login:{email}"

    if redis and await is_locked_redis(redis, key):
        return None                              # caller raises 429, not 401

    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.hashed_password):
        if redis:
            await record_failure_redis(redis, key)
        return None

    if redis:
        await clear_lockout_redis(redis, key)
    return TokenResponse(access_token=create_access_token(str(user.id)))
```

### Router change

When `authenticate_user` returns `None` after a lock, return **429 Too Many
Requests** with a `Retry-After` header — not 401 (which would confirm the
account exists and is locked):

```python
result = await authenticate_user(session, form_data.username, form_data.password, redis)
if result is None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many failed attempts. Try again later.",
        headers={"Retry-After": str(settings.auth_lockout_window_seconds)},
    )
```

### Rules

- Use `email` (not IP address) as the lockout key — IP-based lockout is
  trivially bypassed with proxies and blocks legitimate users on shared IPs.
- Never reveal in the error message which field was wrong.
- Lockout must not prevent an attacker from learning an account exists — use
  the same generic message for locked and non-locked accounts.

---

## 4. Audit Logging

Audit logs record *who did what to which resource*. They are separate from
request logs: request logs capture every HTTP call; audit logs capture only
security-relevant events.

### What to audit

| Event | Example |
| ----- | ------- |
| Auth | login success, login failure, logout, token refresh |
| Account | signup, password change, email change, account deletion |
| Admin actions | user role change, user suspension, config change |
| Sensitive data access | bulk export, PII access, payment details viewed |

Do **not** audit ordinary read/list endpoints — the volume makes the log unusable.

### Implementation — `app/utils/audit.py`

```python
import logging
from typing import Any

from fastapi import Request

audit_logger = logging.getLogger("audit")


def audit_log(
    action: str,
    *,
    user_id: int | None = None,
    resource_type: str,
    resource_id: str | int | None = None,
    result: str = "ok",
    detail: str | None = None,
    request: Request | None = None,
) -> None:
    """
    Emit a structured audit event. Always call from the router layer
    (where the request context is available), never from services.
    """
    audit_logger.info(
        "%s %s %s",
        action,
        resource_type,
        result,
        extra={
            "audit": True,
            "action": action,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id is not None else None,
            "result": result,
            "detail": detail,
            "ip": request.client.host if request and request.client else None,
            "user_agent": request.headers.get("User-Agent") if request else None,
        },
    )
```

### Usage in router

```python
from app.utils.audit import audit_log

@router.post("/auth/login", ...)
def login(request: Request, ...):
    token = authenticate_user(session, form_data.username, form_data.password)
    if token is None:
        audit_log("login.failure", resource_type="user",
                  detail=form_data.username, result="fail", request=request)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    audit_log("login.success", user_id=user.id,
              resource_type="user", resource_id=user.id, request=request)
    return token
```

### Rules

- Emit the audit event **after** the operation succeeds, and emit a failure
  event immediately when the operation is rejected.
- Never include passwords, tokens, or raw secrets in audit events.
- Audit logs must go to a separate log stream in production — do not mix them
  with request logs. Configure a separate log handler or route the `audit`
  logger to a dedicated destination.
- Audit logs must be tamper-evident in production — write to append-only
  storage or a SIEM, not to a mutable database table.

---

## 5. General Rules

**Secrets**

- `SECRET_KEY` is the single most sensitive variable — rotate it independently
  of database passwords. Rotation invalidates all active JWTs; plan accordingly.
- Never log the value of any variable that contains "key", "secret", "token",
  "password", or "credential" — even at DEBUG level.

**Error responses**

- The global exception handler must return a generic `{"detail": "Internal
  server error"}` for unhandled exceptions. Never include a stack trace,
  file path, or database error message in any API response.
- 4xx responses may include a human-readable `detail` field but must not
  reveal system internals (e.g. "column 'email' violates unique constraint").

**Dependencies**

- Run `uv run pip-audit` (or equivalent) in CI to catch known CVEs in
  dependencies. Block the build on HIGH or CRITICAL findings.
- Pin the exact versions of security-critical libraries (JWT, password hashing,
  cryptography) in `pyproject.toml` — do not accept semver ranges for these.

---

## Production Checklist

- [ ] Security headers middleware registered and verified with [securityheaders.com](https://securityheaders.com)
- [ ] HSTS enabled in production (`Strict-Transport-Security` header present)
- [ ] Refresh tokens implemented; access token lifetime ≤ 30 minutes
- [ ] Account lockout active on login endpoint
- [ ] Audit logging wired to auth and admin routes
- [ ] `pip-audit` or equivalent runs in CI
- [ ] No stack traces in API responses (verify with a deliberate 500)
- [ ] `SECRET_KEY` rotation procedure documented
- [ ] `refresh_tokens` table has an index on `expires_at` for efficient cleanup
- [ ] A scheduled job or migration step purges expired refresh tokens
