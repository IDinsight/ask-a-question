# Quick Setup with Docker Compose

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

**Step 1:** Clone the [AAQ repository](https://github.com/IDinsight/aaq-core).

    git clone git@github.com:IDinsight/aaq-core.git

**Step 2:** Navigate to the `deployment/docker-compose/` subfolder.

**Step 3:** Copy `template.env` to `.env` and edit it to set the
variables. If `DOMAIN` is commented out, it defaults to `localhost`.

**Step 4:** Run docker-compose

    docker compose -f docker-compose.yml -f docker-compose.dev.yml \
        -p aaq-stack up -d --build

You can now view the AAQ admin app at `https://$DOMAIN/` (e.g. `https://localhost/`) and the API documentation at
`https://$DOMAIN/api/docs`

!!! note "To test the endpoints, see [Calling the endpoints](../develop/testing.md#call-the-endpoints)."

**Step 5:** Shutdown containers

    docker compose -f docker-compose.yml -f docker-compose.dev.yml -p aaq-stack down
