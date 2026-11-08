---
name: api-setup-fastapi
description: >
  FastAPI-specific implementation guide for the api-setup skill. Covers folder
  structure per level, library choices, and implementation patterns. Read
  alongside the main SKILL.md and the selected database reference.
  Apply only what the target level requires.
---

# FastAPI Stack Reference

FastAPI + SQLModel + pydantic-settings managed with `uv` (Python 3.12). For MongoDB, replace SQLModel/Alembic with Motor + Beanie as described in the MongoDB reference.

**Library choices — do not substitute:**
- `pyjwt` — `python-jose` is unmaintained
- `pwdlib[argon2]` — `passlib` is unmaintained and breaks with modern `bcrypt`
- `psycopg[binary]` — psycopg3 driver, connection URL prefix `postgresql+psycopg://`

---

## Review mode — what to inspect

| Area | What to look for |
|---|---|
| Layer separation | Business logic in services not routers; no `HTTPException` in services |
| Folder structure | Matches the level claimed (see table below) |
| Schema separation | API schemas (`<feature>/schema.py`) distinct from ORM models (`<feature>/model.py`) |
| Dependency injection | Auth via `Depends`, not manually parsed from request headers |
| Settings | pydantic-settings with no hardcoded secrets; `secret_key` required |
| Auth library choices | `pyjwt` and `pwdlib[argon2]`, not unmaintained alternatives |

---

## Folder structure by level

```
Level 1 (spike — flat, no layers required):
app/
├── main.py        # entry point + routers inline
└── schemas.py     # optional, inline Pydantic models acceptable

Level 2 (prototype — feature modules):
app/
├── main.py
├── models.py      # imports all feature models for Alembic
├── utils/         # config, database
└── orders/        # one package per feature
    ├── __init__.py
    ├── model.py   # SQLModel table class
    ├── schema.py  # Pydantic request/response shapes
    ├── router.py  # HTTP layer
    └── service.py # business logic

Level 3 (internally testable — full feature arch):
app/
├── main.py
├── models.py      # central model registry for Alembic
├── utils/         # config, database, security, logging, limiter
├── dependencies/  # reusable FastAPI dependencies (auth)
└── orders/        # feature module
    ├── __init__.py
    ├── model.py   # ORM entity
    ├── schema.py  # API DTOs
    ├── router.py  # HTTP concerns only
    └── service.py # business logic + orchestration (queries inline via session)

Level 4 (pre-production — repository only when earned):
app/
├── (all of Level 3)
└── orders/
    └── repository.py  # only if queries are complex/reused; do not add by default
```

**Layer rules (all levels where a layer exists):**

- **Router:** HTTP only — parse request, validate input, call service, return response. Never queries the DB directly or raises `HTTPException` from service logic.
- **Service:** Business logic and data access. Receives `session: Session` via dependency injection and writes queries inline. Returns domain values or `None` on failure. Never raises `HTTPException` (stays framework-agnostic and unit-testable).
- **Repository (Level 4–5 only):** `<feature>/repository.py` — do not add by default. Introduced only when a service is genuinely cluttered with data-access code, or the same query is reused across multiple services. A simple single-table query used once does not qualify. Not a generic CRUD wrapper for every model.
- **Models vs schemas:** ORM entities (`<feature>/model.py`) and API DTOs (`<feature>/schema.py`) are always separate. Map between them in the router or service — never expose an ORM entity as a response model directly.

---

## Project initialisation (Level 1+)

```bash
mkdir <project_name> && cd <project_name>
uv init --name <project_name> --python 3.12
rm -f main.py hello.py
curl -fsSL https://raw.githubusercontent.com/github/gitignore/refs/heads/main/Python.gitignore -o .gitignore
```

Append to `.gitignore`: `.env`, `.env.test`, `*.db`

`.dockerignore`:
```
.venv .git __pycache__ *.pyc .pytest_cache .ruff_cache .mypy_cache tests .env .env.test
```

---

## Dependencies by level

**Level 1:**
```bash
uv add "fastapi[standard]"
```

**Level 2+ (add to Level 1):**
```bash
uv add sqlmodel pydantic-settings "pydantic[email]" alembic "psycopg[binary]"
```

**Level 3+ (add to Level 2):**
```bash
uv add pyjwt "pwdlib[argon2]" slowapi python-multipart loguru
uv add --dev pytest httpx ruff mypy
```

**Level 4+ (add to Level 3):**
```bash
# Observability — choose based on platform; examples:
uv add prometheus-fastapi-instrumentator "sentry-sdk[fastapi]" opentelemetry-sdk
```

---

## Settings — `app/utils/config.py` (Level 1+)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "API"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Level 3+
    secret_key: str = ""   # no default at Level 3 — remove "" and let it fail fast
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Level 2+
    database_url: str = ""
    test_database_url: str | None = None
    cors_origins: list[str] = ["http://localhost:3000"]

    # Level 3+
    rate_limit_enabled: bool = True

    # Level 4+ (pool sizing — see database reference)
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800
    db_pool_timeout: int = 30
    db_connect_retries: int = 5
    db_connect_retry_interval_seconds: float = 2.0
    db_slow_query_ms: int = 500

settings = Settings()
```

At Level 3+, `secret_key` must have no default — the process fails fast if unset.

---

## Logging

### Level 1–2: Python built-in logging — `app/utils/logging.py`

At Levels 1 and 2, use Python's standard `logging` module. Keep it simple — basic format, stdout output, no extra dependencies.

```python
import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
```

Call `setup_logging()` in `main.py` at startup. Use `logging.getLogger(__name__)` in modules.

---

### Level 3+: Loguru — `app/utils/logging.py`

At Level 3 and above, switch to **loguru** for structured JSON logging with request ID propagation. Loguru replaces the standard library logger entirely.

The purpose of logging at Level 3+ is **debugging in production-like environments**. Every log line should help an engineer trace what happened during a request. Log:

- **Requests**: method, path, status code, duration, and request ID on every request.
- **Errors**: full exception context with request ID so failures are traceable.
- **Key transformations**: important business logic decisions, state transitions, and data transformations that aid debugging (e.g. "user upgraded from plan X to Y", "payment intent created", "retry attempt 2/3").

Do not log sensitive data (passwords, tokens, PII). Do not log routine success of trivial operations.

```python
import contextvars
import sys

from loguru import logger

from app.utils.config import settings

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def request_id_patcher(record):
    record["extra"]["request_id"] = request_id_var.get()


def setup_logging():
    logger.remove()  # remove default stderr handler

    logger.configure(patcher=request_id_patcher)

    logger.add(
        sys.stdout,
        serialize=True,  # structured JSON output
        level="INFO" if settings.environment == "production" else "DEBUG",
        backtrace=True,
        diagnose=settings.environment != "production",  # hide variable values in prod
    )
```

**Usage in application code:**

```python
from loguru import logger

# In a service — log key transformations
logger.info("Order status transition", order_id=order.id, from_status=old, to_status=new)

# In error handling
logger.exception("Payment processing failed", user_id=user.id, amount=amount)

# In middleware — log requests (see middleware section)
logger.info(
    "Request completed",
    method=request.method,
    path=request.url.path,
    status=response.status_code,
    duration_ms=duration_ms,
)
```

**Structured output example:**

```json
{"text": "Request completed", "record": {"level": {"name": "INFO"}, "time": "2025-06-30T10:00:00.000000+0000", "extra": {"request_id": "abc123", "method": "POST", "path": "/orders", "status": 201, "duration_ms": 45}}}
```

**What to log at each level:**

| Level | Log content |
|-------|-------------|
| 3 | Requests (method, path, status, duration, request ID), errors with full context, key business logic decisions and state transitions |
| 4 | All of Level 3 + audit events, slow queries, rate limit triggers, outbound service calls |
| 5 | All of Level 4 + SLO-relevant metrics, security events, data retention actions |

---

## Database (Level 2+)

Database setup is fully defined in the database reference for the selected variant. This file provides only the basic SQLModel engine pattern.

For PostgreSQL, replace the snippet below with the implementation in `references/database/variants/postgres.md` (includes retry, pool config, and slow query logging).

```python
# app/utils/database.py — minimal pattern for Level 2
from sqlmodel import Session, create_engine
from app.utils.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

def get_session():
    with Session(engine) as session:
        yield session
```

No `create_all()` on startup — Alembic owns the schema.

---

## Security utilities — `app/utils/security.py` (Level 3+)

```python
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from app.utils.config import settings

password_hash = PasswordHash.recommended()  # argon2id

def hash_password(plain: str) -> str:
    return password_hash.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": subject, "exp": expire}, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        sub = payload.get("sub")
        return sub if isinstance(sub, str) else None
    except jwt.PyJWTError:
        return None
```

---

## Auth dependency and router (Level 3+)

`app/dependencies/auth.py` — provides `get_current_user` and `get_admin_user` FastAPI dependencies using `OAuth2PasswordBearer`. Raises `HTTPException(401)` on invalid or expired tokens.

`app/auth/service.py` — `signup_user` and `authenticate_user`. These are plain functions. They return `None` to signal failure; they never raise `HTTPException`.

`app/auth/router.py` — `POST /auth/signup` (201), `POST /auth/login` (OAuth2 form), `GET /auth/me`. Translates `None` returns from the service into appropriate HTTP errors.

Apply `@limiter.limit("10/minute")` on signup and `@limiter.limit("5/minute")` on login. Routes with rate limits must accept `request: Request` as a parameter.

---

## Application entry point — `app/main.py`

**Level 1:** minimal FastAPI app with one or two routes.

**Level 2+:** add `CORSMiddleware` with origins from settings. Never use `["*"]` together with `allow_credentials=True`.

**Level 3+:** add middleware in this order:
1. CORS
2. Request ID middleware — generate UUID per request, propagate to `request_id_var`, add `X-Request-ID` to response
3. Slowapi rate limit exception handler
4. Global unhandled exception handler — logs the exception, returns `{"detail": "Internal server error"}`, never leaks stack traces

Wire the database into a `lifespan` context manager. Call `setup_logging()` at startup.

---

## Alembic migrations (Level 2+)

```bash
uv run alembic init migrations
```

Configure `migrations/env.py` to read `DATABASE_URL` from settings and set `target_metadata = SQLModel.metadata`. Import `app.models` at the top of `env.py` so autogenerate detects all feature models registered there.

Add `import sqlmodel` to `migrations/script.py.mako` below `import sqlalchemy as sa`.

```bash
uv run alembic revision --autogenerate -m "describe the change"
# review the generated file before running
uv run alembic upgrade head
```

The full `migrations/env.py` implementation is in `references/database/variants/postgres.md`.

---

## Tests (Level 1+)

**Level 1 — smoke tests only:**
```python
def test_root(client):
    assert client.get("/").status_code == 200
```

**Level 2 — happy-path tests.** Basic smoke tests that confirm core paths work.

**Level 3 — service unit tests.** Test business logic independently from HTTP. Call service functions directly with a `session` fixture — no `TestClient`, no auth headers. Cover: success cases, conflict/failure returns (`None`/`False`), edge cases, and boundary conditions.

**Level 4 — integration tests.** Use pytest + httpx `TestClient`. For PostgreSQL, use the conftest from `references/database/variants/postgres.md` — it runs Alembic migrations against `TEST_DATABASE_URL` and rolls back per test. Cover every status code the feature can return: success, 401, 403, 404, 409, 422. One test per scenario.

Do not substitute SQLite when the production database is PostgreSQL — schema dialects differ.

Set env vars before any app import in `conftest.py`:
```python
import os
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
```

---

## Lint, format, type check (Level 3+)

Append to `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 100
exclude = ["migrations/versions/*"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]

[tool.mypy]
python_version = "3.12"
ignore_missing_imports = true
disallow_untyped_defs = true
```

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy app
```

---

## Containerisation (Level 4+)

Multi-stage Dockerfile. Runtime stage runs as a non-root user. No secrets baked in. Python 3.12 is used — 3.13 and 3.14 are also valid targets (see [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/) for base image options).

```dockerfile
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r appuser && useradd -r -g appuser appuser
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/app /app/app
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`--no-editable` installs the project into the venv rather than referencing source — the final stage only needs the venv and the app package, not the full build tree.

Run `alembic upgrade head` as a deploy step before starting the container.

---

## Verification by level

**Level 1:** `uv run fastapi dev app/main.py` — confirm server starts and example endpoint responds.

**Level 2:** `uv run alembic upgrade head` — migrations apply; `uv run pytest -v` — happy-path tests pass.

**Level 3:** `uv run pytest -v && uv run ruff check . && uv run mypy app` — unit tests and linting pass clean.

**Level 4:** `uv run pytest -v` — full integration test suite passes; `docker compose up` — full stack starts; `curl localhost:8000/health` returns 200 with all checks passing.

---

## Authoritative References

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [FastAPI — Security tutorial](https://fastapi.tiangolo.com/tutorial/security/)
- [FastAPI — OAuth2 with JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [FastAPI — CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [FastAPI — Dependency injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI — SQL databases (SQLModel)](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [SQLModel documentation](https://sqlmodel.tiangolo.com/)
- [Pydantic v2 documentation](https://docs.pydantic.dev/latest/)
- [Pydantic v2 migration guide](https://docs.pydantic.dev/latest/migration/)
- [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Alembic documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy engine configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [PyJWT documentation](https://pyjwt.readthedocs.io/)
- [pwdlib documentation](https://frankie567.github.io/pwdlib/)
- [psycopg 3 documentation](https://www.psycopg.org/psycopg3/docs/)
- [Loguru documentation](https://loguru.readthedocs.io/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
- [slowapi documentation](https://slowapi.readthedocs.io/)
- [uv documentation](https://docs.astral.sh/uv/)
- [uv — Docker integration](https://docs.astral.sh/uv/guides/integration/docker/)
- [uv — GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/)
