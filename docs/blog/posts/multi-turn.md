---
authors:
  - Sid
category:
  - Admin App
  - Chat
date: 2024-09-01
---

# Introducing Multi-turn Chat

Ever wanted to ask follow-up questions without losing context from previous answers?
We’ve now got you covered with our brand-new **multi-turn chat** endpoint. It’s like having a running conversation with your data—no extra setup or repeated prompts needed. Just keep asking, and the chat remembers what you said before.

<!-- more -->

## Why did we build this?

Managing user inquiries on-the-fly often means juggling multiple questions and follow-ups. This can get tricky when new messages layer onto an ongoing conversation. Multi-turn chat solves that by keeping track of your entire conversation history, so your questions can seamlessly connect to prior answers.

## How does multi-turn chat work?

Here’s a quick overview:

1. **Start or continue a conversation**
   You send a message to `/chat` with (or without) a `session_id`. If you’re continuing an existing session, the API fetches your conversation history from Redis and picks up right where you left off.

2. **Chat history is updated**
   The conversation gets appended with your new question and the LLM’s response. No matter how many times you circle back for clarifications, the history grows accordingly.

3. **Message type detection**
   Under the hood, each user query is classified as either a _Follow-up Message_ (building on a previous topic) or a _New Message_ (starting a fresh topic). This helps the LLM decide what context to look up.

4. **Contextual replies**
   The system crafts an internal query to search through a vector database, pulling in relevant information. This ensures each answer is tailored and _contextualized_ to everything mentioned so far.

5. **Redis for the win**
   Since the entire conversation is stored in Redis, you never have to resend old questions or previous responses. It’s quick, resilient, and always ready to continue your conversation.

Here’s a peek at the Swagger documentation for multi-turn chat:

![Swagger Multi-turn Chat Screenshot](./swagger-multi-turn-chat-screenshot.png){: .blog-img }

## How can you use it?

1. **Check for an existing session**: If you want to jump back into a prior convo, pass along your `session_id`.
2. **Start fresh**: If you omit the `session_id`, the system will create one for you automatically, so you can begin a brand-new conversation.
3. **Stay secure**: Each request needs an API key because the endpoint uses an LLM for those rich, context-savvy responses.
4. **Test it out**: Use the built-in `/chat` documentation in your API reference or Admin App to see multi-turn chat in action.

## Benefits at a glance

- **Fluid follow-ups**: No more rehashing context or manually stitching together old responses—just ask away.
- **Reduced complexity**: Streamlined conversation management thanks to Redis caching.
- **Scalable**: The endpoint adapts whether you’re running small pilot Q&As or enterprise-scale chat solutions.

## Doc references

- [Multi-turn Chat Setup](../../components/multi-turn-chat/index.md)
- [Search Endpoint](../../components/search/index.md)
- [Admin App Authentication](../../components/admin-app/auth/index.md)
