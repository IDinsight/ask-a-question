#!make

ENDPOINT_URL = localhost:8000
OPENAI_API_KEY := $(shell printenv OPENAI_API_KEY)

## Main targets
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

# Python envs and linting live in each sub-project (e.g. `cd core_backend && uv sync`,
# `make -C core_backend lint`). This Makefile only runs the local dev infrastructure.

# Dev requirements
setup-dev: setup-db setup-redis setup-llm-proxy
teardown-dev: teardown-db teardown-redis teardown-llm-proxy

## Helper targets
guard-%:
	@if [ -z '${${*}}' ]; then echo 'ERROR: environment variable $* not set' && exit 1; fi

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

teardown-redis:
	@docker stop redis-local
	@docker rm redis-local


# Dev LiteLLM Proxy server
setup-llm-proxy:
	-@docker stop litellm-proxy
	-@docker rm litellm-proxy
	@docker system prune -f
	@sleep 2
	@docker pull ghcr.io/berriai/litellm:v1.97.0
	@docker run \
		--name litellm-proxy \
		--rm \
		-v "$(CURDIR)/deployment/docker-compose/litellm_proxy_config.yaml":/app/config.yaml \
		-v "$(CURDIR)/deployment/docker-compose/.gcp_credentials.json":/app/credentials.json \
		--env-file "$(CURDIR)/deployment/docker-compose/.litellm_proxy.env" \
		-p 4000:4000 \
		-d ghcr.io/berriai/litellm:v1.97.0 \
		--config /app/config.yaml --detailed_debug

teardown-llm-proxy:
	@docker stop litellm-proxy
	@docker rm litellm-proxy

# Dev LiteLLM Proxy without Docker: runs the same LiteLLM version as a local
# process in a throwaway uv environment, so it never touches core_backend/.venv
# (which pins an older LiteLLM without the proxy extras).
# FastAPI is pinned because litellm 1.97.0's proxy imports
# fastapi.dependencies.utils.get_flat_dependant, which newer FastAPI (e.g. 0.162)
# removed; the Docker image avoids this by shipping its own pinned FastAPI.
# Reads provider keys from deployment/docker-compose/.litellm_proxy.env.
# Defaults to port 4001 so it doesn't clash with other gateways on 4000; set
# LITELLM_LOCAL_PORT to change it, and match LITELLM_ENDPOINT in core_backend/.env.
LITELLM_LOCAL_PORT ?= 4001
setup-llm-proxy-local:
	@test -f deployment/docker-compose/.litellm_proxy.env || \
		{ echo "Missing deployment/docker-compose/.litellm_proxy.env (copy template.litellm_proxy.env)"; exit 1; }
	@set -a; . deployment/docker-compose/.litellm_proxy.env; set +a; \
	case "$$OPENAI_API_KEY" in ""|"[OPENAI_API_KEY]") \
		echo "Set OPENAI_API_KEY in deployment/docker-compose/.litellm_proxy.env first"; exit 1;; esac; \
	uvx --from 'litellm[proxy]==1.97.0' \
		--with 'fastapi==0.136.3' \
		litellm \
		--config deployment/docker-compose/litellm_proxy_config.yaml \
		--port $(LITELLM_LOCAL_PORT)


build-embeddings-arm:
	@git clone https://github.com/huggingface/text-embeddings-inference.git
	@docker build text-embeddings-inference -f text-embeddings-inference/Dockerfile \
		--platform=linux/arm64 \
		-t text-embeddings-inference-arm
	@cd ..
	@rm -rf text-embeddings-inference

setup-embeddings-arm: guard-HUGGINGFACE_MODEL guard-HUGGINGFACE_EMBEDDINGS_API_KEY
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

setup-embeddings: guard-HUGGINGFACE_MODEL guard-HUGGINGFACE_EMBEDDINGS_API_KEY
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

run-docker-compose-dev:
	@docker compose -f deployment/docker-compose/docker-compose-dev.yml -p aaq-dev up --build -d --remove-orphans
	@docker system prune -f

stop-docker-compose-dev:
	@docker compose -f deployment/docker-compose/docker-compose-dev.yml -p aaq-dev down

restart-docker-compose-dev: stop-docker-compose-dev run-docker-compose-dev
