# Other components

The codebase includes a number of optional components that support end-to-end
deployment of AAQ and support some extended features.

<div class="grid cards" markdown>

- :material-chat-question:{ .lg .middle } __Chat Managers__

    ---

    You can use the AAQ endpoints through various chat managers.

    [:octicons-arrow-right-24: More info](./chat_managers/index.md)

- :material-view-dashboard:{ .lg .middle } __LLM Proxy Server__

    ---

    AAQ uses the [LiteLLM Proxy Server](https://litellm.vercel.app/docs/simple_proxy) for
    managing LLM calls, allowing you to use any LiteLLM supported model (including self-hosted ones).

    [:octicons-arrow-right-24: More info](./litellm-proxy/index.md)

- :material-database:{ .lg .middle .red} __Direct WhatsApp Connector__

    ---

    The direct WhatsApp connector allows you to send and receive messages
    using the WhatsApp Business API without a chat manager.

    [:octicons-arrow-right-24: More info](./whatsapp/index.md)

- :material-format-align-middle:{ .lg .middle } __Align Score__

    ---

    Use [AlignScore](https://arxiv.org/abs/2305.16739) to catch hallucination and
    check if LLM response is consistent with the context.

    [:octicons-arrow-right-24: More info](./align-score/index.md)

</div>
