# Quick Setup with Docker Compose

## Quick setup

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

**Step 1:** Clone the [AAQ repository](https://github.com/IDinsight/ask-a-question).

```shell
git clone git@github.com:IDinsight/ask-a-question.git
```

**Step 2:** Navigate to the `deployment/docker-compose/` subfolder.

```shell
cd deployment/docker-compose/
```

**Step 3:** Copy `template.*.env` files to `.*.env`:

```shell
cp template.base.env .base.env
cp template.core_backend.env .core_backend.env
cp template.litellm_proxy.env .litellm_proxy.env
```

**Step 4:** Configure LiteLLM Proxy server

1. (optional) Edit `litellm_proxy_config.yaml` with LLM services you want to use. See
   [LiteLLM Proxy Server](../components/litellm-proxy/index.md) for more details.
2. Update the API key(s) and authentication information in
   `.litellm_proxy.env`. Make sure you set up the correct authentication for the LLM
   services defined in `litellm_proxy_config.yaml`.

**Step 5:** Run docker-compose

```shell
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
    -p aaq-stack up -d --build
```

You can now view the AAQ admin app at `https://$DOMAIN/` (by default, this should be [https://localhost/](https://localhost/)) and the API documentation at
`https://$DOMAIN/api/docs` (you can also test the endpoints here).

**Step 6:** Shutdown containers

```shell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -p aaq-stack down
```

## Ready to deploy?

See [Configuring AAQ](./config-options.md) to configure your app.
