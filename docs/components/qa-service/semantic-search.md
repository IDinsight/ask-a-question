# Semantic Search

![Semantic Search](./semantic-search-screenshot.png)

This service returns the contents from the database with the most similar vector
embeddings to the question. The content returned is exactly what is the database.

See OpenAPI specification or SwaggerUI for more details on how to call the service.

## Process flow
``` mermaid
sequenceDiagram
  autonumber
  User->>Semantic Search: "Aaj ka mausum kaisa hai?"
  Semantic Search->>LLM: Identify Language
  LLM->>Semantic Search: <Language>
  Semantic Search->>LLM: Translate Text
  LLM->>Semantic Search: <Translated Text>
  Semantic Search->>LLM: Paraphrase Question
  LLM->>Semantic Search: <Paraphrased Question>
  Semantic Search->>Vector Db: Find K most similar items in Db
  Vector Db->>Semantic Search: Return K items with similarity score
  Semantic Search->>User: Return JSON of LLM response and K items

```
