# Writing and running tests

!!! note "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

## Running unit tests

### Running all unit tests

??? warning "Don't run `pytest` directly"
    Unless you have updated your environment variables and started a testing instance
    of postrges and qdrant, the tests will end up writing to your dev environment :weary_cat:

Setup your openAPI API key

    export OPENAI_API_KEY=<YOUR KEY>

Run tests using

    make tests

This target starts up new postgres and qdrant container for testing. It also sets the
correct environment variables, runs `pytest`, and then destroys the containers.

### Debugging unit tests

Before debugging, run `make setup-tests` within `core_backend` to launch new postgres and
qdrant containers for testing and set the correct environment variables.

After debugging, clean up the testing resources by calling `make teardown-tests`.

### Debugging on Visual Studio Code

Add the following configuration to your `.vscode/launch.json` file to set environment
variables for debugging:

```json
{
    "version": "0.2.0",
    "configurations": [
        {  // configuration for debugging
            "name": "Python: Tests in current file",
            "purpose": ["debug-test"],
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "args": ["--color=yes"],
            "envFile": "${workspaceFolder}/core_backend/tests/test.env",
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

Add the following configuration to `.vscode/settings.json` to set the correct pytest
working directory and environment variables:

```json
{
    "python.testing.cwd": "${workspaceFolder}/core_backend",
    "python.testing.pytestArgs": [
        "tests",
        "--rootdir=${workspaceFolder}/core_backend"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
    "python.envFile": "${workspaceFolder}/core_backend/tests/test.env"
}
```

## Calling endpoints

### Run the app

See [Quick Start](../index.md#quick_start) for how to start the application stack
using docker-compose.

Alternatively, you can run each of the containers manually as per [dev setup](setup.md)

The following curl commands call the endpoints:

#### 1. Create some content

    curl -X POST -d '{"content_text":"The tennis racquet, an extension of a player'\''s arm, is a marvel of engineering and design. From its early wooden iterations to today'\''s advanced composite materials, the racquet has evolved to enhance performance on the court. With the right balance, weight, and string tension, a tennis racquet can make all the difference in those match-winning shots."}' -H 'Content-Type: application/json' localhost:8000/content/create

Note the `content_id`. You'll need it for steps 4 and 5.

#### 2. Send a question

??? note "The QUESTION_ANSWER_SECRET parameter"
    You'll need to know your `QUESTION_ANSWER_SECRET`. The default value can be found
    in `core_backend/app/configs/app_config.py` but can be overridden by setting the environment
    variable.

    curl -X POST -d '{"query_text":"i love sport, tell me about a vegetable that will keep be strong"}'  \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer [QUESTION_ANSWER_SECRET]' \
    localhost:8000/embeddings-search

Note the `query_id` and `feedback_secret_key`. You'll need them for the next command.

#### 3. Send feedback

    curl -X POST -S -d '{"query_id":"[QUERY_ID]","feedback_secret_key":"[SECRET_KEY]", \
    "feedback_text":"this is feedback" }' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer [QUESTION_ANSWER_SECRET]' \
    localhost:8000/feedback

#### 4. Edit the content

    curl -X PUT -d '{"content_text":"content 2 updated"}' \
    -H 'Content-Type: application/json' localhost:8000/content/[CONTENT_ID]/edit

#### 5. Delete the content

    curl -X DELETE localhost:8000/content/[CONTENT_ID]/delete
