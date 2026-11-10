"""Ask A Question backend package.

The FastAPI app lives in `app.main` (see that module). This file only loads
`core_backend/.env`, and it must run before anything else: `app.core.config` and
`prometheus_client` read `os.environ` at import time, and Python executes this
package `__init__` before any `app.*` submodule (uvicorn, gunicorn, alembic,
scripts).

`override=False` means variables already set in the real environment (Docker, CI)
always win over `.env`. If no `.env` exists (e.g. production containers) this is a
no-op.

Under pytest (which sets `PYTEST_VERSION` before importing anything) `.env` is NOT
loaded. Tests take their settings from `tests/test.env` only, so a developer's local
database, Sentry DSN or API keys can never leak into a test run.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

if "PYTEST_VERSION" not in os.environ:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
