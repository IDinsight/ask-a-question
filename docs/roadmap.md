| Quarter     | Feature                                              | Status             | Description                                                                                                                                       |
| ----------- | ---------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q4 2023     | FastAPI Refactor                                     | :white_check_mark: | Refactored to an all-components-in-one-repo codebase                                                                                              |
|             | LLM-powered search                                   | :white_check_mark: | Match user questions to content in the database using embeddings from LLMs (Open AI)                                                              |
| **Q1 2024** | LLM responses                                        | :white_check_mark: | Craft a custom response to the question using LLM chat and the content in the database                                                            |
|             | AI Guardrails                                        | :white_check_mark: | Keep LLM responses friendly and strictly context-based                                                                                            |
|             | Multi-lingual content                                | :tools:            | Support storage and matching of multi-language variants of FAQs                                                                                   |
| Q2 2024     | Support for low resource language                    | :construction:     | Support question-answering in regional languages. First targets: Xhosa, Zulu, Hindi, Igbo, Hausa                                                  |
|             | Intent Classification & Message Triaging             | :construction:     | Tag user messages with intents & flag urgency                                                                                                     |
|             | Admin app 2.0                                        | :construction:     | A new and better look for Admin App that supports multilingual content management                                                                 |
| Q3 2024     | Content Management Dashboard & Engineering Dashboard | :pencil:           | Monitor uptime, response rates, throughput HTTP response codes. See content use, questions that receive poor feedback, missing content, and more. |
|             | Multi-turn chat                                      | :pencil:           | Refine or clarify user question through conversation.                                                                                             |
|             | Document-based question answering                    | :pencil:           | Retrieve answers from a document set                                                                                                              |
| Q4 2024     | Voice notes support                                  | :pencil:           | Automatic Speech Recognition for audio message to content matching                                                                                |
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
