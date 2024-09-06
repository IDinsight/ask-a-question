# How to use in-house Speech models

This guide outlines the process for hosting and utilizing our custom In-house **Speech-to-Text** and **Text-to-Speech** models using a specialized Docker image designed for end-to-end Speech Service.

## Prerequisite steps

### **Step 1:** Configure `Environment Variables`.

To access the in-house models, ensure that the `CUSTOM_TTS_ENDPOINT` and `CUSTOM_STT_ENDPOINT` environment variables are properly set. These should be configured in the `.core_backend.env` file (cf. [Configuring AAQ](../../deployment/config-options.md#configuring-the-backend-core_backend)).

## Deploying In-house Speech Models

!!! info "Ensure you've completed the [prerequisite steps](#prerequisite-steps) before proceeding."

To deploy in-house speech models, follow the deployment instructions in the [QuickSetup](../../deployment/quick-setup.md) with this additional step:

In _**Step 5:** Run docker-compose_, append `docker-compose.speech.yml -p` to the
docker compose command:

```shell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f \
docker-compose.speech.yml -p aaq-stack up -d --build
```

## Setting up In-house Models for development

!!! info "Ensure you've completed the [prerequisite steps](#prerequisite-steps) before proceeding."

to [set up your development environment](../../develop/setup.md) for In-house speech models follow these steps:

!!! warning "Currently the in-house Models only work with the [Docker Compose Watch](../../develop/setup.md#set-up-using-docker-compose-watch) setup"

To configure the Speech service for development with **Docker Compose Watch**

add `docker-compose.speech.yml -p` to the docker compose command:

```shell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f \
docker-compose.speech.yml -p aaq-stack up -d --build
```

## Additional Resources

1. [External Speech Models](./external-apis.md)
2. [Setup for Deployment](../../deployment/quick-setup.md)
3. [Setup for development](../../develop/setup.md)
