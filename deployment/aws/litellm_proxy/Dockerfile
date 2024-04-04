FROM ghcr.io/berriai/litellm:main-v1.34.6

COPY ./litellm_proxy_config.yaml /app/config.yaml

# read secrets from AWS secret manager
COPY ./fetch_aws_env_vars.sh /fetch_aws_env_vars.sh
RUN chmod +x /fetch_aws_env_vars.sh

ENTRYPOINT [ "/fetch_aws_env_vars.sh" ]
