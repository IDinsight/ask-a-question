---
authors:
  - Amir
category:
  - API

date: 2024-07-22
---
# One Endpoint to Rule Them All

We refactored our two question-answering endpoints into a single one called `/search` for clarity and ease of use.

<!-- more -->

## Why change?

We realised our two `/embeddings-search` and `/llm-response` endpoints were a bit confusing, and since they performed very similar tasks we combined them into one for ease of use.

## What's new?

We now have a single endpoint called `/search` which always returns the top contents in the database that most
closely matched your query and can optionally return an LLM-generated resposne to your question.

![Search endpoint](../../components/qa-service/search.png)

We've also simplified the parameters in our response model so it's easier to use. We will now respond with something like this:

```json
{
    "query_id": 1,
    "llm_response": "Example LLM response "
    "(null if generate_llm_response is False)",
    "search_results": {
        "0": {
            "title": "Example content title",
            "text": "Example content text",
            "id": 23,
            "distance": 0.1,
        },
        "1": {
            "title": "Another example content title",
            "text": "Another example content text",
            "id": 12,
            "distance": 0.2,
        },
    },
    "feedback_secret_key": "secret-key-12345-abcde",
    "debug_info": {"example": "debug-info"},
}
```

## Docs references

- [Search](../../components/qa-service/search.md)
