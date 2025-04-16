---
authors:
  - Tony
  - Suzin
category:
  - API
  - Components
date: 2025-04-16
---

# Chat with AAQ, in text or voice


You can now chat with AAQ using the `/chat` endpoint, and chat in voice using the `/voice-chat`!

<!-- more -->

Using these endpoints, AAQ will respond with the conversation history in mind. Even the safety guardrails will take the chat history into account to assess whether the new query is safe or not.

## **How to use `/chat` and `/voice-chat`**

For up-to-date APIs, check out our [API docs](https://app.ask-a-question.com/api/docs).

**Start a new chat session**: Skip the `session_id` field in your request payload. The endpoint will generate a new `session_id` and return it in the response for you to use.

**Continue a chat session**: To continue the same session, just pass the same `session_id` in the request payload.


## **Potential future work**

We want to add a capability for you to configure the overall context, goals, and the desired tone, personality, and response length. This will ensure the generated response is more context-relevant and appropriate.

## **Docs references**

- [Voice Service](../../components/voice-service/index.md)
