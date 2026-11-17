#!make

SHELL := /bin/bash

.PHONY : lint check audit tests tests-alembic tests-rails teardown-test-containers

# The same non-SAST checks CI runs in Phase 1: ruff, mypy and the dependency audit.
check:
	uv run ruff check .
	uv run mypy .
	$(MAKE) audit

# Audit exactly what ships (locked runtime deps, no dev group), as CI does.
# Nothing is installed; pip-audit checks the pinned versions against OSV/PyPI.
audit:
	@req=$$(mktemp) && trap 'rm -f "$$req"' EXIT && \
	uv export --locked --no-dev --no-emit-project --format requirements-txt -o "$$req" -q && \
	uvx pip-audit==2.9.0 -r "$$req" --disable-pip --progress-spinner off

# Format, lint, type-check and SAST (config in pyproject.toml and .pylintrc).
lint:
	uv run black .
	uv run ruff check .
	uv run mypy .
	uv run bandit -c pyproject.toml -r . -q
	uv run pylint app tests

# `uv run pytest` is all you need. tests/__init__.py loads tests/test.env, and
# tests/conftest.py starts the `testdb` / `redis-test` docker containers when they
# are not running, then recreates a clean, migrated test database on every run.
# The real-LLM `rails` tests are excluded by default (see [tool.pytest] addopts).

# Whole suite (features, alembic migrations, BDD) with the 80% coverage gate.
tests:
	uv run pytest --cov --cov-report=term-missing

# Only the alembic migration tests (they use their own empty database).
tests-alembic:
	uv run pytest -m alembic tests/migrations

# Guardrail tests that call a real LLM (needs LLM credentials in your shell).
tests-rails:
	uv run pytest -m rails tests/question_answer/rails

# The containers are left running between runs to keep start-up fast.
teardown-test-containers:
	-@docker stop testdb redis-test
	-@docker rm testdb redis-test
