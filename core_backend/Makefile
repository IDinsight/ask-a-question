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
	pip install --upgrade pip; \
	pip install -r requirements.txt --ignore-installed; \
	pip install -r ../requirements-dev.txt --ignore-installed; \
	pre-commit install

	if [ "$(replace_psycopg_w_binary)" = "true" ]; then \
		$(CONDA_ACTIVATE) $(PROJECT_NAME); \
		pip uninstall -y psycopg2; \
		pip install psycopg2-binary==2.9.7; \
	fi

tests: setup-test-db setup-test-vector-db run-tests stop-test-db stop-test-vector-db

setup-tests: setup-test-db setup-test-vector-db setup-test-state

teardown-tests: stop-test-db stop-test-vector-db

setup-test-db:
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

setup-test-vector-db:
	-@docker stop testvectordb
	-@docker rm testvectordb
	docker run --name testvectordb \
		-p 6334:6333 \
		-d qdrant/qdrant

setup-test-state:
	@set -a && source ./tests/test.env && set +a && \
	python -m alembic upgrade head

run-tests:
	@set -a && source ./tests/test.env && set +a && \
	python -m alembic upgrade head && \
	python -m pytest -rPQ

stop-test-db:
	@docker stop testdb
	@docker rm testdb

stop-test-vector-db:
	@docker stop testvectordb
	@docker rm testvectordb
