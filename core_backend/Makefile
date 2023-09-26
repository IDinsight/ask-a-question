#!make

.PHONY : tests
tests:
	-docker stop testdb
	-docker rm testdb
	@docker system prune -f
	@sleep 2
	@export POSTGRES_USER=postgres-test-user POSTGRES_PASSWORD=postgres-test-pw \
		POSTGRES_DB=postgres-test-db POSTGRES_PORT=5433 && \
	docker run --name testdb \
		-p 5433:5432 \
		-e POSTGRES_PASSWORD \
		-e POSTGRES_USER \
		-e POSTGRES_DB \
		-d postgres && \
	sleep 2 && \
	python -m alembic upgrade head && \
	python -m pytest -rPQ
	docker stop testdb
	docker rm testdb
