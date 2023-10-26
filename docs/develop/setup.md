# Setting up your development environment

## Clone repo

Clone the repo using

    git clone git@github.com:IDinsight/aaq-core.git

navigate to repo and run pre-commit

    cd aaq-core
    pre-commit install

Make sure you also run `mypy` separately with `mypy core_backend/app` (1)
{ .annotate }

1. `pre-commit` runs in its own virtual environment. Since `mypy` needs all the
   packages installed, this would mean keeping a whole separate copy of your
   environment just for it. That's too bulky so the pre-commit only checks
   a few high-level typing things. You still need to run `mypy` directly to catch
   all the typing issues.
   If you forget, GitHub Actions 'Linting' workflow will pick up all the mypy errors.

## Setup your virtual python environment

You can automatically create a ready-to-go `aaq-core` conda environment with:

    make fresh-env

??? warning "Errors with `pyscopg2`?"

    `psycopg2` vs `psycopg2-binary`: For production use cases we should use `psycopg2` but for local development,
    `psycopg2-binary` suffices and is often easier to install. If you are getting errors
    from `psycopg2`, try installing `psycopg2-binary` instead.

    If you would like `psycopg2-binary` instead of `psycopg2`, run `make fresh-env psycopg_binary=true` instead (see below for why you may want this).

    See [here](https://www.psycopg.org/docs/install.html#psycopg-vs-psycopg-binary) for more details.

??? note "Setting up the environment manually"

    If you would like to setup the environment manually, you can use conda to create virtual environment (or `venv` or other).

        conda create --name aaq-core python=3.10

    Install the python packages. While in `aaq-core` directory, run:

        pip install -r core_backend/requirements.txt
        pip install -r requirements-dev.txt

## Databases

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

You can create both postgres and vector databases (without a persistent data volume) and run the necessary migrations using:

    make setup-dbs

You can stop and remove them using:

    make teardown-dbs

Otherwise, you can run them manually as below.

??? note "Setting up databases manually"

    ### Run a local postgres server

        docker run --name postgres-local \
            -e POSTGRES_PASSWORD=postgres \
            -p 5432:5432 \
            -d postgres

    Note that data will not be persisted when the container is destroyed. It might be
    preferable to create your database from scratch each time. But if you wish to persist data
    use a volume as below:

        docker run --name postgres-local \
        -e POSTGRES_PASSWORD=postgres \
        -p 5432:5432 \
        -v postgres_local_vol:/var/lib/postrges/data \
        -d postgres

    ### Run a local qdrant server

        docker run --name qdrant-local \
        -p 6333:6333 \
        -d qdrant/qdrant

    As with above, if you wish to persist the data in your vector db, you should run

        docker run --name qdrant-local \
        -p 6333:6333 \
        -v qdrant_local_vol:/qdrant/storage \
        -d qdrant/qdrant

    ### Run migrations

    From `aaq-core/core_backend` run:

        python -m alembic upgrade head

## Run the backend app

With the Docker databases running, from `aaq-core/core_backend` run:

    python main.py

This will launch the application in "reload" mode i.e. the app with automatically
refresh everytime you make a change to one of the files

## Run the Admin app

??? warning "You need to have nodejs v19 installed locally"

    If you have a different version installed already, you may wish to use
    [nvm](https://github.com/nvm-sh/nvm) to install v19.

From `aaq-core/admin_app` run:

    npm run dev

This will start the react/nextjs front end used to manage content.

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
