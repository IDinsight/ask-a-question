
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

## Optional components

### Align Score

In the Process Flow above, _Step 12: Check if answer is consistent with content_ can
be done using [AlignScore](https://github.com/yuh-zha/AlignScore).

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
  Semantic Search->>AlignScore: Check if answer is consistent with content
  AlignScore->>Semantic Search: <Consistency score>
  Semantic Search->>User: Return JSON of LLM response and K items

```

#### Enable Align Score

To enable using AlignScore for checking content consistency, set `ALIGN_SCORE_METHOD`
config variable to `AlignScore`. See [Configuring AAQ](../../deployment/config-options.md)
for ways to set this.

#### Setup infrastructure

To use AlignScore, AAQ needs access to the AlignScore service. This can be deployed
using a docker container. See [AlignScore](../../other-components/align-score/index.md) under
__Other Components__ for how to do this.
