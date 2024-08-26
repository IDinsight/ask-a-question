# Voice-Search

![Voice-Search endpoint](./voice-search.png)

This service accepts an audio file URL, transcribes the speech to text, processes the query similar to the text-based search, and returns both a text response and an audio response URL.

See OpenAPI specification or [SwaggerUI](index.md/#swaggerui) for more details on how to call the service.

## Process flow for End to End Speech Generation

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '16px', 'messageFontSize': '16px', 'noteMargin': '10px'}}}%%
sequenceDiagram
    participant User
    participant AAQ
    participant Speech-to-Text
    participant LLM
    participant Vector DB
    participant Text-to-Speech

    User->>AAQ: Audio file URL
    AAQ->>Speech-to-Text: Transcribe audio
    Speech-to-Text->>AAQ: Transcribed text
    AAQ->>LLM: Identify language
    LLM->>AAQ: <Language>
    AAQ->>LLM: Paraphrase question
    LLM->>AAQ: <Paraphrased question>
    AAQ->>Vector DB: Request N most similar contents in DB
    Vector DB->>AAQ: <N contents with similarity score>
    AAQ->>LLM: Generate response based on contents
    LLM->>AAQ: <Text response>
    AAQ->>Text-to-Speech: Convert text response to audio
    Text-to-Speech->>AAQ: Audio file URL
    AAQ->>User: Return JSON with text response, audio URL, and N contents

```

## Voice Service Integration

For detailed information on how to integrate voice capabilities into your application using AAQ, including setup instructions for both in-house and cloud-based speech services, please refer to our **Voice Service** documentation.

<div class="grid cards" markdown>

- :material-api:{ .lg .middle } __This documentation covers__

    ---

    - Setting up the dockerized container for in-house ASR and TTS models
    - Configuring Google Cloud Speech-to-Text and Text-to-Speech integration
    - Best practices for voice input and output in your application

    [:octicons-arrow-right-24: Explore Voice Service Integration](../voice-service/index.md)

</div>
