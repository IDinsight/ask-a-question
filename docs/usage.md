## Usage

There are two major endpoints for Question-Answering:

- **Embeddings search:** Finds the most similar content in the database using cosine similarity between embeddings.
- **LLM response:** Crafts a custom response using LLM chat using the most similar content.

See [docs](https://idinsight.github.io/aaq-core/) or SwaggerUI at `https://<DOMAIN>/api/docs` or `https://<DOMAIN>/docs` for more details and other API endpoints.

### :question: Embeddings search

```
curl -X 'POST' \
  'https://[DOMAIN]/api/embeddings-search' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <BEARER TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
  "query_text": "how are you?",
  "query_metadata": {}
}'
```

### :robot: LLM response

```
curl -X 'POST' \
  'https://[DOMAIN]/api/llm-response' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <BEARER TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
  "query_text": "this is my question",
  "query_metadata": {}
}'
```

### :books: Manage content

You can access the admin console at

```
https://[DOMAIN]/
```

See ["Managing content"]("./content/admin-app.md") for more details
