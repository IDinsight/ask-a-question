# Configuring AAQ

There are several aspects of AAQ you can configure:

1. **Application configs through environment variables**

    All required and optional environment variables are defined in
    `deployment/docker-compose/template.*.env` files. **You will need to copy the
    templates into `.*.env` files.**

    ```shell
    cp template.base.env .base.env
    cp template.core_backend.env .core_backend.env
    cp template.litellm_proxy.env .litellm_proxy.env
    ```

    To get a [local setup running with docker
    compose](./quick-setup.md), you won't need to change any values except for
    [LLM credentials in
    `.litellm_proxy.env`](#authenticating-litellm-proxy-server-to-llms).

    See the rest of
    this page for more information on the environment variables.


2. **LLM models in
   [`litellm_proxy_config.yaml`](https://github.com/IDinsight/ask-a-question/blob/main/deployment/docker-compose/litellm_proxy_config.yaml)**

    This defines which LLM to use for which task. You may want to change the LLMs and
    specific calling parameters based on your needs.

3. **LLM prompts in
   [`llm_prompts.py`](https://github.com/IDinsight/ask-a-question/blob/main/core_backend/app/llm_call/llm_prompts.py)**

    While all prompts have been carefully selected to perform each task well, you can
    customize them to your need here.

<a name="template-env-guide"></a>
!!! note "Understanding the template environment files `template.*.env`"

    For local testing and development, the values shoud work as is, except for LLM API credentials in `.litellm_proxy.env`

    For production, make sure you confirm or update the ones marked "change for production" at the least.

    1. Secrets have been marked with 🔒.
    2. All optional values have been commented out. Uncomment to customize for your own case.

## AAQ-wide configurations

The base environment variables are shared by `caddy` (reverse proxy), `core_backend`,
and `admin_app` during run time.

If not done already, copy the template environment file to `.base.env`

```shell
cd deployment/docker-compose/
cp template.base.env .base.env
```

Then, edit the environment variables according to your need ([guide](#template-env-guide) on updating the template):

```shell title="<code>deployment/docker-compose/template.base.env</code>"
--8<-- "deployment/docker-compose/template.base.env"
```

## Configuring the backend (`core_backend`)

### Environment variables for the backend

If not done already, copy the template environment file to `.core_backend.env` ([guide](#template-env-guide) on updating the template):

```shell
cd deployment/docker-compose/
cp template.core_backend.env .core_backend.env
```

The `core_backend` uses the following required and optional (commented out) environment variables.

```shell title="<code>deployment/docker-compose/template.core_backend.env</code>"
--8<-- "deployment/docker-compose/template.core_backend.env"
```

### Other configurations for the backend

You can view all configurations that `core_backend` uses in
`core_backend/app/*/config.py`
files -- for example, [`core_backend/app/config.py`](https://github.com/IDinsight/ask-a-question/blob/main/core_backend/app/config.py).

??? Note "Environment variables take precedence over the config file."
    You'll see in the config files that we get parameters from the environment and if
    not found, we fall back on defaults provided. So any environment variables set
    will override any defaults you have set in the config file.

## Configuring LiteLLM Proxy Server (`litellm_proxy`)

### LiteLLM Proxy Server configurations

You can edit the default [LiteLLM Proxy Server](../components/litellm-proxy/index.md)
settings by updating
[`litellm_proxy_config.yaml`](https://github.com/IDinsight/ask-a-question/blob/main/deployment/docker-compose/litellm_proxy_config.yaml).
Learn more about the server configuration in [LiteLLM Proxy Server](../components/litellm-proxy/index.md).

### Authenticating LiteLLM Proxy Server to LLMs

The `litellm_proxy` server uses the following required and optional (commented out) environment
variables for authenticating to external LLM APIs ([guide](#template-env-guide) on updating the template).

You will need to set up
the correct credentials (API keys, etc.) for all LLM APIs declared in
[`litellm_proxy_config.yaml`](https://github.com/IDinsight/ask-a-question/blob/main/deployment/docker-compose/litellm_proxy_config.yaml). See [LiteLLM's documentation](https://docs.litellm.ai/docs/) for more information about
authentication for different LLMs.

```shell title="<code>deployment/docker-compose/template.litellm_proxy.env</code>"
--8<-- "deployment/docker-compose/template.litellm_proxy.env"
```

## Configuring optional components

See instructions for setting these in the documentation for the specific optional
component at [Optional components](../components/index.md#internal-components).
