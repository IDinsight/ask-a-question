FROM ghcr.io/berriai/litellm:main-v1.34.6

ARG OPENAI_API_KEY
ENV OPENAI_API_KEY=$OPENAI_API_KEY

COPY ./litellm_proxy_config.yaml /app/config.yaml

CMD ["--port", "4000", "--config", "/app/config.yaml"]
