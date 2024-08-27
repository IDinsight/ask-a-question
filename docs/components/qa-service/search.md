# Search

![Search endpoint](./search.png)

This service returns the contents from the database with the most similar vector embeddings to the question
and optionally also uses an LLM to construct a custom answer to the user's question using the retrieved contents.

See OpenAPI specification or [SwaggerUI](index.md/#swaggerui) for more details on how to call the service.

## Process flow without LLM response generation

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
  AAQ->>Vector DB: Request M most similar contents in DB
  Vector DB->>AAQ: <M contents with similarity score>
  AAQ->>Cross-encoder: Re-rank to get top N contents
  Cross-encoder->>AAQ: <N contents with similarity score>
  AAQ->>User: Return JSON of N contents

```

## Process flow with LLM response generation

```mermaid
sequenceDiagram
  autonumber
  User->>AAQ: User's question
  AAQ->>LLM: Identify language
  LLM->>AAQ: <Language>
  AAQ->>LLM: Check for safety
  LLM->>AAQ: <Safety Classification>
  AAQ->>Vector DB: Request N most similar contents in DB
  Vector DB->>AAQ: <N contents with similarity score>
  AAQ->>Cross-encoder: Re-rank to get top N contents
  Cross-encoder->>AAQ: <N contents with similarity score>
  AAQ->>LLM: Given contents, construct response in user's language to question
  LLM->>AAQ: <LLM response>
  AAQ->>LLM: Check if LLM response is consistent with contents
  LLM->>AAQ: <Consistency score>
  AAQ->>User: Return JSON of LLM response and N contents

```

## Optional components

### Align Score

In the Process Flow above, _Step 12: Check if answer is consistent with content_ can
be done using a custom [AlignScore](https://github.com/yuh-zha/AlignScore) model instead
of another LLM call.

``` mermaid
sequenceDiagram
  autonumber
  User->>AAQ: User's question
  AAQ->>LLM: Identify language
  LLM->>AAQ: <Language>
  AAQ->>LLM: Check for safety
  LLM->>AAQ: <Safety Classification>
  AAQ->>Vector DB: Request N most similar contents in DB
  Vector DB->>AAQ: <N contents with similarity score>
  AAQ->>LLM: Construct response to question given contents
  LLM->>AAQ: <LLM response>
  AAQ->>Custom AlignScore Model: Check if LLM response is consistent with contents
  Custom AlignScore Model ->>AAQ: <Consistency score>
  AAQ->>User: Return JSON of LLM response and N contents

```

To use the custom AlignScore model, AAQ needs access to the AlignScore service. See
[documentation](../../components/align-score/index.md) for how to setup
the service and configure AAQ to call it.
