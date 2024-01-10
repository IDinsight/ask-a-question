# Question-Answering Service

There are two major endpoints that your application can integrate with:


<div class="grid cards" markdown>

-   :material-api:{ .lg .middle .red} __Semantic Search__

    ---

    Allows searching through the content database. Use similarity between
    embeddings of questions and the content to return the best matches

    [:octicons-arrow-right-24: More info](./semantic-search.md)

-   :material-react:{ .lg .middle } __LLM Response__

    ---

    Constructs an answer to the user's questions using an LLM and the most similar
    content in the database.

    [:octicons-arrow-right-24: More info](./llm-response.md)

</div>

## SwaggerUI

<img src="./swagger-ui-screenshot.png" alt="swagger-ui-screenshot" style="border: 1px solid  lightgray;">

If you have the [application running](../../deployment/quick-setup.md), you can access
the SwaggerUI at


    https://[DOMAIN]/api/docs

or if you are using the [dev](../../develop/setup.md) setup:

    http://localhost:8000/docs




## Upcoming

- [ ] Chat capability
