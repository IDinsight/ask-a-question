# Setting up your development environment

Now that you have your local environment setup (1), you can setup the components needed to
develop your new feature.
{ .annotate }

1.  if you haven't see [Contributing to AAQ]("./contributing.md")

## Databases

### Running the database on docker

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

You can launch a container running PostgreSQL database and run the necessary migrations using:

    make setup-db

!!! note "After you've run the FastAPI app, you can also run `make add-dummy-faqs` to auto-load some default FAQs into the database if you wish."

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

## Run the backend app

### Step 1: Set environment variables

Make sure you have the necessary environment variables set, e.g. `OPENAI_API_KEY`, before running the app.

You can do this directly using

    export OPENAI_API_KEY="sk-..."
    export PROMETHEUS_MULTIPROC_DIR=/tmp

Or by loading the variables stored in the deployment or test folders' `.env` file (if you've created those)

    set -a && source ./deployment/.env && set +a

### Step 2: Run the backend app

With the Docker databases running, from `aaq-core/core_backend` run:

    python main.py

This will launch the application in "reload" mode i.e. the app with automatically
refresh everytime you make a change to one of the files

## Run the Admin app

??? warning "You need to have nodejs v19 installed locally"

    If you have a different version installed already, you may wish to use
    [nvm](https://github.com/nvm-sh/nvm) to install v19.

From `aaq-core/admin_app` run

    npm i
    npm run dev

This will install the required packages required for the admin app and start the app in `dev` (autoreload) mode.

## Check health

### Backend

Go to the following URL to check that the app came up correctly

    http://localhost:8000/healthcheck

You can also easily test each endpoint through:

    http://localhost:8000/docs

### Admin app

Admin app can be reached at

    http://localhost:3000/

## Setting up docs

To host docs offline so you can see your changes, run the following (with altered port so it doesn't interfere with the app's server):

    mkdocs serve -a "localhost:8080"
