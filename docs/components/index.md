# Components

In this section you can find the different components within AAQ.

## User-facing Components

There are 3 main components in Ask-A-Question.

<div class="grid cards" markdown>

- :material-api:{ .lg .middle .red} **The Question-Answering Service**

  ***

  Integrate with these API endpoints to answer questions from your
  users.

  [:octicons-arrow-right-24: More info](./qa-service/index.md)

- :material-api:{ .lg .middle .red} **The Urgency Detection Service**

  ***

  Integrate with this API endpoint to tag messages as urgent or not.

  [:octicons-arrow-right-24: More info](./urgency-detection/index.md)

- :material-react:{ .lg .middle } **The Admin App**

  ***

  Manage content in the database. Manage urgency detection rules. Test the service in the playground.
  Explore usage dashboards.

  [:octicons-arrow-right-24: More info](./admin-app/index.md)

</div>

## Internal Components

<div class="grid cards" markdown>

- :material-view-dashboard:{ .lg .middle } **Model Proxy Server**

  ***

  AAQ uses the [LiteLLM Proxy Server](https://litellm.vercel.app/docs/simple_proxy) for
  managing LLM and embedding calls, allowing you to use any LiteLLM supported model (including self-hosted ones).

  [:octicons-arrow-right-24: More info](./litellm-proxy/index.md)

- :material-format-align-middle:{ .lg .middle } **Custom Align Score Model**

  ***

  _(Optional)_ Use a custom dockerised [AlignScore](https://arxiv.org/abs/2305.16739) model to catch
  hallucination and check if LLM response is consistent with the context.

  [:octicons-arrow-right-24: More info](./align-score/index.md)

- :material-format-align-middle:{ .lg .middle } **Huggingface embeddings Model**

  ***

  _(Optional)_ A dockerised huggingface text embeddings model to create vectors
  and perform embeddings search.

  [:octicons-arrow-right-24: More info](./huggingface-embeddings/index.md)

</div>
