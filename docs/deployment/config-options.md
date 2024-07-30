# Configuring AAQ

There are compulsory configs you must set like secrets and API keys. These are all set
in the .env files as shown in Steps 3 and 4 in [Quick Setup](./quick-setup.md).

## Other parameters

In addition to these, you can modify a bunch of other parameters by either:

- Setting environment variables in the `.env` file; or
- Updating the config directly in [`core_backend/app/config.py`](https://github.com/IDinsight/ask-a-question/blob/main/core_backend/app/config.py).

For example, you set a different LLM to be used for each guardrail step.

??? Note "Environment variables take precedence over the config file."
    You'll see in the config files that we get parameters from the environment and if
    not found, we fall back on defaults provided. So any environment variables set
    will override any defaults you have set in the config file.

### Application parameters

You can find parameters than control the behaviour of the app at [`core_backend/app/config.py`](https://github.com/IDinsight/ask-a-question/blob/main/core_backend/app/config.py)

For a number of optional components like offline models, you will need to update the parameters in this file.

See instructions for setting these in the documentation for the specific optional component.

### Updating LLM prompts

You may wish to customize the prompts for your specific context. These are all found
in [`core_backend/app/llm_call/llm_prompts.py`](https://github.com/IDinsight/ask-a-question/blob/main/core_backend/app/llm_call/llm_prompts.py)

### Tracing with Langfuse

To connect your AAQ to [Langfuse](https://langfuse.com/docs), `core_backend` container
needs the following environment variables set:

```shell
LANGFUSE=True # by default, False
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com # optional based on your Langfuse host
```

Also see [LiteLLM's Langfuse Integration docs](https://docs.litellm.ai/docs/observability/langfuse_integration).
