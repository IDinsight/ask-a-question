# Setting up your development environment

## Step 1: Fork the repository

Please fork the
[project repository](https://github.com/IDinsight/ask-a-question) by clicking on the
"Fork" button. Then, clone the repo using your own GitHub handle:

    git clone git@github.com:<your GitHub handle>/ask-a-question.git

For questions related to setup, please contact
[AAQ Support](mailto:aaq@idinsight.org?Subject=AAQ%20Setup%20Help)

## Step 2: Configure environment variables

1. Navigate to the `deployment/docker-compose` directory.

    ```shell
    cd ask-a-question/deployment/docker-compose
    ```

2. Copy `template.*.env` into new files named `.*.env` within the same directory:

    ```shell
    cp template.base.env .base.env
    cp template.core_backend.env .core_backend.env
    cp template.litellm_proxy.env .litellm_proxy.env
    ```

3. Update `.litellm_proxy.env` with LLM service credentials. This will be used by
   LiteLLM Proxy Server to authenticate to LLM services.

    For local development setup, this is the only file you need to update to get started. For more
    information on the variables used here and other template environment files, see [Configuring AAQ](../deployment/config-options.md).

4. (optional) Edit which LLMs are used in the
   [`litellm_proxy_config.yaml`](https://github.com/IDinsight/ask-a-question/blob/main/deployment/docker-compose/litellm_proxy_config.yaml).

## Step 3: Set up your development environment

Once you are done with steps [1](#step-1-fork-the-repository) &
[2](#step-2-configure-environment-variables), there are two ways to set up your development environment for AAQ:

1. [Docker Compose Watch](#set-up-using-docker-compose-watch)
2. [Manual](#set-up-manually)

You can view the [pros and cons of each method](#pros-and-cons-of-each-setup-method) at
the bottom.

### Set up using [Docker Compose Watch](https://docs.docker.com/compose/file-watch/)

#### Install prerequisites

1. Install [Docker](https://docs.docker.com/get-docker/).
2. If you are not using
[Docker Desktop](https://www.docker.com/products/docker-desktop/), install
[Docker Compose](https://docs.docker.com/compose/install/) with version \>=2.22 to use
the `watch` command.

#### Run `docker compose watch`

If not done already, configure the environment variables in [Step 2](#step-2-configure-environment-variables).

1. In the `deployment/docker-compose` directory, run

    ```shell
    docker compose -f docker-compose.yml -f docker-compose.dev.yml \
        -p aaq-stack watch
    ```

    ??? note "Here's what you should see if the above command executes successfully"
            ✔ Network aaq-stack_default            Created
            ✔ Volume "aaq-stack_db_volume"         Created
            ✔ Volume "aaq-stack_caddy_data"        Created
            ✔ Volume "aaq-stack_caddy_config"      Created
            ✔ Container aaq-stack-caddy-1          Started
            ✔ Container aaq-stack-litellm_proxy-1  Started
            ✔ Container aaq-stack-relational_db-1  Started
            ✔ Container aaq-stack-core_backend-1   Started
            ✔ Container aaq-stack-admin_app-1      Started
            Watch enabled

    The app will now run and update with any changes made to the `core_backend` or
    `admin_app` folders.

    The admin app will be available on [https://localhost](https://localhost) and the
    backend API testing UI on [https://localhost/api/docs](https://localhost/api/docs).

2. To stop AAQ, first exit the running app process in your terminal with
`ctrl+c` and then run:

    ```shell
    docker compose -f docker-compose.yml -f docker-compose.dev.yml \
        -p aaq-stack down
    ```

### Set up manually

#### Install prerequisites

1. Install
   [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html).
2. Install [Node.js v19](https://nodejs.org/en/download).

    ??? note "Setting up a different NodeJS version"
        If you have a different NodeJS version installed already, you can switch to a
        different version by installing
        [Node Version Manager](https://github.com/nvm-sh/nvm) and then executing

        ```bash
        nvm install 19
        nvm use 19
        ```

3. Install [Docker](https://docs.docker.com/get-docker/).
4. (optional) Install [GNU Make](https://www.gnu.org/software/make/). `make` is used
to run commands (targets) in `Makefile`s and can be used to automate various setup
procedures.

#### Set up the backend

0. Navigate to `ask-a-question` repository root.

    ```shell
    cd ask-a-question
    ```

1. Set up your Python environment by creating a new conda environment using `make`.

    ```shell
    make fresh-env
    ```

    This command will remove any existing `aaq` conda environment and create a new
    `aaq` conda environment with the required Python packages.

    <a name="psycopg2"></a>
    ??? warning "Errors with `psycopg2`?"
        `psycopg2` vs `psycopg2-binary`: For production use cases we should use
        `psycopg2` but for local development, `psycopg2-binary` suffices and is often
        easier to install. If you are getting errors from `psycopg2`, try installing
        `psycopg2-binary` instead.

        If you would like `psycopg2-binary` instead of `psycopg2`, run
        `make fresh-env psycopg_binary=true` instead (see below for why you may want
        this).

        See [here](https://www.psycopg.org/docs/install.html#psycopg-vs-psycopg-binary)
        for more details.

    <a name="manual-python-setup"></a>
    ??? note "Setting up the Python environment manually"
        **Create virtual environment**

            conda create --name aaq python=3.10

        **Install Python packages**

            pip install -r core_backend/requirements.txt
            pip install -r requirements-dev.txt

        **Install pre-commit**

         [`pre-commit`](https://pre-commit.com/) is used to ensure that code changes
         are formatted correctly. It is only necessary if you are planning on making
         changes to the codebase.

            pre-commit install

2. Activate your `aaq` conda environment.

    ```shell
    conda activate aaq
    ```

3. Set up the required Docker containers by running

    ```shell
    make setup-dev
    ```

    The command will start the following containers:

    - PostgreSQL with pgvector extension
    - LiteLLM Proxy Server
    - Redis

    ??? note "Setting up the DB, LiteLLM Proxy Server, and Redis seprately"

        If you would like to set
        up each of these dependencies *separately*, check out the [Makefile](https://github.com/IDinsight/ask-a-question/blob/main/Makefile) at repository root.

4. Export the environment variables you defined earlier in [Step
   2](#step-2-configure-environment-variables) by running

    ```shell
    set -a
    source deployment/docker-compose/.base.env
    source deployment/docker-compose/.core_backend.env
    set +a
    ```

    ??? note "Saving environment variables in `aaq` conda environment"

        You can set environment variables by either running `conda env config vars set <NAME>=<VALUE>` for each required environment variable, or [save them in the environment activation script](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#saving-environment-variables).

5. Start the backend app.

    ```shell
    python core_backend/main.py
    ```

    ??? note "Here's what you should see if the above command executes successfully"

        ```
        INFO:     Will watch for changes in these directories: ['~/ask-a-question']
        INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
        INFO:     Started reloader process [73855] using StatReload
        INFO:     Started server process [73858]
        INFO:     Waiting for application startup.
        07/15/2024 12:29:08 PM          __init__.py  79 : Application started
        INFO:     Application startup complete.
        ```

    This will launch the application in "reload" mode (i.e., the app will automatically
    refresh everytime you make a change to one of the files).

    You can test the endpoint for the API documentation by going to
    [http://localhost:8000/docs](http://localhost:8000/docs) (the backend itself runs
    on [http://localhost:8000](http://localhost:8000)).

6. To stop the backend app, first exit the running app process in your terminal with
`ctrl+c` and then run:

    ```shell
    make teardown-dev
    ```

#### Set up the frontend

0. Navigate to `ask-a-question` repository root and activate the
`aaq` virtual environment:

    ```shell
    cd ask-a-question
    ```

    ```shell
    conda activate aaq
    ```

1. In a *new* terminal:

    ```shell
    cd admin_app
    nvm use 19
    npm install
    npm run dev
    ```

    ??? note "Here's what you should see if the above commands execute successfully"

        ```
        > admin-app@0.2.0 dev
        > next dev

        ▲ Next.js 14.1.3
        - Local:        http://localhost:3000

        ✓ Ready in 1233ms
        ```

    This will install the required NodeJS packages for the admin app and start the
    admin app in `dev` (i.e., autoreload) mode. The admin app will now be accessible on
    [http://localhost:3000/](http://localhost:3000/).

    You can login with either the default credentials
    (username: `admin`, password: `fullaccess`) or the ones you specified
    in `.core_backend.env`.

2. To stop the admin app, exit the running app process in your terminal with
`ctrl`+`c`.

### Pros and cons of each setup method

| Method | Pros | Cons |
| --- | --- | --- |
| [Set up using docker compose watch](#set-up-using-docker-compose-watch) | <ul><li>Good for end-to-end testing</li><li>Local environment identical to production deployment</li><li>No need to setup local environment</li><li>Set environment variables and configs once</li></ul> | <ul><li>Changes take 20-30s to be reflected in the app</li></ul> |
| [Set up manually](#set-up-manually)| <ul><li>Instant feedback from changes</li></ul>| <ul><li>Requires more configuration before each run</li><li>Requires environment and dependencies to be set up correctly</li><ul> |


## Step 4: Set up docs

---
**Note**

Ensure that you are in the `ask-a-question` project directory and that you have activated the
`aaq` virtual environment before proceeding.

---

To host docs offline so that you can see documentation changes in real-time, run the
following from `ask-a-question` repository root with an altered port (so that it doesn't
interfere with the app's server):

```shell
mkdocs serve -a localhost:8080
```
