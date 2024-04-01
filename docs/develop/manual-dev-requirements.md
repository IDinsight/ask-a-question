# Setting up requirements manually

## Database

### Running the database on docker

You can launch a container running PostgreSQL database and run the necessary migrations using:

    make setup-db

You can stop and remove the PostgreSQL container using:

    make teardown-db

Otherwise, you can run them manually as below.

??? note "Setting up the database manually"

    ### Run a local postgres server

        docker run --name postgres-local \
            -e POSTGRES_PASSWORD=<your password> \
            -p 5432:5432 \
            -d pgvector/pgvector:pg16

    Note that data will not be persisted when the container is destroyed. It might be
    preferable to create your database from scratch each time. But if you wish to persist data
    use a volume as below:

        docker run --name postgres-local \
        -e POSTGRES_PASSWORD=<your password> \
        -p 5432:5432 \
        -v postgres_local_vol:/var/lib/postrges/data \
        -d pgvector/pgvector:pg16

    ### Run migrations

    From `aaq-core/core_backend` run:

        python -m alembic upgrade head

### Connecting to remote databases

In your `.env` file, define the following variables.

To connect to remote Postgres instance:

```
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
```

See `core_backend/app/configs/app_config.py` for the default values for these variables.

## LiteLLM Proxy Server (Required)

1. Set models and parameters in `core_backend/litellm-config.yaml`

2. Set OpenAI API key environment variable in your terminal using

        export OPENAI_API_KEY=sk...

3. Run the Make target

        make setup-llm-proxy

4. Once done, teardown the container with

        make teardown-llm-proxy
