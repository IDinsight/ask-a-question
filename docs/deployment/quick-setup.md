# Quick Setup with Docker Compose

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

**Step 1:** Clone the [AAQ repository](https://github.com/IDinsight/ask-a-question).

    git clone git@github.com:IDinsight/ask-a-question.git

**Step 2:** Navigate to the `deployment/docker-compose/` subfolder.

**Step 3:** Copy `template.env` to `.env` and edit it to set the
variables. If `DOMAIN` is commented out, it defaults to `localhost`.

**Step 4:** If you want to change which LLMs are used, edit `litellm_proxy_config.yaml`.
See [LiteLLM Proxy Server](../components/litellm-proxy/index.md) for more details.

**Step 5:** Run docker-compose

    docker compose -f docker-compose.yml -f docker-compose.dev.yml \
        -p aaq-stack up -d --build

You can now view the AAQ admin app at `https://$DOMAIN/` (e.g. `https://localhost/`) and the API documentation at
`https://$DOMAIN/api/docs` (you can also test the endpoints here).

**Step 6:** Shutdown containers

    docker compose -f docker-compose.yml -f docker-compose.dev.yml -p aaq-stack down
