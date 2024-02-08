There are two ways to interact with the service:

1. Accessing the **API endpoints**
2. The **Admin App**

## API endpoints

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

## Admin app

You can access the admin console at

```
https://[DOMAIN]/
```

On the [Admin app]("./content/admin-app.md"), you can:

- :books: Manage content for more details
- :test_tube: Use the playground to test the Question-Answering service
- :bar_chart: View dashboards
