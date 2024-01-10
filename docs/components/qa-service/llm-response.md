
# LLM Response

![LLM Response](./llm-response-screenshot.png)

This service returns uses most similar content in the database to construct a
custom answer for the user.

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
  Semantic Search->>LLM: Construct response to question with content
  LLM->>Semantic Search: <LLM Answer>
  Semantic Search->>LLM: Check if answer is consistent with content
  LLM->>Semantic Search: <Consistency score>
  Semantic Search->>User: Return JSON of LLM response and K items

```
