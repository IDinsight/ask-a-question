#!make

.PHONY : tests

PROJECT_NAME = aaq-core
CONDA_ACTIVATE=source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate

clean:
	find .. -type f -name "*.py[co]" -delete
	find .. -type d -name "__pycache__" -delete
	find .. -type d -name ".pytest_cache" -delete

# Note: Run `make fresh-env replace_psycopg_w_binary=true` to manually replace psycopg with psycopg-binary
fresh-env :
	conda remove --name $(PROJECT_NAME) --all -y
	conda create --name $(PROJECT_NAME) python==3.10 -y

	$(CONDA_ACTIVATE) $(PROJECT_NAME); \
	pip install -r requirements.txt --ignore-installed; \
	pip install -r ../requirements-dev.txt --ignore-installed; \
	pre-commit install

	if [ "$(psycopg_binary)" = "true" ]; then \
		$(CONDA_ACTIVATE) $(PROJECT_NAME); \
		pip uninstall -y psycopg2; \
		pip install psycopg2-binary==2.9.7; \
	fi

# Running Tests
tests: setup-test-relational-db setup-test-vector-db run-tests stop-test-relational-db stop-test-vector-db

run-tests:
	@set -a && source ./tests/test.env && set +a && \
	python -m alembic upgrade head && \
	python -m pytest -rPQ

# Test DBs
setup-test-relational-dbs: setup-test-relational-db setup-test-vector-db

teardown-test-dbs: stop-test-relational-db stop-test-vector-db

setup-test-relational-db:
	-@docker stop testdb
	-@docker rm testdb
	@docker system prune -f
	@sleep 2
	@set -a && source ./tests/test.env && set +a && \
	docker run --name testdb \
		-p 5433:5432 \
		-e POSTGRES_PASSWORD \
		-e POSTGRES_USER \
		-e POSTGRES_DB \
		-d postgres
	@set -a && source ./tests/test.env && set +a && \
	python -m alembic upgrade head

setup-test-vector-db:
	-@docker stop testvectordb
	-@docker rm testvectordb
	docker run --name testvectordb \
		-p 6334:6333 \
		-d qdrant/qdrant

stop-test-relational-db:
	@docker stop testdb
	@docker rm testdb

stop-test-vector-db:
	@docker stop testvectordb
	@docker rm testvectordb

# Development DBs

setup-dbs: setup-relational-db setup-vector-db

teardown-dbs: stop-relational-db stop-vector-db

setup-relational-db:
	-@docker stop postgres-local
	-@docker rm postgres-local
	@docker system prune -f
	@sleep 2
	@docker run --name postgres-local \
     -e POSTGRES_PASSWORD=postgres \
     -p 5432:5432 \
     -d postgres
	python -m alembic upgrade head

setup-vector-db:
	-@docker stop qdrant-local
	-@docker rm qdrant-local
	docker run --name qdrant-local \
     -p 6333:6333 \
     -d qdrant/qdrant

stop-relational-db:
	@docker stop postgres-local
	@docker rm postgres-local

stop-vector-db:
	@docker stop qdrant-local
	@docker rm qdrant-local
