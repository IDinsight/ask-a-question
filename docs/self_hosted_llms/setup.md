## Self Hosted LLMs

AAQ allows you to connect to self-hosted LLMs instead of using OpenAI LLMs. This is useful for users who want to use their own LLMs for privacy reasons or because they want to use an LLM that is not supported by OpenAI.

## :question: How does it work?

AAQ uses LiteLLM to connect to both OpenAI's API as well as self-hosted LLMs. By default, we use OpenAI endpoints, however, the user can switch to any LiteLLM supported hosted model by changing the `LLM_MODEL` and `LLM_ENDPOINT` environment variable in the `.env` file to their respective values.

Check out [LiteLLM](https://docs.litellm.ai/docs/providers) to know more about what models are supported and how to use them.
