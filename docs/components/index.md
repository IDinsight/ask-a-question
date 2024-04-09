# Components and Integrations

In this section you can find the different components within AAQ and different integrations it supports so far.

## User-facing Components

There are 2 main components in Ask-A-Question.

<div class="grid cards" markdown>

- :material-api:{ .lg .middle .red} __The Question-Answering Service__

    ---

    Integrate with these API endpoints to answer questions from your
    users.

    [:octicons-arrow-right-24: More info](./qa-service/index.md)

- :material-react:{ .lg .middle } __The Admin App__

    ---

    Manage content in the database. Test the service in the playground.
    Explore usage dashboards.

    [:octicons-arrow-right-24: More info](./admin-app/index.md)

</div>

## Internal Components

<div class="grid cards" markdown>

- :material-view-dashboard:{ .lg .middle } __Model Proxy Server__

    ---

    AAQ uses the [LiteLLM Proxy Server](https://litellm.vercel.app/docs/simple_proxy) for
    managing LLM and embedding calls, allowing you to use any LiteLLM supported model (including self-hosted ones).

    [:octicons-arrow-right-24: More info](./litellm-proxy/index.md)

- :material-format-align-middle:{ .lg .middle } __Custom Align Score Model__

    ---

    _(Optional)_ Use a custom dockerised [AlignScore](https://arxiv.org/abs/2305.16739) model to catch
    hallucination and check if LLM response is consistent with the context.

    [:octicons-arrow-right-24: More info](./align-score/index.md)

</div>

## Integrations

<div class="grid cards" markdown>

- :material-chat-question:{ .lg .middle } __Chat Managers__

    ---

    You can use the AAQ endpoints through various chat managers.

    [:octicons-arrow-right-24: More info](./chat_managers/index.md)

- :material-database:{ .lg .middle .red} __Direct WhatsApp Connector__

    ---

    The direct WhatsApp connector allows you to send and receive messages
    using the WhatsApp Business API without a chat manager.

    [:octicons-arrow-right-24: More info](./whatsapp/index.md)

</div>
