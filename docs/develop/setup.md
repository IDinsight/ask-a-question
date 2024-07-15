# Setting up your development environment

There are two ways to set up your development environment. You can view the [pros and
cons of each method](#pros-and-cons-of-each-setup-method) at the bottom.

## Set up using Docker Compose Watch

### Step 0: Install prerequisites

1. Install [Docker](https://docs.docker.com/get-docker/).
2. If you are not using Docker Desktop, install [Docker Compose](https://docs.docker.com/compose/install/) with version \>=2.22 to use the `watch` command.

### Step 1: Configure

1. Go to `deployment/docker-compose`

2. Copy `template.env` to a new file `.env` within the same directory, and set the
   necessary variables. For local setup, you just need to set your own `OPENAI_API_KEY`
   as the app can use default values for other environment variables (check out the various
   `config.py` under `core_backend/app/` and its subdirectories.)

3. (optional) Edit which LLMs are used in the `litellm_proxy_config.yaml`

### Step 2: Run `docker compose watch`

In `deployment/docker-compose`, run

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml -p aaq-stack watch
```

The app will now run and update with any changes made to the `core_backend` or `admin_app` folders.

The admin app will be available on [https://localhost](https://localhost) and the backend API testing UI on [https://localhost/api/docs](https://localhost/api/docs).

## Set up manually

---
**Note**

For questions related to manual setup, please contact:

1. [Tony Zhao](mailto:tony.zhao@idinsight.org?Subject=AAQ%20Local%20Setup%20Help)

---

### Step 0: Install prerequisites

1. Clone the `main` branch of the repository and navigate to the project directory.

        git clone https: github.com/idinsight/aaq-core.git
        cd ~/aaq-core

2. Install
   [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html).
3. Install [Node.js v19](https://nodejs.org/en/download).

    ??? note "Setting up a different NodeJS version"
        If you have a different NodeJS version installed already, you can switch to a
        different version by installing
        [Node Version Manager](https://github.com/nvm-sh/nvm) and then executing

        ```bash
        nvm install 19
        nvm use 19
        ```

4. Install [Docker](https://docs.docker.com/get-docker/).
5. Install [PostgreSQL](https://www.postgresql.org/download/).
6. (optional) Install [GNU Make](https://www.gnu.org/software/make/). `make` is used
to run commands (targets) in `Makefile`s and can be used to automate various setup
procedures.

### Step 1: Set up the backend

---
**NB**

Ensure that you are in the `aaq-core` project directory before proceeding.

---

1. Set up your Python environment by creating a new conda environment using `make`.

        make fresh-env

    This command will remove any existing `aaq` conda environment and create a new
    `aaq` conda environment with the required Python packages.

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

        export PROMETHEUS_MULTIPROC_DIR=/tmp  # required for core_backend

4. (optional) Set optional environment variables in your terminal.

        # To enable Google login
        export NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID=<YOUR_CLIENT_ID>

        # If you want to track using LANGFUSE
        export LANGFUSE=True
        export LANGFUSE_PUBLIC_KEY=pk-...
        export LANGFUSE_SECRET_KEY=sk-...

5. (optional) Set API keys for LLM models in your terminal. This step is only required
if you are using aspects of Ask-A-Question that require the use of API providers.

        # API keys for LLM models used in litellm_proxy_config.yaml, for example
        export OPENAI_API_KEY=sk... # if using OpenAI
        export GEMINI_API_KEY=... # if using Gemini

6. <a name="optional-login-credentials"></a> (optional) Set custom login credentials
for the front end admin app by setting the following environment variables. The
defaults can be found in `/core_backend/add_users_to_db.py`.

        # user 1
        export USER1_USERNAME="user1"
        export USER1_PASSWORD="fullaccess"
        export USER1_API_KEY="user1-key"

        # user 2
        export USER2_USERNAME="user2"
        export USER2_PASSWORD="fullaccess"
        export USER2_API_KEY="user2-key"

7. (optional) Edit which LLMs are used in the
`deployment/docker-compose/litellm_proxy_config.yaml`.

8. Set up the required Docker containers for the `PostgreSQL` database and the
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

9. Start the backend app.

        python core_backend/main.py

    If successful, you should see output similar to the following in your terminal:

        INFO:     Will watch for changes in these directories: ['~/aaq-core']
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

10. To stop the backend app, first exit the running app process in your terminal with
`ctrl+c` and then run:

        make teardown-dev

### Step 2: Set up the front end

---
**NB**

Ensure that you are in the `aaq-core` project directory and that you have activated the
`aaq` virtual environment before proceeding.

---

1. In a *new* terminal:

        cd admin_app
        nvm use 19
        npm install
        npm run dev

    If successful, you should see the following output in your terminal:

        > admin-app@0.2.0 dev
        > next dev

           ▲ Next.js 14.1.3
           - Local:        http://localhost:3000

           ✓ Ready in 1233ms

    This will install the required NodeJS packages for the admin app and start the
    admin app in `dev` (i.e., autoreload) mode. The admin app will now be accessible on
    [http://localhost:3000/](http://localhost:3000/).

    You can login with either the default credentials
    (username: `user1`, password: `fullaccess`) or the ones you specified
    [when setting up the login credentials](#optional-login-credentials).

## Set up docs

---
**NB**

Ensure that you are in the `aaq-core` project directory and that you have activated the
`aaq` virtual environment before proceeding.

---

1. To host docs offline so that you can see documentation changes in real-time, run the
following from `~/aaq-core` with an altered port (so that it doesn't interfere with the
app's server):

        mkdocs serve -a localhost:8080

## Pros and cons of each setup method

| Method | Pros | Cons |
| --- | --- | --- |
| [Set up using docker compose watch](#set-up-using-docker-compose-watch) | <ul><li>Good for end-to-end testing</li><li>Local environment identical to production deployment</li><li>No need to setup local environment</li><li>Set environment variables and configs once</li></ul> | <ul><li>Changes take 5-10s to be reflected in the app</li></ul> |
| [Set up manually](#set-up-manually)| <ul><li>Instant feedback from changes</li></ul>| <ul><li>Requires more configuration before each run</li><li>Requires environment and dependencies to be set up correctly</li><ul> |
