# Writing and Running Tests for the In-house Speech Service

This guide outlines the process for writing, running, and debugging tests for the in-house Speech Service.

## Adding new tests

When developing new features for Speech Service, it's crucial to add corresponding unit tests. These tests should be placed in the following directory:
`optional_components/speech_api/tests`.

## Executing unit Tests

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

To run the unit tests, simply use the following command:

```shell
make tests
```

This command handles all necessary steps, including:

1. Building the Docker container for testing
2. Running the tests inside the container
3. Cleaning up after the tests are complete

The entire process is automated, so you don't need to worry about setting up the environment or cleaning up afterwards.

### Debugging unit tests

For debugging, you can modify the process to run an interactive container:

1. First, build the Docker image:

```shell
make setup-tests
```
2. Then, run an interactive container:

```shell
docker run -it --rm --name speech_test_container speech_test /bin/bash
```
3. Once inside the container, you can run tests manually:

```shell
pytest --color=yes -rPQ tests/*
```
Or run specific tests as needed.

4. Exit the container when done (the container will be automatically removed due to the `--rm` flag).

#### Configs for Visual Studio Code

??? note "Add this to your `.vscode/launch.json` file:"

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
                "envFile": "${workspaceFolder}/optional_components/tests/test.env",
                "console": "integratedTerminal",
                "justMyCode": false
            }
        ]
    }
    ```

??? note "Add this to your `.vscode/settings.json` file:"

    Add the following configuration to `.vscode/settings.json` to set the correct pytest
    working directory and environment variables:

    ```json
    {
        "python.testing.cwd": "${workspaceFolder}/optional_components/speech_api",
        "python.testing.pytestArgs": [
            "tests",
            "--rootdir=${workspaceFolder}/optional_components/speech_api"
        ],
        "python.testing.unittestEnabled": false,
        "python.testing.pytestEnabled": true,
        "python.envFile": "${workspaceFolder}/optional_components/speech_api/tests/test.env"
    }
    ```
With these configurations in place, you'll be able to efficiently run and debug your Speech Service tests within Visual Studio Code.
