| Quarter     | Feature                                              | Status             | Description                                                                                                                                       |
| ----------- | ---------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q4 2023     | FastAPI Refactor                                     | :white_check_mark: | Refactored to an all-components-in-one-repo codebase                                                                                              |
|             | Embeddings-based search                              | :white_check_mark: | Match user questions to content in the database using embeddings                                                                                  |
| Q1 2024     | RAG responses                                        | :white_check_mark: | Craft a custom response to the question using LLM based on retrieved content in the database                                                      |
|             | Guardrails                                           | :white_check_mark: | Keep LLM responses friendly and strictly context-based                                                                                            |
| Q2 2024     | Message Triaging                                     | :white_check_mark: | Tag user messages with intents & flag urgency                                                                                                     |
|             | Multi-user with Google log-in                        | :white_check_mark: | You can now have 1 AAQ deployment with multiple users, each with their own content DB                                                             |
|             | Support for Turn.io, Glific integration              | :white_check_mark: | Add AAQ to popular chat flow builders in social sector, like Turn.io and Glific                                                                   |
|             | Content Tags                                         | :white_check_mark: | Add tags to your content for easy browsing (and more to come!)                                                                                    |
| **Q3 2024** | Analytics for Feedback and Content                   | :white_check_mark: |  See content use, questions that receive poor feedback, missing content, and more                                                                 |
|             | Voice notes support                                  | :white_check_mark: | Automatic Speech Recognition for audio message to content matching                                                                                |
|             | Multi-turn chat                                      | :pencil:           | Refine or clarify user question through conversation.                                                                                             |
|             | Engineering Dashboard                                | :pencil:           | Monitor uptime, response rates, throughput HTTP response codes                                                                                    |
| Q4 2024     | Personalization and contextualization                | :pencil:           | Use contextual information to improve responses                                                                                                   |
|             | Multimedia content                                   | :pencil:           | Respond with not just text but images and audio as well.                                                                                          |
|             | A/B Testing                                          | :pencil:           | Test and decide content that works better for users                                                                                               |

!!! info "Key <br> :white_check_mark:: Completed <br> :tools:: Under development <br> :construction:: Queued <br>:pencil:: Yet to be scoped"

Beyond 2024

- Multi-tenant architecture
- User configurable Guardrails (in Admin app)
- Feedback-based model/LLM fine tuning
- Safety tests, fairness reports and ethical reviews
