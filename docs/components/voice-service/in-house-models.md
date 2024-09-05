# How to use in-house Speech models

To host the in-house **Speech-to-text** and **Text-to-speech** models we use a custom docker image made for end to end Speech Service.

## Prerequisite steps

### **Step 1:** Set up your `Environment Variables`.

To access the inhouse models u need to make sure that the `CUSTOM_TTS_ENDPOINT` and the `CUSTOM_STT_ENDPOINT` environment variables are set. These should be set in `.core_backend.env` (cf. [Configuring AAQ](../../deployment/config-options.md)).
??? note "You Can choose to use a combination of both internal and external models"
    Just set the environment variables accordingly, if one of the environment variable is not set then it will automatically fallback on the external model, for how to configure and use the external models refer to our [External Apis](./external-apis.md) guide.

## Deploying In-house Speech Models

!!! info "Make sure you've performed the [prerequisite steps](#prerequisite-steps) before proceeding."

To deploy In-house Speech Models , follow the deployment instructions in [QuickSetup](../../deployment/quick-setup.md) with the following additional steps.

On _**Step 5:** Run docker-compose_, add `docker-compose.speech.yml -p` to the
docker compose command:

```shell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f \
docker-compose.speech.yml -p aaq-stack up -d --build
```

## Setting up In-house Models for development

!!! info "Make sure you've performed the [prerequisite steps](#prerequisite-steps) before proceeding."

follow these steps to [set up your development environment](../../develop/setup.md) for In-house speech models.

??? note "Currently the in-house Models only work with the [Docker Compose Watch](../../develop/setup.md#set-up-using-docker-compose-watch) setup"

For setting up the Speech service for development with **Docker Compose Watch**

_Run docker-compose_, add `docker-compose.speech.yml -p` to the docker compose command:

```shell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f \
docker-compose.speech.yml -p aaq-stack up -d --build
```

## Also see

1. [External Speech Models](./external-apis.md)
2. [Quick Setup](../../deployment/quick-setup.md)
