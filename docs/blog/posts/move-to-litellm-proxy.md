---
authors:
  - Amir
category:
  - Architecture

date: 2024-04-05
---
# Model calls made flexible

Instead of being handled directly in our code, our model calls are now routed through an LiteLLM Proxy server, which lets use change models on the fly and have retries, fallbacks, budget tracking, and more.

<!-- more -->

## Why change?

[LiteLLM Proxy](https://litellm.vercel.app/docs/simple_proxy) introduces a streamlined approach for handling various large language models (LLMs) through a single interface. We can now manage model endpoints and configurations via a proxy server, replacing the previous method of hard-coding them into the environment of our app.

This setup not only simplifies the codebase by centralizing the model configurations but also provides the flexibility to switch or update models without altering the core application logic. We can even add and remove models through the proxy's API.

The LiteLLM Proxy server offers features such as consistent input/output formats across different models, fallback mechanisms for error handling, detailed logging, and tracking of token usage and spending. Additionally, it supports features like caching and asynchronous handling of requests. Users configure models in a `config.yaml` file, allowing the proxy to handle requests to different LLMs, such as OpenAI's models or self-hosted ones, by simply setting the model alias in the completion call. See `deployment/docker-compose/litellm_config.yaml` for an example.

## Any downsides?

Potential downsides include dependency on the LiteLLM project for updates for new models and parameters, a possible increase in latency, and increasing code complexity.
