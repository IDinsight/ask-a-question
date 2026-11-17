# Document Ingestion aka DocMuncher

`/docmuncher` is the endpoint that allows document uploads. We then chunk each uploaded document to create content cards tagged with each document name.
This content is then searchable using the `/search` endpoints.

<img src="./docmuncher_api.png">

There are specifically two endpoints: the `POST` endpoint accepts document uploads (.pdf or .zip) and creates FastAPI background tasks for each document uploaded. The `GET` endpoints return the status of the created jobs.

## Process flow for document ingestion

```mermaid
sequenceDiagram
  autonumber
  Admin App->>Backend: Document upload
  Backend->>MistralAI: Convert document text to Markdown
  MistralAI->>LangChain: Chunk Markdown text by headers
  LangChain->>Backend: <Markdown chunks>
  Backend->>Backend: Post-process chunks for continuity, formatting
  Backend->>Admin App: <Final content cards + tags>
```

## Upcoming

- [ ] Semantiic clustering: cluster cards with similar content
- [ ] Paraphrasing cards for brevity
