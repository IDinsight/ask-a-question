# GitHub Actions — Python (FastAPI / Django)

GitHub Actions workflow patterns for Python API projects. Load this reference after the main CI/CD skill has confirmed the stack and target level.

**Official documentation:**
- [GitHub Actions workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Using Python with GitHub Actions](https://docs.github.com/en/actions/guides/building-and-testing-python)
- [astral-sh/setup-uv documentation](https://docs.astral.sh/uv/guides/integration/github/)
- [actions/setup-python documentation](https://github.com/actions/setup-python)
- [actions/upload-artifact documentation](https://github.com/actions/upload-artifact)

## Runtime Setup

Use `uv` for dependency management. Falls back to `pip` if the project uses `requirements.txt` instead of `pyproject.toml`.

### uv (preferred)

```yaml
- uses: actions/checkout@v4
- uses: astral-sh/setup-uv@v4
  with:
    enable-cache: true
- run: uv sync --frozen
```

`--frozen` ensures the lockfile is respected exactly. If a project has no lockfile, use `uv sync` and note it as a gap.

### pip (fallback)

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version-file: '.python-version'
    cache: 'pip'
- run: pip install -r requirements.txt
```

---

## Level 1 — Lint + Test

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run pytest -v --tb=short
```

---

## Level 2 — Add Type Check + Build Verification

```yaml
  type-check:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run mypy app

  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: [lint, type-check, test]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run python -m build
```

For containerized projects, replace the build job with a Docker build:

```yaml
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: [lint, type-check, test]
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t app:ci .
```

---

## Level 3 — Security Scan + Coverage

### Test with coverage

```yaml
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run pytest -v --tb=short --cov=app --cov-report=xml --cov-report=term-missing --cov-fail-under=80
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-report
          path: coverage.xml
          retention-days: 7
```

### Test with PostgreSQL service container

When tests require a real database:

```yaml
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd="pg_isready -U test"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
    env:
      DATABASE_URL: postgresql://test:test@localhost:5432/test_db
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run pytest -v --tb=short --cov=app --cov-report=xml --cov-fail-under=80
```

### Security scanning

```yaml
  security:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run pip-audit
```

### Concurrency and permissions (Level 3+)

Add these at the top of every workflow:

```yaml
permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

---

## Level 4 — SAST + Notifications

### Static analysis with Bandit

```yaml
  sast:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run bandit -r app -ll
```

Bandit checks for common security issues in Python code. Configure severity with `-ll` (medium and high) or `-lll` (high only). For configuration details, see [Bandit documentation](https://bandit.readthedocs.io/).

### Slack notification on failure

```yaml
  notify:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: [lint, type-check, test, build]
    if: failure() && github.ref == 'refs/heads/main'
    steps:
      - uses: slackapi/slack-github-action@v2
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
          webhook-type: incoming-webhook
          payload: |
            {
              "text": "CI failed on main: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
```

---

## Level 5 — Pin Actions + SBOM

At Level 5, pin all third-party actions to full commit SHAs:

```yaml
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
- uses: astral-sh/setup-uv@d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86  # v4
```

Use Dependabot to receive automated update PRs for pinned actions:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

## Matrix Builds

When the project supports multiple Python versions:

```yaml
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.11', '3.12', '3.13']
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
      - run: uv python install ${{ matrix.python-version }}
      - run: uv sync --frozen
      - run: uv run pytest -v --tb=short
```

---

## Common Pitfalls

- **`pip install` instead of `pip install -r requirements.txt` or `uv sync --frozen`.** Without a lockfile reference, CI may install different versions than development.
- **Caching `.venv` directly.** Cache the package manager's store, not the virtual environment. The `setup-uv` action handles this with `enable-cache: true`.
- **Missing `POSTGRES_USER` in service container.** The default user is `postgres`, but health checks with `-U test` fail if the user isn't explicitly created. Always set `POSTGRES_USER` to match the health check.
- **`mypy` failing on missing stubs.** Install type stubs as dev dependencies (`types-requests`, `types-pyyaml`, etc.) or use `--ignore-missing-imports` as a temporary workaround (document it as tech debt).
