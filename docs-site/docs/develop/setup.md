# Setting up your development environment

## Step 1: Fork the repository

Please fork the
[project repository](https://github.com/IDinsight/ask-a-question) by clicking on the
"Fork" button. Then, clone the repo using your own GitHub handle:

    git clone git@github.com:<your GitHub handle>/ask-a-question.git

For questions related to setup, please contact
[AAQ Support](mailto:aaq@idinsight.org?Subject=AAQ%20Setup%20Help)

## Step 2: Configure environment variables

1. From the repository root, run

    ```shell
    make docker-env
    ```

    This copies each `template.*.env` file in `deployment/docker-compose/` to a
    matching `.*.env` file (`.base.env`, `.core_backend.env`, `.litellm_proxy.env`)
    and creates an empty `.gcp_credentials.json` placeholder. Files that already
    exist are never overwritten, so it's safe to run again.

    ??? note "Doing this by hand"

        ```shell
        cd deployment/docker-compose
        cp template.base.env .base.env
        cp template.core_backend.env .core_backend.env
        cp template.litellm_proxy.env .litellm_proxy.env
        echo '{}' > .gcp_credentials.json
        ```

        The credentials file must exist even if you don't use Google Cloud. Without
        it, Docker mounts an empty directory in its place and the LiteLLM proxy fails
        to start.

2. Update `.litellm_proxy.env` with LLM service credentials (for example
   `OPENAI_API_KEY`). The LiteLLM Proxy Server uses these to authenticate to LLM
   services.

    For local development, this is the only file you need to edit to get started.
    For more information on these variables and the other environment files, see
    [Configuring AAQ](../deployment/config-options.md).

3. (optional) Edit which LLMs are used in
   [`litellm_proxy_config.yaml`](https://github.com/IDinsight/ask-a-question/blob/main/deployment/docker-compose/litellm_proxy_config.yaml).

4. (optional) If you use Vertex AI or Google Cloud Storage, replace
   `deployment/docker-compose/.gcp_credentials.json` with your service account key.

## Step 3: Set up your development environment

There are two ways to run AAQ for development:

1. [Docker](#set-up-using-docker): every app runs in a container, with live reload
2. [Local](#set-up-locally): the apps run on your machine; only Postgres, Redis and
   LiteLLM run in Docker

See the [pros and cons of each method](#pros-and-cons-of-each-setup-method) at the
bottom. Run `make` at the repository root to list every available target.

### Set up using Docker

#### Install prerequisites

1. Install [Docker](https://docs.docker.com/get-docker/) with Compose v2 (included
   in Docker Desktop).
2. Install [GNU Make](https://www.gnu.org/software/make/) (preinstalled on macOS and
   most Linux distributions).

#### Start the stack

1. From the repository root, run

    ```shell
    make dev
    ```

    This builds and starts every service in `docker-compose-dev.yml`: `core_backend`,
    `admin_app`, `docs`, `litellm_proxy`, `redis` and `relational_db`. The backend
    applies database migrations before it starts. The first run takes a few minutes
    while images build and dependencies install. Follow progress with
    `make dev-logs`.

    Source folders are mounted into the containers, so changes to `core_backend/`,
    `admin_app/` or `docs-site/` reload straight away.

    | Service   | URL                                                     |
    | --------- | ------------------------------------------------------- |
    | Admin app | [http://localhost:3000](http://localhost:3000)          |
    | Backend   | [http://localhost:8000/docs](http://localhost:8000/docs) |
    | Docs site | [http://localhost:8001](http://localhost:8001)          |
    | Postgres  | `localhost:5434`                                        |
    | Redis     | `localhost:6380`                                        |
    | LiteLLM   | `localhost:4001`                                        |

    Log in to the admin app with `ADMIN_USERNAME` and `ADMIN_PASSWORD` from
    `.core_backend.env`.

2. Day-to-day commands:

    | Command                       | What it does                                               |
    | ----------------------------- | ---------------------------------------------------------- |
    | `make dev-logs [SERVICE=…]`   | Follow logs, optionally for one service                    |
    | `make dev-ps`                 | Show container status                                      |
    | `make dev-shell [SERVICE=…]`  | Open a shell in a container (defaults to `core_backend`)   |
    | `make dev-migrate`            | Run Alembic migrations in the backend container            |
    | `make dev-rebuild`            | Rebuild images after `uv.lock` or `pnpm-lock.yaml` changes |
    | `make dev-restart [SERVICE=…]`| Restart containers without rebuilding                      |

3. To stop AAQ, run

    ```shell
    make dev-down
    ```

    This keeps the database volume. `make dev-clean` also deletes the volumes,
    which wipes the dev database.

??? note "Optional services: speech and Hugging Face embeddings"

    Turn on optional services with `PROFILES`:

    ```shell
    make dev PROFILES=speech
    make dev PROFILES="speech huggingface-embeddings"
    ```

    For the backend to use the in-house speech service, set
    `CUSTOM_STT_ENDPOINT=http://speech_service:8001/transcribe` and
    `CUSTOM_TTS_ENDPOINT=http://speech_service:8001/synthesize` in
    `.core_backend.env`. See
    [in-house speech models](../components/voice-service/in-house-models.md).

??? note "Running the production-style stack locally"

    `make prod-up` builds the optimised images and serves them behind Caddy at
    [https://localhost](https://localhost). The backend is at
    [https://localhost/api/docs](https://localhost/api/docs). It includes a Postgres
    container by default (`PROD_PROFILES=local-db`), which needs
    `POSTGRES_HOST=relational_db` in `.core_backend.env`. Use `make prod-logs`,
    `make prod-ps` and `make prod-down` to manage it. This is useful for end-to-end
    checks, but there's no live reload.

### Set up locally

#### Install prerequisites

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/). uv
   installs the right Python version (3.12) for you.
2. Install the current [Node.js LTS](https://nodejs.org/en/download). The
   `admin_app` uses [pnpm](https://pnpm.io/) through
   [corepack](https://nodejs.org/api/corepack.html), which pins the pnpm version
   listed in `admin_app/package.json`.
3. Install [Docker](https://docs.docker.com/get-docker/) to run Postgres, Redis and
   LiteLLM.
4. Install [GNU Make](https://www.gnu.org/software/make/) (preinstalled on macOS and
   most Linux distributions).

#### Start the dependencies

From the repository root, run

```shell
make setup-dev
```

This starts the following containers and then applies the database migrations:

- PostgreSQL with the pgvector extension on `localhost:5432`
- Redis on `localhost:6379`
- LiteLLM Proxy Server on `localhost:4000`

??? note "Starting the dependencies separately"

    `make setup-db`, `make setup-redis` and `make setup-llm-proxy` start each one on
    its own. `make setup-llm-proxy-local` runs LiteLLM as a local process on port
    4001 instead of in Docker. If you use it, set
    `LITELLM_ENDPOINT=http://localhost:4001` in `core_backend/.env`.

When you're done, remove the containers with

```shell
make teardown-dev
```

#### Set up the backend

1. Create the backend's env file and install its dependencies:

    ```shell
    cd core_backend
    cp .env.example .env
    uv sync
    ```

    The defaults in `.env.example` already point at the containers from
    `make setup-dev`. The only thing to check is that the Postgres credentials in
    `core_backend/.env` match those in `deployment/docker-compose/.core_backend.env`,
    because that's the file the Postgres container was created from.

2. Start the backend:

    ```shell
    uv run --env-file .env python -m app.main
    ```

    The backend doesn't load `.env` on its own, so keep `--env-file`.

    ??? note "Here's what you should see if the above command executes successfully"

        ```
        INFO:     Will watch for changes in these directories: ['~/ask-a-question/core_backend']
        INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
        INFO:     Started reloader process [73855] using StatReload
        INFO:     Started server process [73858]
        INFO:     Waiting for application startup.
        INFO:     Application startup complete.
        ```

    The backend runs in reload mode, so it restarts whenever you change a file. The
    API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).

3. (optional) Install the pre-commit hooks if you plan to make changes:

    ```shell
    uv run pre-commit install
    ```

4. To stop the backend, press `ctrl`+`c`.

??? note "Migrations"

    `make setup-dev` applies migrations once. After pulling new migrations, run
    them from `core_backend/`:

    ```shell
    uv run --env-file .env python -m alembic upgrade head
    ```

#### Set up the frontend

1. In a *new* terminal:

    ```shell
    cd admin_app
    corepack enable
    pnpm install
    pnpm dev
    ```

    This installs the admin app's packages and starts it in dev (hot reload) mode at
    [http://localhost:3000](http://localhost:3000).

    The browser only talks to the admin app's `/bff` routes, which then call the
    backend at `BACKEND_INTERNAL_URL`. That defaults to `http://localhost:8000`, so
    you don't need to configure anything for local development.

    Log in with `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `.core_backend.env`.

2. To stop the admin app, press `ctrl`+`c`.

#### Tests and linting

Each app runs its own checks:

| App          | Tests                       | Lint and type checks       |
| ------------ | --------------------------- | -------------------------- |
| core_backend | `uv run pytest`             | `make -C core_backend lint` |
| admin_app    | `pnpm test`                 | `pnpm lint`                |

The backend tests start their own throwaway `testdb` and `redis-test` containers,
so you don't need `make setup-dev` running for them.

### Pros and cons of each setup method

| Method | Pros | Cons |
| --- | --- | --- |
| [Docker](#set-up-using-docker) | <ul><li>One command starts everything</li><li>No Python or Node setup on your machine</li><li>Same images and service names as deployment</li></ul> | <ul><li>Slower first start while images build</li><li>Rebuild needed when dependencies change</li><li>Debuggers and IDE tooling need extra setup to attach to containers</li></ul> |
| [Local](#set-up-locally) | <ul><li>Fastest feedback loop</li><li>Easy to attach debuggers and run individual tests</li></ul> | <ul><li>Needs uv, Node.js and pnpm installed</li><li>Two env files to keep in sync</li><li>Each app started in its own terminal</li></ul> |

## Step 4: Set up docs

The docs are a standalone [uv](https://docs.astral.sh/uv/) project in `docs-site/`, so
you don't need any backend dependencies. With the Docker setup they're already
running at [http://localhost:8001](http://localhost:8001).

To run them on their own, use a port that doesn't clash with the backend:

```shell
cd docs-site
uv run mkdocs serve -a localhost:8001
```

`uv run` installs the pinned docs dependencies on first use.
