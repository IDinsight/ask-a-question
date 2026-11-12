#!make

.PHONY : help ud-validation setup-test-containers teardown-test-containers setup-test-db teardown-test-db

# Main test target
ud-validation: setup-test-containers run-ud-validation teardown-test-containers

# Test runner. Needs Redis on REDIS_HOST (default redis://localhost:6379) and the
# LiteLLM proxy on LITELLM_ENDPOINT. JWT_SECRET is a throwaway key for this run.
# --no-cov: the 80% coverage gate in pyproject.toml is for tests/, not validation.
run-ud-validation:
	set -a && source ./validation.env && set +a && \
	export JWT_SECRET=$$(uv run python -c 'import secrets; print(secrets.token_hex(32))') && \
	cd "../../" && \
	uv run --group validation pytest -rP -vv --no-cov validation/urgency_detection/validate_ud.py \
	  --validation_data_path="../../data/mc_urgency_message_data.csv" \
	  --validation_data_question_col="Question" \
	  --validation_data_label_col="Urgent" \
	  --ud_rules_path="../../data/mc_urgency_rules.csv" \
	  --ud_rules_col="Urgency Rules" \


## Helper targets
setup-test-containers: setup-test-db
teardown-test-containers: teardown-test-db

setup-test-db:
	-@docker stop testdb
	-@docker rm testdb
	@docker system prune -f
	@sleep 2
	@set -a && source ./validation.env && set +a && \
	docker run --name testdb \
		-p 5433:5432 \
		-e POSTGRES_PASSWORD \
		-e POSTGRES_USER \
		-e POSTGRES_DB \
		-d pgvector/pgvector:pg16
	@set -a && source ./validation.env && set +a && \
	export JWT_SECRET=$$(uv run python -c 'import secrets; print(secrets.token_hex(32))') && \
	cd "../../" && \
	uv run alembic upgrade head

teardown-test-db:
	@docker stop testdb
	@docker rm testdb
