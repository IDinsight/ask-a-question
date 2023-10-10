# Setting up your development environment
!!! note "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

## Clone repo

Clone the repo using

    git clone git@github.com:IDinsight/aaq-core.git

navigate to repo and run pre-commit

    cd aaq-core
    pre-commit install

??? warning "Make sure you also run `mypy core_backend/app`"

    `pre-commit` runs in it's own virtual environment. Since `mypy` needs all the
    packages installed, this would mean keeping a whole separate copy of your
    environment just for it. That's too bulky so the pre-commit only checks
    a few high-level typing things. You still need to run `mypy` directly to catch
    all the typing issues.

    If you forget, GitHub Actions 'Linting' workflow will pick up all the mypy errors

## Setup your virtual python environment

    conda create --name aaq-core python=3.10

Install the python packages. While in `aaq-core` directory, run:

    pip install -r core_backend/requirements.txt
    pip install -r requirements-dev.txt

!!! note "`psycopg2` vs `psycopg2-binary`"

    For production use cases we should use `psycopg2` but for local development,
    `psycopg2-binary` suffices and is often easier to install. If you are getting errors
    from `psycopg2`, try installing `psycopg2-binary` instead.

    See [here](https://www.psycopg.org/docs/install.html#psycopg-vs-psycopg-binary) for more details.

## Run a local postgres server

    docker run --name aaq-local \
     -e POSTGRES_PASSWORD=postgres \
     -p 5432:5432 \
     -d postgres

Note that data will not be persisted when the container is destroyed. It might be
preferable to create your database from scratch each time. But if you wish to persist data
use a volume as below:

    docker run --name aaq-local \
     -e POSTGRES_PASSWORD=postgres \
     -p 5432:5432 \
     -v postgres_local_vol:/var/lib/postrges/data \
     -d postgres


## Run a local qdrant server

    docker run --name qdrant-local \
     -p 6333:6333 \
     -d qdrant/qdrant

As with above, if you wish to persist the data in your vector db, you should run

    docker run --name qdrant-local \
     -p 6333:6333 \
     -v qdrant_local_vol:/qdrant/storage \
     -d qdrant/qdrant

## Run migrations

From `aaq-core/core_backend` run:

    python -m alembic upgrade head

## Run the FastAPI app

From `aaq-core/core_backend` run:

    python main.py

This will launch the application in "reload" mode i.e. the app with automatically
refresh everytime you make a change to one of the files

## Check health

Go to the following URL to check that the app came up correctly

    http://localhost:8000/healthcheck
