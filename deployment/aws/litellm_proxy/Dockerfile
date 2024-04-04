FROM ghcr.io/berriai/litellm:main-v1.34.6

COPY ./litellm_proxy_config.yaml /app/config.yaml

# read secrets from AWS secret manager
COPY ./fetch_aws_env_vars.sh /fetch_aws_env_vars.sh
RUN chmod +x /fetch_aws_env_vars.sh

RUN apt-get update && apt-get install -y \
    gcc libpq-dev python3-dev jq dnsutils

RUN pip install --upgrade pip \
    && pip install --no-cache-dir awscli

ENTRYPOINT [ "/fetch_aws_env_vars.sh", "litellm" ]
