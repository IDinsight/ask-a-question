#!make

.PHONY : tests

PROJECT_NAME = aaq-core
CONDA_ACTIVATE=source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate
ENDPOINT_URL = localhost:8000

clean:
	find .. -type f -name "*.py[co]" -delete
	find .. -type d -name "__pycache__" -delete
	find .. -type d -name ".pytest_cache" -delete

# Note: Run `make fresh-env psycopg2-binary=true` to manually replace psycopg with psycopg2-binary
fresh-env :
	conda remove --name $(PROJECT_NAME) --all -y
	conda create --name $(PROJECT_NAME) python==3.11 -y

	$(CONDA_ACTIVATE) $(PROJECT_NAME); \
	pip install -r requirements.txt --ignore-installed; \
	pip install -r ../requirements-dev.txt --ignore-installed; \
	pre-commit install

	if [ "$(psycopg2-binary)" = "true" ]; then \
		$(CONDA_ACTIVATE) $(PROJECT_NAME); \
		pip uninstall -y psycopg2==2.9.9; \
		pip install psycopg2-binary==2.9.9; \
	fi

# Running Tests
tests: setup-test-containers run-tests teardown-test-containers
run-tests:
	@set -a && source ./tests/api/test.env && set +a && \
	python -m alembic upgrade head && \
	python -m pytest -rPQ -m "not rails"

# Test DBs
setup-test-containers: setup-test-db setup-alignscore-container

teardown-test-containers: stop-test-db stop-alignscore-container

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

setup-alignscore-container:
	-@docker stop testalignscore
	-@docker rm testalignscore
	docker run --name testalignscore \
		-p 5002:5001 \
		-d alignscore-base:latest
	@sleep 10

stop-alignscore-container:
	@docker stop testalignscore
	@docker rm testalignscore

stop-test-db:
	@docker stop testdb
	@docker rm testdb

# Development DB
setup-db:
	-@docker stop postgres-local
	-@docker rm postgres-local
	@docker system prune -f
	@sleep 2
	@docker run --name postgres-local \
     -e POSTGRES_PASSWORD=postgres \
     -p 5432:5432 \
     -d pgvector/pgvector:pg16
	python -m alembic upgrade head

teardown-db:
	@docker stop postgres-local
	@docker rm postgres-local
