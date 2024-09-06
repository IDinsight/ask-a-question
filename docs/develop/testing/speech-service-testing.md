# Writing and Running Tests for Speech Service

This guide outlines the process for writing, running, and debugging tests for the Speech Service.

## Adding new tests

When developing new features for Speech Service, it's crucial to add corresponding unit tests. These tests should be placed in the following directory:
`optional_components/speech_api/tests`.

## Running unit tests

**Environment Setup**

Please use the `aaq-speech` environment to run speech tests. You can create this environment using the following command from the root directory:

```shell
make fresh-env-speech
```

## Executing Tests

To run the tests, use the following command:

```shell
make tests
```

??? info "This command performs the following actions"

    1. Creates the required directories
    2. Downloads the necessary models
    3. Runs `pytest`
    4. Cleans up by removing the created models and directories

    This automated process simplifies test execution and cleanup.

## Debugging unit tests

Debugging these tests can be done normally, as no containers are required in the process.

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
