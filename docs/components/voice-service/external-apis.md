# How to use External Speech models

This guide outlines the process for using the external Google Cloud [Speech-to-Text](https://cloud.google.com/speech-to-text?hl=en) and [Text-to-Speech](https://cloud.google.com/text-to-speech?hl=en) speech-to-text and text-to-speech models within AAQ.

## Prerequisite steps

### Configure environment variables

To access the in-house models, ensure that the `CUSTOM_TTS_ENDPOINT` and `CUSTOM_STT_ENDPOINT` environment variables are **not set** (i.e. blank).

You will also need to set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable and make sure you have the `.gcp_credentials.json` file so that the you can access Google Cloud Services. These should be configured in the `.core_backend.env` and `.litellm_proxy.env` files respectively (cf. [Configuring AAQ](../../deployment/config-options.md)).

## Using External Speech Models in Deployment

To deploy external speech models, simply follow the deployment instructions in the [QuickSetup](../../deployment/quick-setup.md). No additional steps are needed.

## Setting up External Models for Development

Follow these steps to [set up your development environment](../../develop/setup.md) for external speech models.

Note: To use the [Manual Setup](../../develop/setup.md#set-up-manually) method, you will need to add your `gcp_credentials` file manually in your local environment as below:

1. Place your `gcp_credentials.json` file inside the `core_backend/` folder.

2. Run `export GOOGLE_APPLICATION_CREDENTIALS="core_backend/credentials.json"` to set the environment variable.

3. While in the root of the directory, run `python core_backend/main.py`.


??? "Do not navigate to `core_backend` folder using `cd core_backend`"
    If you do this, then you will also have to adjust `GOOGLE_APPLICATION_CREDENTIALS` to be `"/credentials.json"` as it's relative to your terminal.

---

## Additional Resources

1. [How to use in-house speech models](./in-house-models.md)
2. [Quick Setup with Docker Compose](../../deployment/quick-setup.md)
3. [Setting up your development environment](../../develop/setup.md)
