# Writing and running tests

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

## Running unit tests

??? warning "Don't run `pytest` directly"
    Unless you have updated your environment variables and started a testing instance
    of postrges and qdrant, the tests will end up writing to your dev environment :weary_cat:

Run tests using

    make tests

This target starts up new postgres and qdrant container for testing. It also sets the
correct environment variables, runs `pytest`, and then destroys the containers.

### Debugging unit tests

Before debugging, run `make setup-test-dbs` within `core_backend` to launch new postgres and
qdrant containers for testing and set the correct environment variables.

After debugging, clean up the testing resources by calling `make teardown-test-dbs`.

#### Configs for Visual Studio Code

??? note "`.vscode/launch.json`"

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

??? note "`.vscode/settings.json`"

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

See [Quick Start](../index.md#quick_start) for how to start the application stack using docker-compose.

Alternatively, you can run each of the containers manually as per [dev setup](setup.md).

### Call the endpoints

To use FastAPI's WebGUI to call the endpoints easily, navigate to

    http://localhost:8000/docs

and run endpoints as desired.

??? warning "Authorising the `/embedding_search` and `/llm-response` endpoints"
    To use these endpoints, you'll have to Authorise and set the bearer token to the value of `QUESTION_ANSWER_SECRET`.

    The default value can be found in `core_backend/app/configs/app_config.py` but may have been overridden if the
    environment variable was manually set differently.
