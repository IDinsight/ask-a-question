There are two ways to interact with the service:

1. Accessing the **API endpoints**
2. The **Admin App**

## API endpoints

To get answers from your database of contents, you can use the `/search` endpoint. This endpoint returns the following:

- Search results: Finds the most similar content in the database using cosine distance between embeddings.
- (Optionally) LLM generated response: Crafts a custom response using LLM chat using the most similar content.

You can also add your contents programatically using API endpoints. See [docs](https://docs.ask-a-question.com/) or SwaggerUI at `https://<DOMAIN>/api/docs` or `https://<DOMAIN>/docs` for more details and other API endpoints.

### :question: Embeddings search

```
curl -X 'POST' \
  'https://[DOMAIN]/api/search' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <BEARER TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
  "query_text": "how are you?",
  "generate_llm_response": false,
  "query_metadata": {}
}'
```

### :robot: LLM response

```
curl -X 'POST' \
  'https://[DOMAIN]/api/search' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <BEARER TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
  "query_text": "this is my question",
  "generate_llm_response": true,
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
