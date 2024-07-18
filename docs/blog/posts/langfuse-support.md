---
authors:
  - Suzin
category:
  - Observability

date: 2024-06-06
---
# Tracing your AAQ calls with Langfuse

By integrating [Langfuse](https://langfuse.com/), a popular LLM observability tool with a generous
fee tier, you can now track all LLM calls made via AAQ.

<!-- more -->

## What's in a Trace?

With Langfuse enabled, AAQ is set up to trace each query to the `POST /search` endpoint.

![Traces page of Langfuse: you can view each trace by query_id and user_id](../images/langfuse-traces.png)

Each query is represented as a
[Trace](https://langfuse.com/docs/tracing#introduction-to-traces-in-langfuse). If you
click on the Trace ID, you can view the details of the trace. Here is an example for a
`/search` call with `generate_llm_response` set to `true`:

![Trace Details page outlining system prompt. On the right there are Generations that fall under this particular Trace: "detect-language", "safety", "get_similar_content_async", "generate-response", etc.](../images/langfuse-trace-detail.png)

On the right, there are Generations associated with this trace. In
AAQ, each generation is each call to the [LiteLLM Proxy Server](../../components/litellm-proxy/index.md).
You can view the series of input checks, RAG ("get_similar_content_async" and
"openai/generate-response") and one output check we perform (you can learn more about
our Guardrails [here](../../components/qa-service/llm-response.md#process-flow)). The generation names come
from the model names used in your [LiteLLM Proxy Server Config](../../components/litellm-proxy/index.md#example-config).

## Why does AAQ need observability?

As we begin piloting AAQ in various use cases, we wanted to be able to track LLM calls
so that we can debug, analyze, and improve AAQ's question-answering ability. We are
using it to test different prompt templates and guardrails. If you are
interested in getting your hands dirty with AAQ's codebase, we imagine this will be
useful to you. (Langfuse has a generous free tier and is self-hostable!)

## So how do I use it?

Sign up to [Langfuse](https://langfuse.com/), and set the following environment variables in the backend app to
get started.

```shell
export LANGFUSE=True
export LANGFUSE_PUBLIC_KEY=pk-...
export LANGFUSE_SECRET_KEY=sk-...
export LANGFUSE_HOST=https://cloud.langfuse.com # optional based on your Langfuse host
```

See more in [Config options - Tracing with Langfuse](../../deployment/config-options.md#tracing-with-langfuse).

## What's next?

We want to explore the rich set of features that Langfuse offers, such as evaluation and
scoring. One concrete next step is to trace AAQ's [Feedback
endpoint](../../components/qa-service/response-feedback.md) using Langfuse's
[Scores](https://langfuse.com/docs/scores/user-feedback).

## Docs references

- [Config options - Tracing with Langfuse](../../deployment/config-options.md#tracing-with-langfuse)
- [Dev setup](../../develop/setup.md)
- [LiteLLM Proxy Server](../../components/litellm-proxy/index.md)
