#!make

PROJECT_NAME = aaq
CONDA_ACTIVATE=source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate
ENDPOINT_URL = localhost:8000
OPENAI_API_KEY := $(shell printenv OPENAI_API_KEY)

## Main targets
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

# Note: Run `make fresh-env psycopg2-binary=true` to manually replace psycopg with psycopg2-binary
fresh-env :
	conda remove --name $(PROJECT_NAME) --all -y
	conda create --name $(PROJECT_NAME) python==3.10 -y

	$(CONDA_ACTIVATE) $(PROJECT_NAME); \
	pip install -r core_backend/requirements.txt --ignore-installed; \
	pip install -r requirements-dev.txt --ignore-installed; \
	pre-commit install

	if [ "$(psycopg2-binary)" = "true" ]; then \
		$(CONDA_ACTIVATE) $(PROJECT_NAME); \
		pip uninstall -y psycopg2==2.9.9; \
		pip install psycopg2-binary==2.9.9; \
	fi

# Dev requirements
setup-dev: setup-db setup-redis add-users-to-db setup-llm-proxy
teardown-dev: teardown-db teardown-redis teardown-llm-proxy

## Helper targets

# Add users to db
add-users-to-db:
	$(CONDA_ACTIVATE) $(PROJECT_NAME); \
	set -a && \
        source "$(CURDIR)/deployment/docker-compose/.core_backend.env" && \
        set +a && \
	python core_backend/add_users_to_db.py

# Dev db
setup-db:
	-@docker stop postgres-local
	-@docker rm postgres-local
	@docker system prune -f
	@sleep 2
	@docker run --name postgres-local \
		--env-file "$(CURDIR)/deployment/docker-compose/.core_backend.env" \
		-p 5432:5432 \
		-d pgvector/pgvector:pg16
	set -a && \
        source "$(CURDIR)/deployment/docker-compose/.base.env" && \
        source "$(CURDIR)/deployment/docker-compose/.core_backend.env" && \
        set +a && \
	cd core_backend && \
	python -m alembic upgrade head

teardown-db:
	@docker stop postgres-local
	@docker rm postgres-local

setup-redis:
	-@docker stop redis-local
	-@docker rm redis-local
	@docker system prune -f
	@sleep 2
	@docker run --name redis-local \
     -p 6379:6379 \
     -d redis:6.0-alpine

make teardown-redis:
	@docker stop redis-local
	@docker rm redis-local


# Dev LiteLLM Proxy server
setup-llm-proxy:
	-@docker stop litellm-proxy
	-@docker rm litellm-proxy
	@docker system prune -f
	@sleep 2
	@docker pull ghcr.io/berriai/litellm:main-v1.40.10
	@docker run \
		--name litellm-proxy \
		--rm \
		-v "$(CURDIR)/deployment/docker-compose/litellm_proxy_config.yaml":/app/config.yaml \
		-v "$(CURDIR)/deployment/docker-compose/.gcp_credentials.json":/app/credentials.json \
		--env-file "$(CURDIR)/deployment/docker-compose/.litellm_proxy.env" \
		-p 4000:4000 \
		-d ghcr.io/berriai/litellm:main-v1.40.10 \
		--config /app/config.yaml --detailed_debug

teardown-llm-proxy:
	@docker stop litellm-proxy
	@docker rm litellm-proxy


build-embeddings-arm:
	@git clone https://github.com/huggingface/text-embeddings-inference.git
	@docker build text-embeddings-inference -f text-embeddings-inference/Dockerfile \
		--platform=linux/arm64 \
		-t text-embeddings-inference-arm
	@cd ..
	@rm -rf text-embeddings-inference

setup-embeddings-arm:
	-@docker stop huggingface-embeddings
	-@docker rm huggingface-embeddings
	@docker system prune -f
	@sleep 2
	@docker run \
		--name huggingface-embeddings \
        -p 8080:80 \
        -v "$(PWD)/data:/data" \
        -d text-embeddings-inference-arm \
        --model-id $(HUGGINGFACE_MODEL) \
        --api-key $(HUGGINGFACE_EMBEDDINGS_API_KEY)

setup-embeddings:
	-@docker stop huggingface-embeddings
	-@docker rm huggingface-embeddings
	@docker system prune -f
	@sleep 2
	@docker run \
		--name huggingface-embeddings \
		-p 8080:80 \
		-v "$(PWD)/data:/data" \
		--pull always ghcr.io/huggingface/text-embeddings-inference:cpu-1.5 \
		--model-id $(HUGGINGFACE_MODEL) \
		--api-key $(HUGGINGFACE_EMBEDDINGS_API_KEY)

teardown-embeddings:
	@docker stop huggingface-embeddings
	@docker rm  huggingface-embeddings
