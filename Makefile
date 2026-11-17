#!make

# Run `make` (or `make help`) to list the targets.
#
# Quick start (everything in Docker, with live reload):
#   make docker-env   # first time only: creates config from templates
#   make dev          # build + start the full dev stack
#   make dev-logs     # follow logs (SERVICE=core_backend to narrow it)
#   make dev-down     # stop it
#
# Python envs and linting live in each sub-project (e.g. `cd core_backend && uv sync`,
# `make -C core_backend lint`). This Makefile only runs infrastructure and containers.

.DEFAULT_GOAL := help

ENDPOINT_URL = localhost:8000
OPENAI_API_KEY := $(shell printenv OPENAI_API_KEY)

ENV_DIR := deployment/docker-compose

# Compose stacks at the repo root. Fixed project names keep dev and prod
# containers/volumes separate, so both can exist on one machine.
COMPOSE_DEV  := docker compose -f docker-compose-dev.yml -p aaq-dev
COMPOSE_PROD := docker compose -f docker-compose.yml -p aaq

# Optional compose profiles, space separated. Examples:
#   make dev PROFILES=speech
#   make dev PROFILES="speech huggingface-embeddings"
#   make prod-up PROD_PROFILES="local-db speech"
# PROD_PROFILES defaults to local-db so the prod stack runs on one machine with
# no external database; set PROD_PROFILES= to use a managed Postgres instead.
PROFILES      ?=
PROD_PROFILES ?= local-db
profile_flags  = $(foreach p,$(1),--profile $(p))

# Narrow logs/shell/restart to one service, e.g. SERVICE=core_backend
SERVICE ?=

.PHONY: help clean docker-env \
	dev dev-up dev-down dev-restart dev-rebuild dev-logs dev-ps dev-shell dev-migrate dev-clean \
	prod-up prod-down prod-restart prod-logs prod-ps prod-pull \
	setup-dev teardown-dev setup-db teardown-db setup-redis teardown-redis \
	setup-llm-proxy teardown-llm-proxy setup-llm-proxy-local \
	build-embeddings-arm setup-embeddings-arm setup-embeddings teardown-embeddings \
	run-docker-compose-dev stop-docker-compose-dev restart-docker-compose-dev

## Help: list targets (lines tagged with a double-hash comment)
help:
	@echo "Usage: make <target> [PROFILES=...] [SERVICE=...]"
	@echo
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}'

clean: ## Remove Python caches across the repo
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

## Helper targets
guard-%:
	@if [ -z '${${*}}' ]; then echo 'ERROR: environment variable $* not set' && exit 1; fi

# ---------------------------------------------------------------------------
# Docker config
# ---------------------------------------------------------------------------

# Creates any missing env file from its template and never overwrites an
# existing one. The GCP credentials file must exist even when unused: without
# it, Docker bind-mounts an empty *directory* in its place and LiteLLM fails.
# The final loop prints key NAMES (never values) still equal to the template.
docker-env: ## Create missing env files + GCP placeholder in deployment/docker-compose/
	@for f in base core_backend litellm_proxy; do \
		if [ ! -f "$(ENV_DIR)/.$$f.env" ]; then \
			cp "$(ENV_DIR)/template.$$f.env" "$(ENV_DIR)/.$$f.env"; \
			echo "Created $(ENV_DIR)/.$$f.env from template"; \
		fi; \
	done
	@if [ -d "$(ENV_DIR)/.gcp_credentials.json" ]; then \
		echo "ERROR: $(ENV_DIR)/.gcp_credentials.json is a directory (left by an earlier docker run). Remove it and re-run."; \
		exit 1; \
	fi
	@if [ ! -f "$(ENV_DIR)/.gcp_credentials.json" ]; then \
		echo '{}' > "$(ENV_DIR)/.gcp_credentials.json"; \
		echo "Created empty $(ENV_DIR)/.gcp_credentials.json (replace it if you use Vertex AI / GCS)"; \
	fi
	@for pair in litellm_proxy:OPENAI_API_KEY core_backend:JWT_SECRET core_backend:ADMIN_PASSWORD \
			core_backend:ADMIN_API_KEY core_backend:POSTGRES_PASSWORD; do \
		f=$${pair%%:*}; key=$${pair#*:}; \
		tmpl=$$(grep -E "^$$key=" "$(ENV_DIR)/template.$$f.env"); \
		if [ -n "$$tmpl" ] && grep -qxF "$$tmpl" "$(ENV_DIR)/.$$f.env"; then \
			echo "WARNING: $$key in $(ENV_DIR)/.$$f.env still has the template value"; \
		fi; \
	done

# ---------------------------------------------------------------------------
# Full dev stack (docker-compose-dev.yml): live reload, no Caddy/TLS
#   Admin app  http://localhost:3000    Backend  http://localhost:8000/docs
#   Docs site  http://localhost:8001    Postgres localhost:5434
#   Redis      localhost:6380           LiteLLM  localhost:4001
# ---------------------------------------------------------------------------

dev: dev-up ## Alias for dev-up

dev-up: docker-env ## Build and start every app with live reload (PROFILES=speech ...)
	$(COMPOSE_DEV) $(call profile_flags,$(PROFILES)) up --build -d --remove-orphans
	@echo
	@echo "  Admin app  -> http://localhost:3000"
	@echo "  Backend    -> http://localhost:8000/docs"
	@echo "  Docs site  -> http://localhost:8001"
	@echo
	@echo "  First start installs dependencies; follow progress with 'make dev-logs'."

dev-down: ## Stop the dev stack (keeps the database volume)
	$(COMPOSE_DEV) --profile "*" down --remove-orphans

dev-restart: ## Restart dev containers without rebuilding (SERVICE=... for one)
	$(COMPOSE_DEV) restart $(SERVICE)

dev-rebuild: docker-env ## Rebuild images (after lockfile changes) and restart
	$(COMPOSE_DEV) $(call profile_flags,$(PROFILES)) up --build -d --force-recreate --remove-orphans $(SERVICE)

dev-logs: ## Follow dev logs (SERVICE=... for one)
	$(COMPOSE_DEV) logs -f --tail=200 $(SERVICE)

dev-ps: ## Show dev container status
	$(COMPOSE_DEV) ps

dev-shell: ## Open a shell in a dev container (default SERVICE=core_backend)
	$(COMPOSE_DEV) exec $(or $(SERVICE),core_backend) sh

dev-migrate: ## Run alembic migrations inside the dev backend container
	$(COMPOSE_DEV) exec core_backend python -m alembic upgrade head

dev-clean: ## Stop the dev stack AND delete its volumes (wipes the dev database)
	$(COMPOSE_DEV) --profile "*" down -v --remove-orphans

# ---------------------------------------------------------------------------
# Production-style stack (docker-compose.yml): optimised images behind Caddy
# at https://$$DOMAIN (https://localhost by default).
# With the local-db profile, set POSTGRES_HOST=relational_db in
# deployment/docker-compose/.core_backend.env.
# ---------------------------------------------------------------------------

prod-up: docker-env ## Build and start the prod stack (PROD_PROFILES="local-db speech" ...)
	@if echo " $(PROD_PROFILES) " | grep -q " local-db " && \
		! grep -qE '^POSTGRES_HOST="?relational_db"?' "$(ENV_DIR)/.core_backend.env"; then \
		echo "WARNING: local-db profile is on but POSTGRES_HOST in $(ENV_DIR)/.core_backend.env is not relational_db"; \
	fi
	$(COMPOSE_PROD) $(call profile_flags,$(PROD_PROFILES)) up --build -d --remove-orphans

prod-pull: ## Pull prebuilt images (AAQ_BACKEND_IMAGE / AAQ_ADMIN_APP_IMAGE)
	$(COMPOSE_PROD) $(call profile_flags,$(PROD_PROFILES)) pull

prod-down: ## Stop the prod stack (keeps volumes: DB data, TLS certs)
	$(COMPOSE_PROD) --profile "*" down --remove-orphans

prod-restart: ## Restart prod containers (SERVICE=... for one)
	$(COMPOSE_PROD) restart $(SERVICE)

prod-logs: ## Follow prod logs (SERVICE=... for one)
	$(COMPOSE_PROD) logs -f --tail=200 $(SERVICE)

prod-ps: ## Show prod container status
	$(COMPOSE_PROD) ps

# Older target names, kept so existing scripts and habits keep working.
run-docker-compose-dev: dev-up
stop-docker-compose-dev: dev-down
restart-docker-compose-dev: dev-down dev-up

# ---------------------------------------------------------------------------
# Single dev services, for running core_backend / admin_app on the host
# ---------------------------------------------------------------------------

setup-dev: setup-db setup-redis setup-llm-proxy ## Postgres, Redis and LiteLLM as standalone containers
teardown-dev: teardown-db teardown-redis teardown-llm-proxy ## Remove the standalone dev containers

# Dev db
setup-db: ## Standalone Postgres on :5432 + run migrations from the host
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
	uv run python -m alembic upgrade head

teardown-db:
	@docker stop postgres-local
	@docker rm postgres-local

setup-redis: ## Standalone Redis on :6379
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
setup-llm-proxy: ## Standalone LiteLLM proxy on :4000
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
setup-llm-proxy-local: ## LiteLLM proxy as a host process via uvx (no Docker)
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


build-embeddings-arm: ## Build the HF text-embeddings image for ARM
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

setup-embeddings: guard-HUGGINGFACE_MODEL guard-HUGGINGFACE_EMBEDDINGS_API_KEY ## Standalone HF embeddings on :8080
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
