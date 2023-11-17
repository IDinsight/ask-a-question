# Quick Setup

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

**Step 1:** Clone the [repo](https://github.com/IDinsight/aaq-core) to your machine

    git clone git@github.com:IDinsight/aaq-core.git

**Step 2:** Copy `deployment/template.env` to `deployment/.env` and edit it to set the variables

    POSTGRES_PASSWORD=
    OPENAI_API_KEY=
    QUESTION_ANSWER_SECRET=
    ... etc.

**Step 3:** Copy `deployment/template.env.nginx` to `deployment/.env.nginx` and edit it to set the variables

    DOMAIN=
    EMAIL=
    ... etc.

**Step 4:** Run `deployment/init-letsencrypt.sh` to get an SSL certificate from LetsEncrypt

    cd deployment
    chmod a+x ./init-letsencrypt.sh
    ./init-letsencrypt.sh

**Step 5:** Run docker-compose

    cd deployment
    docker compose -f docker-compose.yml -p aaq-stack up -d --build

You can now access the admin app at `https://[DOMAIN]/` and the apis at `https://[DOMAIN]/api`

!!! note "Also see [Calling the endpoints](../develop/testing.md#call-the-endpoints)."

**Step 6:** Shutdown containers

    cd deployment
    docker compose -f docker-compose.yml -p aaq-stack down
