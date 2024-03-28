# LLM Proxy Server

AAQ uses the [LiteLLM Proxy Server](https://litellm.vercel.app/docs/simple_proxy) for
managing LLM calls, allowing you to use any LiteLLM [supported model](https://docs.litellm.ai/docs/providers) including self-hosted ones.

This proxy server runs as a separate Docker container with configs read from a `config.yaml` file, where you can set the appropriate model
names and endpoints for each LLM task.

You can see an example `config.yaml` file below. In our backend code, we refer to the models by their custom task `model_name` (e.g. "summarize"), but
which actual LLM model each call is routed to is set here.

```yaml
model_list:
  - model_name: embeddings
    litellm_params:
      model: text-embedding-ada-002
      api_key: "os.environ/OPENAI_API_KEY"
  - model_name: default
    litellm_params:
      model: gpt-4-0125-preview
      api_key: "os.environ/OPENAI_API_KEY"
  - model_name: summarize
    litellm_params:
      model: gpt-4-0125-preview
      api_key: "os.environ/OPENAI_API_KEY"
  - model_name: detect-language
    litellm_params:
      model: gpt-3.5-turbo-1106
      api_key: "os.environ/OPENAI_API_KEY"
  - model_name: translate
    litellm_params:
      model: gpt-3.5-turbo-1106
      api_key: "os.environ/OPENAI_API_KEY"
  - model_name: paraphrase
    litellm_params:
      model: gpt-3.5-turbo-1106
      api_key: "os.environ/OPENAI_API_KEY"
  - model_name: safety
    litellm_params:
      model: gpt-3.5-turbo-1106
      api_key: "os.environ/OPENAI_API_KEY"
  - model_name: alignscore
    litellm_params:
      model: gpt-3.5-turbo-1106
      api_key: "os.environ/OPENAI_API_KEY"
litellm_settings:
  num_retries: 3
  request_timeout: 100
  telemetry: False
```

See the [Contributing Setup](../../develop/setup.md) and [Docker Compose Setup](../../deployment/quick-setup.md) for how this service is run in our stack.
