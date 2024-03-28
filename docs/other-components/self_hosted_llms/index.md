# Self Hosted LLMs

AAQ allows you to connect to self-hosted LLMs instead of using OpenAI LLMs. This is useful for users who want to use their own LLMs for privacy reasons or because they want to use an LLM that is not supported by OpenAI.

## :question: How does it work?

AAQ uses LiteLLM and so can connect to any of LiteLLM's [supported models](https://docs.litellm.ai/docs/providers) by setting the appropriate environment variables. This includes OpenAI as well as self-hosted LLMs.

### Default LLM

We use OpenAI endpoints by default, but the user can switch to any LiteLLM supported model by changing the `LITELLM_MODEL_DEFAULT` and `LITELLM_ENDPOINT_DEFAULT` environment variables in the terminal before running the backend app in development mode, or in the `.env` file that is loaded for the docker-compose deployment.

### Using a different LLM for each task

We also support using different models for different LLM tasks instead of using the default model for all tasks. These can be set through their respective environment variables (e.g. for summarization, set `LITELLM_MODEL_SUMMARIZATION` and `LITELLM_ENDPOINT_SUMMARIZATION`). See `core_backend/app/config.py` for all environment variables that can be set.
