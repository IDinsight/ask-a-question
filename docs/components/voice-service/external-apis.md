# How to use External Speech models

This guide outlines the process for utilizing the External Google Cloud [Speech-to-Text](https://cloud.google.com/speech-to-text?hl=en) and [Text-to-Speech](https://cloud.google.com/text-to-speech?hl=en) models designed for end-to-end Speech Service.

## Prerequisite steps

### **Step 1:** Configure `Environment Variables`.

To access the in-house models, ensure that the `CUSTOM_TTS_ENDPOINT` and `CUSTOM_STT_ENDPOINT` environment variables are **NOT SET** at all. You will also need to set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable and make sure u have the `.gcp_credentials.json` file so that the You can access the google cloud services. These should be configured in the `.core_backend.env` and `.litellm_proxy.env` files respectively (cf. [Configuring AAQ](../../deployment/config-options.md)).

## Deploying External Speech Models

!!! info "Ensure you've completed the [prerequisite steps](#prerequisite-steps) before proceeding."

To deploy external speech models, follow the deployment instructions in the [QuickSetup](../../deployment/quick-setup.md) , no additional Steps are needed!

## Setting up External Models for development

!!! info "Ensure you've completed the [prerequisite steps](#prerequisite-steps) before proceeding."

Follow these steps to [set up your development environment](../../develop/setup.md) for In-house speech models.

---
**Note**
For Using the [Manual Setup](../../develop/setup.md#set-up-manually), You will need to add your `gcp_credentials` file manually in your local environment.
1. First Expose the environment variable `GOOGLE_APPLICATION_CREDENTIALS` from your `.litellm_proxy.env` or set it manually using
```shell
conda env config vars set <NAME>=<VALUE>
```
2. Place your `gcp_credentials` according to the relative path mentioned in the `GOOGLE_APPLICATION_CREDENTIALS` variable.

??? warning "The `gcp_credentials` file is accessed by the `core_backend` directory so make sure it is accessed w.r.t to the current directory"
    for example:

    if u run the command
    ```shell
    python core_backend/main.py
    ```
    then u will need to place the gcp credentials in the path set by `GOOGLE_APPLICATION_CREDENTIALS` w.r.t the root directory.

    if u run the command
    ```shell
    cd core_backend
    python main.py
    ```
    then u will need to place the gcp credentials in the path set by `GOOGLE_APPLICATION_CREDENTIALS` w.r.t the core_backend directory.

---

## Additional Resources

1. [In-house Speech Models](./in-house-models.md)
2. [Setup for Deployment](../../deployment/quick-setup.md)
3. [Setup for development](../../develop/setup.md)
