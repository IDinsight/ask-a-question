#!/bin/bash

REPO_PATH="$1"  # Get the value of REPO_PATH from the first command line argument
cd "$REPO_PATH"
git pull origin main
cd ./deployment/docker-compose
docker compose -f docker-compose.yml -f docker-compose.dev.yml -p aaq-stack up --build -d
