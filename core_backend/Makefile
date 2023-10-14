#!make

.PHONY : tests setup-test-db setup-test-vector-db run-tests stop-test-db stop-test-vector-db

ifneq (,$(wildcard ./.env))
	include .env
	export
endif


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
