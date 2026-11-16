# How to use in-house speech models

This guide outlines the process for hosting and using our custom in-house **Speech-to-Text** and **Text-to-Speech** models using our specialized Docker image.

## Prerequisite steps

### Configure environment variables

To properly set the `CUSTOM_TTS_ENDPOINT` and `CUSTOM_STT_ENDPOINT` environment variables, open the `.core_backend.env` file and locate the lines for these variables. If they're commented out, uncomment them and ensure their values are set to the correct endpoint URLs for your in-house TTS and STT models (cf. [Configuring AAQ](../../deployment/config-options.md#configuring-the-backend-core_backend)).

## Using In-house Speech Models in Deployment

To deploy in-house speech models, follow the deployment instructions in the [QuickSetup](../../deployment/quick-setup.md) with this additional step:

On _**Step 5:** Start AAQ_, turn on the `speech` profile. From the repository root:

```shell
make prod-up PROD_PROFILES="local-db speech"
```

Leave out `local-db` if you use a managed database. The equivalent Compose command
is `docker compose -p aaq --profile speech up -d --build`.

## Setting Up In-house Models for Development

The in-house models run as a container, so use the
[Docker setup](../../develop/setup.md#set-up-using-docker) with the `speech` profile:

```shell
make dev PROFILES=speech
```

The backend reaches the service at `http://speech_service:8001`.

## Additional Resources

1. [How to use External Speech models](./external-apis.md)
2. [Quick Setup with Docker Compose](../../deployment/quick-setup.md)
3. [Setting up your development environment](../../develop/setup.md)
