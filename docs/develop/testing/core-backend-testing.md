# Writing and running tests

If you are writing new features, you should also add unit tests. Tests are under
`core_backend/tests`.

## Running unit tests

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

??? warning "Don't run `pytest` directly"
    Unless you have updated your environment variables and started a testing instance
    of postgres, the tests will end up writing to your dev environment :weary_cat:

Run tests using:

    make tests

This target starts up new postgres and redis containers for testing. It also sets the
correct environment variables, runs `pytest`, and then destroys the containers once done.

### Debugging unit tests

Before debugging, run `make setup-test-db` within `core_backend` to launch new postgres container for testing and set the correct environment variables.

After debugging, clean up the testing resources by calling `make teardown-test-db`.

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
                "envFile": "${workspaceFolder}/core_backend/tests/api/test.env",
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
        "python.envFile": "${workspaceFolder}/core_backend/tests/api/test.env"
    }
    ```

## Running optional tests

There are some additional tests that are not run by default. Most of these
either make call to OpenAI or depend on other components:

- *Language Identification*: Tests if the the solution is able to identify the
language given a short sample text.
- *Test if LLM response aligns with provided context*: Tests for hallucinations by
checking if the LLM response is supported by the provided context.
- *Test safety*: Tests for prompt injection and jailbreaking.

These tests will require the LiteLLM Proxy server to be running (to accept LLM calls). You can run this by going to root and running:

    make setup-llm-proxy

Then run the tests using:

    cd core_backend
    make setup-test-db
    python -m pytest -m rails

And when done:

    make teardown-test-db
