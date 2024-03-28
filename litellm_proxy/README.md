# LiteLLM Proxy Docker

All of our embeddings and LLM calls will now pass through this proxy.

## How to run

1.  Pull LiteLLM proxy image

        docker pull ghcr.io/berriai/litellm:main-v1.34.6

2.  Set models and parameters in `config.yaml`

3.  Run the Docker container

        docker run \
            --name litellm-proxy \
            --rm \
            -v <PATH_TO_CONFIG>:/app/config.yaml \
            -e OPENAI_API_KEY="sk-..." \
            -p 4000:4000 \
            ghcr.io/berriai/litellm:main-v1.34.6 \
            --config /app/config.yaml --detailed_debug
