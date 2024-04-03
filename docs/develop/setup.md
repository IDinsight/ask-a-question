# Setting up your development environment

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

## Option 1 - Using Docker Compose Watch

| Pros | Cons |
| --- | --- |
| Good for end-to-end testing | Changes take 5-10s to be reflected in the app |
| Local environment identical to production deployment | |
| No need to setup local environment | |
| Set environment variables and configs once | |

Steps:

1. go to `deployment/docker-compose`

2. copy `template.env` to a new file `.env` and set the necessary variables (for local deployment, you just
need to set the `OPENAI_API_KEY` and can leave everything else as default)

3. (optional) Edit which LLMs are used in the `litellm_config.yaml`

4. run

        docker compose -f docker-compose.yml -f docker-compose.dev.yml -p aaq-stack watch

The app will now run and update with any changes made to the `core_backend` or `admin_app` folders.

The admin app will be available on [https://localhost](https://localhost) and the backend API testing UI on [https://localhost/api/docs](https://localhost/api/docs).

## Option 2 - Manual

| Pros | Cons |
| --- | --- |
| Instant feedback from changes | Requires more configuration before each run |
| | Requires environment and dependencies to be set up correctly |

### A: Run the Backend

Steps:

1. Set up your conda environment as per [Contributing to AAQ](./contributing.md) and run

        conda activate aaq

2. Set required environment variables in your terminal using

        export PROMETHEUS_MULTIPROC_DIR=/tmp
        export OPENAI_API_KEY=sk...

3. (optional) Edit which LLMs are used in the `litellm_config.yaml` at the repository root.

4. Run Make target to set up required Docker containers for the database and the LiteLLM proxy server.

        make setup-dev

5. Run the app

        python core_backend/main.py

    This will launch the application in "reload" mode i.e. the app will automatically
    refresh everytime you make a change to one of the files.

     You can test the endpoints by going to [http://localhost:8000/docs](http://localhost:8000/docs) (backend will be running on [http://localhost:8000](http://localhost:8000)).

6. Once done, exit the running app process with `ctrl+c` and run

        make teardown-dev

??? note "Setting up up database and LiteLLM proxy containers manually"

    ## Database

    ### Running the database on docker

    You can launch a container running PostgreSQL database and run the necessary migrations using:

        make setup-db

    You can stop and remove the PostgreSQL container using:

        make teardown-db

    See the contents of these Makefile targets to see how you could run them manually if required.

    ## LiteLLM Proxy Server

    1. Set models and parameters in `core_backend/litellm-config.yaml`

    2. Set OpenAI API key environment variable in your terminal using

            export OPENAI_API_KEY=sk...

    3. Run the Make target

            make setup-llm-proxy

    4. Once done, teardown the container with

            make teardown-llm-proxy

### B: Run the Admin app

??? warning "You need to have nodejs v19 installed locally"

    If you have a different version installed already, you may wish to use
    [nvm](https://github.com/nvm-sh/nvm) to install v19.

From `aaq-core/admin_app` run

    npm i
    npm run dev

This will install the required packages required for the admin app and start the app in `dev` (autoreload) mode.

The admin app will now be accessible on [http://localhost:3000/](http://localhost:3000/)

## Setting up docs

To host docs offline so you can see your changes, run the following in the root of the repo (with altered port so it doesn't interfere with the app's server):

    mkdocs serve -a "localhost:8080"
