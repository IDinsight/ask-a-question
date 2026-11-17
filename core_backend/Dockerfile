# syntax=docker/dockerfile:1
#
# Production image for core_backend (used by the root docker-compose.yml).
#
#   docker build -t aaq-backend core_backend
#
# Three stages:
#   build   - installs the locked deps (uv.lock, no dev group) into a
#             self-contained virtualenv (/opt/venv) with uv
#   models  - downloads the ML models so containers start without network calls
#   runtime - slim image with only runtime libs, the venv, the models and the
#             app code, running as an unprivileged user
#
# Local development uses Dockerfile.dev instead (hot reload, bind-mounted code).

ARG PYTHON_IMAGE=python:3.12-slim-bookworm
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.26

# Named stage so the uv version can be set once via the ARG above.
FROM ${UV_IMAGE} AS uv

# ---------------------------------------------------------------------------
# Stage 1: install Python dependencies into a virtualenv
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS build

# uv is a single static binary; it never ends up in the runtime image.
COPY --from=uv /uv /usr/local/bin/uv

# gcc + libc6-dev + libpq-dev compile the C extensions with no wheel here
# (psycopg2 is not the -binary package; hdbscan has no aarch64 wheel).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# - UV_PROJECT_ENVIRONMENT: build the venv at /opt/venv, a fixed path we copy
#   into the runtime stage (both stages share the base image, so the venv's
#   python symlink to /usr/local/bin/python3 still resolves there).
# - UV_PYTHON_DOWNLOADS=never: use the image's Python, never fetch another one.
# - UV_COMPILE_BYTECODE: precompile .pyc files for faster container start-up.
# - UV_LINK_MODE=copy: the cache is a separate mount, so hardlinks can't work.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /build

# Only the dependency manifests are copied, so code changes don't invalidate
# this (slow) layer. --frozen fails the build if uv.lock is out of date with
# pyproject.toml instead of silently re-resolving. torch comes from the CPU-only
# index on Linux (see [tool.uv.sources] in pyproject.toml).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------------------
# Stage 2: pre-download ML models
# ---------------------------------------------------------------------------
FROM build AS models

ARG CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
ENV HF_HOME=/opt/hf_cache

# Loading each model through the same class the app uses pulls every file it
# needs (weights, config and tokenizer). The whisper path is hardcoded to
# /whisper_models in app/question_answer/service.py.
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('${CROSS_ENCODER_MODEL}')" \
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" \
    && python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', download_root='/whisper_models')"

# ---------------------------------------------------------------------------
# Stage 3: runtime image
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime

LABEL maintainer="IDinsight"

ARG HOME_DIR=/usr/src/aaq_backend
ARG UID=1000
ARG GID=1000

# Runtime-only system libraries: libpq for psycopg2/asyncpg, ffmpeg for pydub
# and whisper audio decoding. No compilers in the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Unprivileged user that owns and runs the app.
RUN groupadd --gid ${GID} app \
    && useradd --uid ${UID} --gid app --no-create-home --shell /usr/sbin/nologin app

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH="${HOME_DIR}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/hf_cache \
    WHISPER_MODEL_DIR=/whisper_models \
    PORT=8000

# The venv is read-only for the app user (owned by root), which is what we want.
COPY --from=build /opt/venv /opt/venv
# Models are owned by `app` in case a library needs to write lock/metadata files.
COPY --from=models --chown=app:app /opt/hf_cache /opt/hf_cache
COPY --from=models --chown=app:app /whisper_models /whisper_models

WORKDIR ${HOME_DIR}

# Code last, so editing app code only rebuilds this layer. .dockerignore keeps
# tests, local venvs, caches and .env files out of the image.
COPY --chown=app:app . .

# - Strip Windows line endings from the entrypoint (a CRLF shebang fails with
#   "no such file or directory"), then make it executable.
# - temp/ is where uploaded audio is written (relative to WORKDIR). Creating it
#   here with the right owner means a named volume mounted on it inherits that
#   ownership on first use.
RUN sed -i 's/\r$//' startup.sh \
    && chmod +x startup.sh \
    && mkdir -p temp \
    && chown app:app temp

USER app

EXPOSE ${PORT}

# startup.sh runs `alembic upgrade head`, then gunicorn with 4 uvicorn workers.
CMD ["./startup.sh"]
