# Quick Setup with Docker Compose

## Quick setup

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/) (with Compose v2) and [GNU Make](https://www.gnu.org/software/make/)"

**Step 1:** Clone the [AAQ repository](https://github.com/IDinsight/ask-a-question)
and move into it. Run every command below from the repository root.

```shell
git clone git@github.com:IDinsight/ask-a-question.git
cd ask-a-question
```

**Step 2:** Create the environment files:

```shell
make docker-env
```

This copies each `template.*.env` in `deployment/docker-compose/` to `.base.env`,
`.core_backend.env` and `.litellm_proxy.env`. It also creates an empty
`.gcp_credentials.json`, which must exist even if you don't use Google Cloud.
Existing files are never overwritten. The command warns you about any secrets that
still have their template value. Change them before deploying anywhere public.

**Step 3:** Configure the LiteLLM Proxy server

1. (optional) Edit `deployment/docker-compose/litellm_proxy_config.yaml` with the LLM
   services you want to use. See
   [LiteLLM Proxy Server](../components/litellm-proxy/index.md) for more details.
2. Update the API key(s) and authentication information in
   `deployment/docker-compose/.litellm_proxy.env`. Make sure you set up the correct
   authentication for the LLM services defined in `litellm_proxy_config.yaml`.

**Step 4:** Choose a database

- **Postgres in a container (default):** set `POSTGRES_HOST=relational_db` in
  `deployment/docker-compose/.core_backend.env`.
- **Managed Postgres** (e.g. Cloud SQL, RDS): set `POSTGRES_HOST`, `POSTGRES_PORT`
  and the credentials in `.core_backend.env` to point at it, and add
  `PROD_PROFILES=` to the commands in Step 5. The database needs the
  [pgvector](https://github.com/pgvector/pgvector) extension.

**Step 5:** Start AAQ

```shell
make prod-up
```

This builds the images and starts them behind [Caddy](https://caddyserver.com/),
which handles HTTPS automatically. The backend applies database migrations on start.

You can now view the AAQ admin app at `https://$DOMAIN/` (by default
[https://localhost/](https://localhost/)) and the API documentation at
`https://$DOMAIN/api/docs`, where you can also test the endpoints.

Check on it with `make prod-ps` and `make prod-logs` (add `SERVICE=core_backend` to
see a single service).

??? note "Running the Docker Compose commands directly"

    `make prod-up` is a shortcut for:

    ```shell
    docker compose -p aaq --profile local-db up -d --build
    ```

    Leave out `--profile local-db` when using a managed database. To deploy
    prebuilt images instead of building on the server, set `AAQ_BACKEND_IMAGE` and
    `AAQ_ADMIN_APP_IMAGE`, then run `make prod-pull` and
    `docker compose -p aaq up -d --no-build`.

**Step 6:** Shut down the containers

```shell
make prod-down
```

Volumes are kept, so your database and TLS certificates survive a restart.

## Ready to deploy?

See [Configuring AAQ](./config-options.md) to configure your app.

For a development setup with live reload, see
[Setting up your development environment](../develop/setup.md).
