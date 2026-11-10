# Writing and running tests

If you are writing new features, you should also add tests. Tests live under
`core_backend/tests` and mirror the feature layout of `core_backend/app`.

## Layout

Each feature gets one test file per layer:

```
tests/
├── conftest.py                         # shared fixtures (users, workspaces, client)
├── test.env                            # test settings, loaded automatically
├── tags/
│   ├── test_tags_router.py             # HTTP: status codes, auth, validation
│   ├── test_tags_service.py            # business rules, repository mocked out
│   └── test_tags_repository.py         # SQL against a real Postgres
├── users/
│   └── ...
├── core/                               # app/core (database, utils, observability)
├── migrations/                         # alembic migration tests
├── bdd/                                # pytest-bdd user/workspace scenarios
└── question_answer/rails/              # guardrail tests that call a real LLM
```

How each layer is tested:

- **Router tests** go through `TestClient(app)` (the `client` fixture). To reach an
  error branch, patch the service function the router imports, or use
  `app.dependency_overrides` and reset it afterwards.
- **Service tests** don't touch the database or the network. Patch the repository
  functions the service imports with `unittest.mock.AsyncMock`.
- **Repository tests** use the `rollback_asession` fixture. Everything they write
  is rolled back when the test ends, so they need no clean-up code.

## Running tests

!!! warning "You need to have installed [Docker](https://docs.docker.com/get-docker/)"

From `core_backend/`:

    uv run pytest

That's it. You don't need to source any env file or start containers:

- `tests/test.env` is loaded automatically. Variables you export in your shell take
  priority. Your dev `core_backend/.env` is never read during tests.
- If the test Postgres (port 5433) or Redis (port 6381) is not reachable, the
  `testdb` and `redis-test` containers are started for you.
- Every run gets a **brand-new database**, copied from a migrated template. The
  template is rebuilt only when the migrations change. The test database name must
  contain `test`, otherwise the run stops instead of dropping it.

Useful variations:

    uv run pytest tests/tags                 # one feature
    uv run pytest --cov                      # with coverage (fails under 80%)
    uv run pytest --durations=10             # find slow tests
    uv run pytest -p no:randomly             # fixed order (pytest-randomly shuffles)
    make teardown-test-containers            # stop and remove the test containers

### Debugging unit tests

Because the settings load automatically, the VS Code test explorer and debugger
work with no extra env file. Point them at `core_backend`:

??? note "`.vscode/settings.json`"

    ```json
    {
        "python.testing.cwd": "${workspaceFolder}/core_backend",
        "python.testing.pytestArgs": ["tests"],
        "python.testing.unittestEnabled": false,
        "python.testing.pytestEnabled": true
    }
    ```

## Running optional tests

Some tests are not run by default because they call a real LLM:

- *Language Identification*: checks that the solution can identify the language of
  a short sample text.
- *Test if LLM response aligns with provided context*: checks for hallucinations by
  testing whether the LLM response is supported by the provided context.
- *Test safety*: tests for prompt injection and jailbreaking.

These need the LiteLLM Proxy server to be running. From the repository root:

    make setup-llm-proxy

Then, with your LLM credentials exported in the shell:

    cd core_backend
    uv run pytest -m rails tests/question_answer/rails
