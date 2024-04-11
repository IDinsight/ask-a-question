---
authors:
  - Amir
category:
  - Architecture

date: 2024-04-05
---
# Adding a model proxy server

Instead of being handled directly in our code, our model calls are now routed through a LiteLLM Proxy server. This lets us change models on the fly and have retries, fallbacks, budget tracking, and more.

<!-- more -->

## Why change?

[LiteLLM Proxy](https://litellm.vercel.app/docs/simple_proxy) introduces a streamlined approach for handling various large language models (LLMs) through a single interface. We can now manage model endpoints and configurations via a proxy server, replacing the previous method of hard-coding them into the environment of our app.

The benefits of this setup:

- Simplifies codebase by centralizing the model configurations
- Provides the flexibility to switch or update models without altering the core application logic - we can even add and remove models through the proxy's API!
- Multiple instances of AAQ can use the same model server

We now configure models in a `config.yaml` file, allowing the proxy to route requests to different LLMs (commercial or self-hosted - full list [here](https://litellm.vercel.app/docs/providers)). See `deployment/docker-compose/litellm_config.yaml` for an example.

The LiteLLM Proxy server also has some extra useful features:

- Consistent input/output formats across different models
- Fallback mechanisms for error handling
- Detailed logging and connectivity to Langfuse and others
- Tracking of token usage and spending.
- Asynchronous handling of requests and caching.

## Any downsides?

Potential downsides include:

- Dependency on the LiteLLM project for updates for new models and parameters
- A possible increase in latency
- A new Docker container in our stack which, despite its name, it not "lite"!

## Docs reference

- [LLM Proxy Server](../../components/litellm-proxy/index.md)
- [Dev setup](../../develop/setup.md)
