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

### Step 0: Install prerequisites

1. Install
   [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html).
2. Install [Node.js v19](https://nodejs.org/en/download). If you have a different
   version installed already, you may wish to use [nvm](https://github.com/nvm-sh/nvm)
   to install v19.
3. Install [Docker](https://docs.docker.com/get-docker/).

### Step 1: Run the backend

1. [Set up your python environment](contributing.md#setup-your-virtual-python-environment).

2. Activate your `aaq` conda environment

        conda activate aaq

3. Set required environment variables in your terminal using

        export OPENAI_API_KEY=sk...  # required for model proxy server
        export PROMETHEUS_MULTIPROC_DIR=/tmp  # required for core_backend
        export NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID=<YOUR_CLIENT_ID> # optional

4. (optional) Set custom login credentials by setting the following environment variables. The defaults
can be found in `core_backend/add_users_to_db.py`.

        # user 1
        export USER1_USERNAME = "user1"
        export USER1_PASSWORD = "fullaccess"
        export USER1_RETRIEVAL_SECRET = "user1-key"

        # user 2
        export USER2_USERNAME = "user2"
        export USER2_PASSWORD = "fullaccess"
        export USER2_RETRIEVAL_SECRET = "user2-key"

5. (optional) Edit which LLMs are used in the `deployment/docker-compose/litellm_proxy_config.yaml`.

6. Run Make target to set up required Docker containers for the database and the LiteLLM proxy server.

        make setup-dev

7. Run the app

        python core_backend/main.py

    This will launch the application in "reload" mode i.e. the app will automatically
    refresh everytime you make a change to one of the files.

     You can test the endpoints by going to [http://localhost:8000/docs](http://localhost:8000/docs) (backend will be running on [http://localhost:8000](http://localhost:8000)).

8. Once done, exit the running app process with `ctrl+c` and run

        make teardown-dev

??? note "Set up database and LiteLLM proxy containers manually"

    The `make setup-dev` command should set up the database docker container and LiteLLM proxy server automatically. If you wish to set them up separately, here are the steps:

    #### PostgreSQL database on docker

    You can launch a container running PostgreSQL database and run the necessary migrations using:

        make setup-db

    You can stop and remove the PostgreSQL container using:

        make teardown-db

    See the contents of these Makefile targets to see how you could run them manually if required.

    #### LiteLLM Proxy Server

    1. Set models and parameters in `deployment/docker-compose/litellm_proxy_config.yaml`

    2. Set OpenAI API key environment variable in your terminal using

            export OPENAI_API_KEY=sk...

    3. Run the Make target

            make setup-llm-proxy

    4. Once done, teardown the container with

            make teardown-llm-proxy

### Step 2: Run the admin app

1. In a new terminal, navigate to `aaq-core/admin_app`
2. If you want Google login option to work, you'll need to set the Google login client ID

        export NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID=<YOUR_CLIENT_ID>

3. Run

        npm i
        npm run dev

This will install the required packages required for the admin app and start the app in `dev` (autoreload) mode.

The admin app will now be accessible on [http://localhost:3000/](http://localhost:3000/)

## Set up docs

1. [mkdocs](https://www.mkdocs.org/user-guide/installation/) should be installed in your
development conda environment created by `make fresh-env`. Activate the conda environment:

        conda activate aaq

2. To host docs offline so you can see your changes, run the following in the root of the repo (with altered port so it doesn't interfere with the app's server):

        mkdocs serve -a "localhost:8080"

## Pros and cons of each setup method

| Method | Pros | Cons |
| --- | --- | --- |
| [Set up using docker compose watch](#set-up-using-docker-compose-watch) | <ul><li>Good for end-to-end testing</li><li>Local environment identical to production deployment</li><li>No need to setup local environment</li><li>Set environment variables and configs once</li></ul> | <ul><li>Changes take 5-10s to be reflected in the app</li></ul> |
| [Set up manually](#set-up-manually)| <ul><li>Instant feedback from changes</li></ul>| <ul><li>Requires more configuration before each run</li><li>Requires environment and dependencies to be set up correctly</li><ul> |
