# Semantic Search

![Semantic Search](./semantic-search-screenshot.png)

This service returns the contents from the database with the most similar vector
embeddings to the question. The content returned is exactly what is the database.

See OpenAPI specification or [SwaggerUI](index.md/#swaggerui) for more details on how to call the service.

## Process flow

```mermaid
sequenceDiagram
  autonumber
  User->>AAQ: User's question
  AAQ->>LLM: Identify language
  LLM->>AAQ: <Language>
  AAQ->>LLM: Translate text
  LLM->>AAQ: <Translated text>
  AAQ->>LLM: Paraphrase question
  LLM->>AAQ: <Paraphrased question>
  AAQ->>Vector DB: Request N most similar contents in DB
  Vector DB->>AAQ: <N contents with similarity score>
  AAQ->>User: Return JSON of N contents

```
