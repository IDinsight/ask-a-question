#!make

.PHONY : help retrieval-validation setup-test-containers teardown-test-containers setup-test-db stop-test-db

# Main test target
retrieval-validation: setup-test-containers run-retrieval-validation teardown-test-containers

# Test runner
run-retrieval-validation:
	set -a && source ./validation.env && set +a && \
	cd "../../../" && \
	pwd && \
	python -m pytest -rP -vv core_backend/validation/retrieval/validate_retrieval.py \
	  --validation_data_path "./data/mc_validation_clean_small.csv" \
	  --validation_data_question_col "question" \
	  --validation_data_label_col "faq_name" \
	  --content_data_path "./data/mc_faqs_small.csv" \
	  --content_data_label_col "faq_name" \
	  --content_data_text_col "faq_content_to_send"


## Helper targets
setup-test-containers: setup-test-db
teardown-test-containers: stop-test-db

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
	cd "../../" && \
	python -m alembic upgrade head

stop-test-db:
	@docker stop testdb
	@docker rm testdb
