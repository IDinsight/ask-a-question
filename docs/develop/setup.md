# Setting up your development environment

There are two ways to set up your development environment for AAQ:

1. [Docker Compose Watch](#set-up-using-docker-compose-watch)
2. [Manual](#set-up-manually)

You can view the [pros and cons of each method](#pros-and-cons-of-each-setup-method) at
the bottom.

Before you get started, please fork the
[project repository](https://github.com/IDinsight/ask-a-question) by clicking on the
"Fork" button and then clone the repo using:

    git clone git@github.com:<your GitHub handle>/ask-a-question.git

For questions related to setup, please contact
[AAQ Support](mailto:aaq@idinsight.org?Subject=AAQ%20Setup%20Help)

## Set up using [Docker Compose Watch](https://docs.docker.com/compose/file-watch/)

### Step 0: Install prerequisites

1. Install [Docker](https://docs.docker.com/get-docker/).
2. If you are not using
[Docker Desktop](https://www.docker.com/products/docker-desktop/), install
[Docker Compose](https://docs.docker.com/compose/install/) with version \>=2.22 to use
the `watch` command.

### Step 1: Configure environment variables

1. Navigate to the `deployment/docker-compose` directory.

        cd ask-a-question/deployment/docker-compose

2. Copy `template.env` to a new file named `.env` within the same directory, and set
   the necessary variables. For local setup, you just need to set your own
   `OPENAI_API_KEY` as the app can use default values for other environment variables
   (check out the various `config.py` under `core_backend/app/` and its subdirectories.)

3. (optional) Edit which LLMs are used in the `litellm_proxy_config.yaml`.

### Step 2: Run `docker compose watch`

1. In the `deployment/docker-compose` directory, run

    ```bash
    docker compose -f docker-compose.yml -f docker-compose.dev.yml -p aaq-stack watch
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

2. To stop the admin app, first exit the running app process in your terminal with
`ctrl+c` and then run:

        docker compose -f docker-compose.yml -f docker-compose.dev.yml -p aaq-stack down

## Set up manually

### Step 0: Install prerequisites

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
4. Install [PostgreSQL](https://www.postgresql.org/download/).
5. (optional) Install [GNU Make](https://www.gnu.org/software/make/). `make` is used
to run commands (targets) in `Makefile`s and can be used to automate various setup
procedures.

### Step 1: Set up the backend

---
**Note**

Ensure that you are in the `ask-a-question` project directory before proceeding.

---

1. Set up your Python environment by creating a new conda environment using `make`.

        make fresh-env

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

        conda activate aaq

3. Set required environment variables in your terminal.

        # 1. Required for core_backend
        export PROMETHEUS_MULTIPROC_DIR=/tmp

4. ??? note "Set up optional environment variables"

            1. To enable Google login
            export NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID=<YOUR_CLIENT_ID>

            2. If you want to track using LANGFUSE
            export LANGFUSE=True
            export LANGFUSE_PUBLIC_KEY=pk-...
            export LANGFUSE_SECRET_KEY=sk-...

            3. API keys for LLM models used in litellm_proxy_config.yaml. This step is only required if you are using aspects of AAQ that require calls to API providers.
            export OPENAI_API_KEY=sk... # if using OpenAI
            export GEMINI_API_KEY=... # if using Gemini

            4. Edit which LLMs are used in the `deployment/docker-compose/litellm_proxy_config.yaml`.

5. <a name="optional-login-credentials"></a> You can set custom login credentials for
the frontend admin app by setting the following environment variables. The defaults can
be found in `/core_backend/add_users_to_db.py`.

        # user 1
        export USER1_USERNAME="user1"
        export USER1_PASSWORD="fullaccess"
        export USER1_API_KEY="user1-key"

        # user 2
        export USER2_USERNAME="user2"
        export USER2_PASSWORD="fullaccess"
        export USER2_API_KEY="user2-key"

6. Set up the required Docker containers for the `PostgreSQL` database and the
`LiteLLM` proxy server using `make`.

        make setup-dev

    ??? note "Setting up the `PostgreSQL` database and `LiteLLM` proxy server separately"

        The `make setup-dev` command should set up the `PostgreSQL` database docker
        container and `LiteLLM` proxy server automatically.  If you would like to set
        up each of these *separately*, here are the steps:

        NB: To run each of the `make` steps *manually*, you can check out the
        individual steps in each of the corresponding Make targets.

        ####`PostgreSQL` database on Docker

        You can launch a container running `PostgreSQL` database and run the necessary
        migrations using:

            make setup-db

        You can stop and remove the `PostgreSQL` container using:

            make teardown-db

        ####LiteLLM Proxy Server

            1. Set models and parameters in `deployment/docker-compose/litellm_proxy_config.yaml`.

            2. Set the appropriate API key(s) as environment variables in your terminal:

                export OPENAI_API_KEY=sk... # if using OpenAI
                export GEMINI_API_KEY=... # if using Gemini

            3. Run the Make target to set up the `LiteLLM` proxy server:

                make setup-llm-proxy

            4. Once done, teardown the container with:

                make teardown-llm-proxy

7. Start the backend app.

        python core_backend/main.py

    ??? note "Here's what you should see if the above command executes successfully"
            INFO:     Will watch for changes in these directories: ['~/ask-a-question']
            INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
            INFO:     Started reloader process [73855] using StatReload
            INFO:     Started server process [73858]
            INFO:     Waiting for application startup.
            07/15/2024 12:29:08 PM          __init__.py  79 : Application started
            INFO:     Application startup complete.

    This will launch the application in "reload" mode (i.e., the app will automatically
    refresh everytime you make a change to one of the files).

    You can test the endpoint for the API documentation by going to
    [http://localhost:8000/docs](http://localhost:8000/docs) (the backend itself runs
    on [http://localhost:8000](http://localhost:8000)).

8. To stop the backend app, first exit the running app process in your terminal with
`ctrl+c` and then run:

        make teardown-dev

### Step 2: Set up the frontend

---
**NB**

Ensure that you are in the `ask-a-question` project directory and that you have activated the
`aaq` virtual environment before proceeding.

---

1. In a *new* terminal:

        cd admin_app
        nvm use 19
        npm install
        npm run dev

    ??? note "Here's what you should see if the above commands execute successfully"
            > admin-app@0.2.0 dev
            > next dev

            ▲ Next.js 14.1.3
            - Local:        http://localhost:3000

            ✓ Ready in 1233ms

    This will install the required NodeJS packages for the admin app and start the
    admin app in `dev` (i.e., autoreload) mode. The admin app will now be accessible on
    [http://localhost:3000/](http://localhost:3000/).

    You can login with either the default credentials
    (username: `admin`, password: `fullaccess`) or the ones you specified
    [when setting up the login credentials](#optional-login-credentials).

2. To stop the admin app, exit the running app process in your terminal with
`ctrl`+`c`.

## Set up docs

---
**NB**

Ensure that you are in the `ask-a-question` project directory and that you have activated the
`aaq` virtual environment before proceeding.

---

1. To host docs offline so that you can see documentation changes in real-time, run the
following from `ask-a-question` repository root with an altered port (so that it doesn't
interfere with the app's server):

        mkdocs serve -a localhost:8080

## Pros and cons of each setup method

| Method | Pros | Cons |
| --- | --- | --- |
| [Set up using docker compose watch](#set-up-using-docker-compose-watch) | <ul><li>Good for end-to-end testing</li><li>Local environment identical to production deployment</li><li>No need to setup local environment</li><li>Set environment variables and configs once</li></ul> | <ul><li>Changes take 20-30s to be reflected in the app</li></ul> |
| [Set up manually](#set-up-manually)| <ul><li>Instant feedback from changes</li></ul>| <ul><li>Requires more configuration before each run</li><li>Requires environment and dependencies to be set up correctly</li><ul> |
