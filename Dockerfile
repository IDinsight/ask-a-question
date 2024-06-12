FROM docker

COPY core_backend core_backend
COPY admin_app admin_app

COPY deployment/docker-compose/Caddyfile /etc/caddy/Caddyfile
COPY deployment/docker-compose/litellm_proxy_config.yaml /app/config.yaml
COPY docker-compose.yml ./
COPY .env ./
# TODO: in cloudebuild inject secrets into .env file

EXPOSE 80 443

ENTRYPOINT ["docker", "compose", "-f", "docker-compose.yml", "-p", "aaq-stack", "up", "--build"]

# Build
# docker build -t aaq .
# Run with
# docker run -v /var/run/docker.sock:/var/run/docker.sock -p 80:80 -p 443:443 -p \
# 443:443/udp -t aaq
# DOESN'T WORK
