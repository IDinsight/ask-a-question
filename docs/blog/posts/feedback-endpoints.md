---
authors:
  - Sid
category:
  - Admin App
  - LLM Response
  - Embeddings Search
  - Feedback
date: 2024-04-16
---
# Revamped feedback endpoints

There are now two new endpoints for feedback:

1. `POST /response-feedback` - Allows you to capture feedback for the responses returned by either of the
Question-Answering APIs.
2. `POST /content-feedback` - Embeddings Search API, returns the top N content matches to your question. Now you
can also capture feedback for each of these content matches.

<!-- more -->

## Sentiment and Text

For both of these endpoints, you are able to provide either sentiment (positive, negative),
text feedback, or both.

See OpenAPI documentation at `https://[DOMAIN]/api/docs` for more details.

## Content cards show feedback

The positive and negative feedback captured for the content can also be seen in the
"Read" modal for each content card in the Admin App.

![Feedback Admin](../images/feedback-admin-app.png){: .blog-img }

## Doc references

- [Response Feedback](../../components/qa-service/response-feedback.md)
- [Content Feedback](../../components/qa-service/content-feedback.md)
