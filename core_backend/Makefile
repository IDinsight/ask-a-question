#!make

.PHONY : tests

# Main test target
tests: setup-test-containers run-tests teardown-test-containers

# Test runner
# NB: `pytest-alembic` requires the DB engine to point an empty database. Thus, alembic
# tests should be run first.
run-tests:
	@set -a && source ./tests/api/test.env && set +a && \
	python -m pytest -rPQ -m "not rails and alembic" --cov-report term-missing --cov-config=../pyproject.toml --cov=. tests/api/test_alembic_migrations.py && \
	python -m pytest -rPQ -m "not rails and not alembic" --cov-report term-missing --cov-config=../pyproject.toml --cov-append --cov=. tests

## Helper targets
setup-test-containers: setup-test-db setup-redis-test
teardown-test-containers: teardown-test-db teardown-redis-test

setup-test-db:
	-@docker stop testdb
	-@docker rm testdb
	@docker system prune -f
	@sleep 2
	@set -a && source ./tests/api/test.env && set +a && \
	docker run --name testdb \
		-p 5433:5432 \
		-e POSTGRES_PASSWORD \
		-e POSTGRES_USER \
		-e POSTGRES_DB \
		-d pgvector/pgvector:pg16
	@set -a && source ./tests/api/test.env && set +a && \
	python -m alembic upgrade head

# Use port 6381 since port 6379 is used for dev and 6380 for docker-compose
setup-redis-test:
	-@docker stop redis-test
	-@docker rm redis-test
	@docker system prune -f
	@sleep 2
	@docker run --name redis-test \
	-p 6381:6379 \
     -d redis:6.0-alpine

teardown-redis-test:
	@docker stop redis-test
	@docker rm redis-test

teardown-test-db:
	@docker stop testdb
	@docker rm testdb

# alignscore containers (if it is needed)
# Use port 5002 since port 5001 is used for dev
setup-alignscore-container:
	-@docker stop testalignscore
	-@docker rm testalignscore
	docker run --name testalignscore \
		-p 5002:5001 \
		-d alignscore-base:latest
	@sleep 10

teardown-alignscore-container:
	@docker stop testalignscore
	@docker rm testalignscore
