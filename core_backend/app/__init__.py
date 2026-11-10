"""Ask A Question backend package.

The app itself is built in `app.main.create_app`. This file only loads the
environment, because it runs before any other `app.*` module is imported.
"""

# Load core_backend/.env BEFORE any other import. Config (app/core/config.py) and
# prometheus_client read os.environ at import time, so loading later would leave
# them on their defaults (e.g. POSTGRES_USER=postgres).
# Every `app.*` import (uvicorn main:app, alembic, scripts) runs this file first.
# override=False: variables already set in the real environment (Docker, CI,
# tests/api/test.env) always take priority over .env. If no .env exists
# (e.g. in production containers), this is a no-op.
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
