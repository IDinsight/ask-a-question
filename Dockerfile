FROM docker

# COPY /core_backend core_backend
# COPY /admin_app admin_app

# COPY /deployment/docker-compose/Caddyfile ./Caddyfile
# COPY /deployment/docker-compose/litellm_proxy_config.yaml ./litellm_proxy_config.yaml

COPY . .

# TODO: in cloudebuild inject secrets into .env file

ENTRYPOINT ["docker", "compose", "-f", "docker-compose.yml", "-p", "aaq-stack", "up"]
