"""Test package for core_backend.

pytest imports this package before it loads `tests/conftest.py`, and the conftest is
the first thing that imports `app`. So this is the place to load `tests/test.env`:
`app.core.config` reads `os.environ` once, at import time.

Loading it here means a plain `uv run pytest` works without sourcing the file first.
Variables already exported in the shell win over the file (`setdefault`), which is
how CI points tests at its own Postgres/Redis hosts.
"""

import os
from pathlib import Path

from dotenv import dotenv_values

for _key, _value in dotenv_values(Path(__file__).parent / "test.env").items():
    if _value is not None:
        os.environ.setdefault(_key, _value)
