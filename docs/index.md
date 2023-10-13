# Welcome to AAQ Documentation

AAQ (Ask-a-question) is an LLM-powered question answering service. It presents a number
of REST endpoints to answer questions using a repository of content.

Upcoming features:

* Voice-based Question Answering
* Conversation capability
* Low-resouced language support

## Quick Start

You need [Docker](https://docs.docker.com/get-docker/)

**STEP 1:** Clone the [repo](https://github.com/IDinsight/aaq-core) to your machine

    git clone git@github.com:IDinsight/aaq-core.git

**STEP 2:** Copy `deployment/template.env` to `deployment/.env` and edit it to set the variables

    # Set variables below and copy to .env

    POSTGRES_PASSWORD=
    OPENAI_API_KEY=
    QUESTION_ANSWER_SECRET=
    ...

**STEP 3:** Run docker-compose

    cd deployment
    docker compose -f docker-compose.yml -p aaq-stack up -d --build

**STEP 4:** Shutdown containers

    cd deployment
    docker compose -f docker-compose.yml -p aaq-stack down
