# How to use in-house speech models

This guide outlines the process for hosting and using our custom in-house **Speech-to-Text** and **Text-to-Speech** models using our specialized Docker image.

## Prerequisite steps

### Configure environment variables

To properly set the `CUSTOM_TTS_ENDPOINT` and `CUSTOM_STT_ENDPOINT` environment variables, open the `.core_backend.env` file and locate the lines for these variables. If they're commented out, uncomment them and ensure their values are set to the correct endpoint URLs for your in-house TTS and STT models (cf. [Configuring AAQ](../../deployment/config-options.md#configuring-the-backend-core_backend)).

## Using In-house Speech Models in Deployment

To deploy in-house speech models, follow the deployment instructions in the [QuickSetup](../../deployment/quick-setup.md) with this additional step:

In "Step 5: Run docker-compose", append `docker-compose.speech.yml -p` to the docker compose command as below:

```shell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f \
docker-compose.speech.yml -p aaq-stack up -d --build
```

## Setting Up In-house Models for Development

Currently the in-house models only work with the [Docker Compose Watch](../../develop/setup.md#set-up-using-docker-compose-watch) dev setup. Use the following command:

```shell
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f \
docker-compose.speech.yml -p aaq-stack up -d --build
```

## Additional Resources

1. [How to use External Speech models](./external-apis.md)
2. [Quick Setup with Docker Compose](../../deployment/quick-setup.md)
3. [Setting up your development environment](../../develop/setup.md)
