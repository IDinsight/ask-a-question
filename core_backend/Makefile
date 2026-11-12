#!make

SHELL := /bin/bash

.PHONY : lint tests tests-alembic tests-rails teardown-test-containers

# Format, lint and type-check (config in pyproject.toml and .pylintrc).
lint:
	uv run black .
	uv run ruff check .
	uv run mypy app tests --ignore-missing-imports --explicit-package-base
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
