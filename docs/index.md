# Welcome to AAQ Documentation

AAQ (Ask-a-question) is an LLM-powered question answering service. It presents a number
of REST endpoints to answer questions using a repository of content.

Upcoming features:

* Voice-based Question Answering
* Conversation capability
* Low-resouced language support

## Quick Start

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

**Step 1:** Clone the [repo](https://github.com/IDinsight/aaq-core) to your machine

    git clone git@github.com:IDinsight/aaq-core.git

**Step 2:** Copy `deployment/template.env` to `deployment/.env` and edit it to set the variables

    # Set variables below and copy to .env

    POSTGRES_PASSWORD=
    OPENAI_API_KEY=
    QUESTION_ANSWER_SECRET=
    ...

**Step 3:** Run docker-compose

    cd deployment
    docker compose -f docker-compose.yml -p aaq-stack up -d --build

!!! note "Also see [Calling the endpoints](./develop/testing.md#call-the-endpoints)."

**Step 4:** Shutdown containers

    cd deployment
    docker compose -f docker-compose.yml -p aaq-stack down
