# Components

In this section you can find the different components within AAQ.

## User-facing Components

There are 5 main components in Ask-A-Question.

<div class="grid cards" markdown>

- :material-react:{ .lg .middle } __The Admin App__

    ---

    Manage content in the database. Manage urgency detection rules. Test the service's performance.
    Explore usage dashboards.

    [:octicons-arrow-right-24: More info](./admin-app/index.md)

- :material-api:{ .lg .middle .red} __Workspaces__

    ---

    Create dedicated workspaces for your data and users.

    [:octicons-arrow-right-24: More info](./workspaces/index.md)

- :material-api:{ .lg .middle .red} __Multi-turn Chat__

    ---

    Engage in multi-turn question-answering sessions with your data.

    [:octicons-arrow-right-24: More info](./multi-turn-chat/index.md)

- :material-api:{ .lg .middle .red} __The Question-Answering Service__

    ---

    Integrate with these API endpoints to answer questions from your
    users.

    [:octicons-arrow-right-24: More info](./qa-service/index.md)

- :material-api:{ .lg .middle .red} __The Urgency Detection Service__

    ---

    Integrate with this API endpoint to tag messages as urgent or not.

    [:octicons-arrow-right-24: More info](./urgency-detection/index.md)

</div>

## Internal Components

<div class="grid cards" markdown>

- :material-view-dashboard:{ .lg .middle } __Model Proxy Server__

    ---

    AAQ uses the [LiteLLM Proxy Server](https://litellm.vercel.app/docs/simple_proxy) for
    managing LLM and embedding calls, allowing you to use any LiteLLM supported model (including self-hosted ones).

    [:octicons-arrow-right-24: More info](./litellm-proxy/index.md)

- :material-api:{ .lg .middle .red} __Self-hosted Hugging Face Embeddings Model__

    ---

    _(Optional)_ A dockerised Hugging Face text embeddings model to create vectors
  and perform vector search.

    [:octicons-arrow-right-24: More info](./huggingface-embeddings/index.md)


- :material-api:{ .lg .middle .red} __Voice Service__

    ---

    _(Optional)_ Supports both in-house and cloud-based solutions for Automatic Speech Recognition (ASR) and Text-to-Speech (TTS)

    [:octicons-arrow-right-24: More info](./voice-service/index.md)

</div>
