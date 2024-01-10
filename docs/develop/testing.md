# Writing and running tests

If you are writing new features, you should also add unit tests. Tests are under
`core_backend/tests`.

## Running unit tests

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

??? warning "Don't run `pytest` directly"
    Unless you have updated your environment variables and started a testing instance
    of postrges and qdrant, the tests will end up writing to your dev environment :weary_cat:

Run tests using:

    make tests

This target starts up new postgres and qdrant containers for testing. It also sets the
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

There are a bunch of additional tests that are not run by default. Most of these
either make call to OpenAI or depend on other components:

- *Language Identification*: Tests if the the solution is able to identify the
language given a short sample text.
- *Test if LLM response aligns with provided context*: Tests for hallucinations by
checking if the LLM response is supported by the provided context.
- *Test safety*: Tests for prompt injection and jailbreaking.

You can run these test using:

```bash
cd /core_backend
python -m pytest -m rail
```

!!! Note

    Remember to export the right API keys or setup the required service before you
    run the tests. For example, for test that call OpenAI, you should export your
    OpenAI key:

    ```bash
    export OPENAI_API_KEY=sk-...
    ```

    See "Other Components" for how to setup required infrastructure.


## Calling endpoints

### Run the app

- *Option 1 [Docker Compose]*: See [Quick Start](../index.md#quick_start) for how to start the application stack using docker-compose.
- *Option 2 [Dev Setup]*: Run each container manually as per [dev setup](setup.md).


### Call the endpoints

You can use FastAPI's Swagger UI to test out the desired endpoints

``` yaml
https://[DOMAIN]/api/docs # (1)!
```

1.  if you are using the [dev setup](setup.md), you can access it at `http://localhost:8000/docs`


??? warning "Authorising the `/embedding_search` and `/llm-response` endpoints"
    To use these endpoints, you'll have to Authorise and set the bearer token to the
    value of `QUESTION_ANSWER_SECRET`.

    The default value can be found in `core_backend/app/configs/app_config.py` but may have been overridden if the
    environment variable was manually set differently.
