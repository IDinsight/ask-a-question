#!make

.PHONY : tests setup-test-db setup-test-vector-db run-tests stop-test-db stop-test-vector-db

ifneq (,$(wildcard ./.env))
	include .env
	export
endif


tests: setup-test-db setup-test-vector-db run-tests stop-test-db stop-test-vector-db

setup-test-db:
	-@docker stop testdb
	-@docker rm testdb
	@docker system prune -f
	@sleep 2
	@export POSTGRES_USER=postgres-test-user POSTGRES_PASSWORD=postgres-test-pw \
		POSTGRES_DB=postgres-test-db POSTGRES_PORT=5433 && \
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

run-tests:
	@export POSTGRES_USER=postgres-test-user POSTGRES_PASSWORD=postgres-test-pw \
		POSTGRES_DB=postgres-test-db POSTGRES_PORT=5433 \
		QDRANT_COLLECTION_NAME=test_collection \
		QDRANT_PORT=6334 && \
	python -m alembic upgrade head && \
	python -m pytest -rPQ

stop-test-db:
	@docker stop testdb
	@docker rm testdb

stop-test-vector-db:
	@docker stop testvectordb
	@docker rm testvectordb

setup-test-state:
	@export POSTGRES_USER=postgres-test-user \
	    POSTGRES_PASSWORD=postgres-test-pw \
		POSTGRES_DB=postgres-test-db POSTGRES_PORT=5433 \
		QDRANT_COLLECTION_NAME=test_collection \
		QDRANT_PORT=6334 && \
	python -m alembic upgrade head

setup-debug: setup-test-db setup-test-vector-db setup-test-state

teardown-debug: stop-test-db stop-test-vector-db
