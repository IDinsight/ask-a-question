| Quarter     | Feature                                              | Status             | Description                                                                                                                                       |
| ----------- | ---------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q4 2023     | FastAPI Refactor                                     | :white_check_mark: | Refactored to an all-components-in-one-repo codebase                                                                                              |
|             | Embeddings-based search                              | :white_check_mark: | Match user questions to content in the database using embeddings                                                                                  |
| Q1 2024     | RAG responses                                        | :white_check_mark: | Craft a custom response to the question using LLM based on retrieved content in the database                                                      |
|             | AI Guardrails                                        | :white_check_mark: | Keep LLM responses friendly and strictly context-based                                                                                            |
| **Q2 2024** | Message Triaging                                     | :white_check_mark:     | Tag user messages with intents & flag urgency                                                                                                 |
|             | Content Tags                                         | :white_check_mark: | Add tags to your content for easy browsing (and more to come!) |
| Q3 2024     | Engineering Dashboard                                | :pencil:           | Monitor uptime, response rates, throughput HTTP response codes |
|             | Analytics for Feedback and Content                   | :tools:     |  See content use, questions that receive poor feedback, missing content, and more  |
|             | Voice notes support                                  | :tools:            | Automatic Speech Recognition for audio message to content matching                                                                                |
|             | Multi-turn chat                                      | :pencil:           | Refine or clarify user question through conversation.                                                                                             |
| Q4 2024     | Document-based question answering                    | :pencil:           | Retrieve answers from a document set                                                                                                              |
|             | Multimedia content                                   | :pencil:           | Respond with not just text but images and audio as well.                                                                                          |
|             | A/B Testing                                          | :pencil:           | Test and decide content that works better for users                                                                                               |

!!! info "Key <br> :white_check_mark: - Completed <br> :tools: - In active development <br> :construction: - Queued <br>:pencil: - Yet to be scoped"

Beyond 2024

- Privately hosted LLM modules
- Multi-tenant architecture
- User configurable Guardrails (in Admin app)
- Answer contextualization by user demographic
- Feedback-based model/LLM fine tuning
- Safety tests, fairness reports and ethical reviews
