#!/bin/bash

cd /home/suzinyou/aaq-core
git pull origin main
cd ./deployment/docker-compose
docker compose -f docker-compose.yml -f docker-compose.dev.yml -p aaq-stack up --build -d
docker system prune --volumes -f
