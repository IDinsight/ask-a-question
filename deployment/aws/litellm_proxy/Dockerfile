FROM ghcr.io/berriai/litellm:main-v1.34.6
COPY ./litellm_proxy_config.yaml /app/config.yaml

# read secrets from AWS secret manager
COPY fetch_aws_secrets.sh /fetch_aws_secrets.sh
RUN chmod +x /fetch_aws_secrets.sh

ENTRYPOINT [ "/fetch_aws_secrets.sh" ]
