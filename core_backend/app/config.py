"""
Config for core_backend. Not that there are other config files within
each endpoin module
"""

import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Root domain
DOMAIN = os.environ.get("DOMAIN", "localhost")

# Postgres variables
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")

# PGVector variables
PGVECTOR_VECTOR_SIZE = os.environ.get("PGVECTOR_VECTOR_SIZE", "1536")
PGVECTOR_M = os.environ.get("PGVECTOR_M", "16")
PGVECTOR_EF_CONSTRUCTION = os.environ.get("PGVECTOR_EF_CONSTRUCTION", "64")
PGVECTOR_DISTANCE = os.environ.get("PGVECTOR_DISTANCE", "vector_cosine_ops")

# LiteLLM proxy variables
# Endpoint
LITELLM_ENDPOINT = os.environ.get("LITELLM_ENDPOINT", "http://localhost:4000")
# API Key. Required but just a dummy for now. The actual OPENAI_API_KEY is set
# in the proxy container.
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "dummy-key")
# Model names. All names come under "openai/..." and correspond to the
# "model_name" in the proxy config.yaml.
# "openai/..." is needed since the proxy presents a unified OpenAI-style API
# for all of its endpoints.
LITELLM_MODEL_EMBEDDING = os.environ.get("LITELLM_MODEL_EMBEDDING", "openai/embeddings")
LITELLM_MODEL_DEFAULT = os.environ.get("LITELLM_MODEL_DEFAULT", "openai/default")
LITELLM_MODEL_GENERATION = os.environ.get(
    "LITELLM_MODEL_GENERATION", "openai/generate-response"
)
LITELLM_MODEL_LANGUAGE_DETECT = os.environ.get(
    "LITELLM_MODEL_LANGUAGE_DETECT", "openai/detect-language"
)
LITELLM_MODEL_TRANSLATE = os.environ.get("LITELLM_MODEL_TRANSLATE", "openai/translate")
LITELLM_MODEL_SAFETY = os.environ.get("LITELLM_MODEL_SAFETY", "openai/safety")
LITELLM_MODEL_PARAPHRASE = os.environ.get(
    "LITELLM_MODEL_PARAPHRASE", "openai/paraphrase"
)
LITELLM_MODEL_ALIGNSCORE = os.environ.get(
    "LITELLM_MODEL_ALIGNSCORE", "openai/alignscore"
)
LITELLM_MODEL_URGENCY_DETECT = os.environ.get(
    "LITELLM_MODEL_URGENCY_DETECT", "openai/urgency-detection"
)
LITELLM_MODEL_DASHBOARD_SUMMARY = os.environ.get(
    "LITELLM_MODEL_DASHBOARD_SUMMARY", "openai/dashboard-summary"
)

LITELLM_MODEL_TOPIC_MODEL = os.environ.get(
    "LITELLM_MODEL_TOPIC_MODEL", "openai/topic-label"
)
# On/Off Topic variables
SERVICE_IDENTITY = os.environ.get(
    "SERVICE_IDENTITY", "air pollution and air quality chatbot"
)
# Cross-encoder
USE_CROSS_ENCODER = os.environ.get("USE_CROSS_ENCODER", "True")
CROSS_ENCODER_MODEL = os.environ.get(
    "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# Rate limit variables
CHECK_CONTENT_LIMIT = os.environ.get("CHECK_CONTENT_LIMIT", True)
DEFAULT_CONTENT_QUOTA = int(os.environ.get("DEFAULT_CONTENT_QUOTA", 50))
DEFAULT_API_QUOTA = int(os.environ.get("DEFAULT_API_QUOTA", 100))
CHECK_API_LIMIT = os.environ.get("CHECK_API_LIMIT", True)
# Alignment Score variables
ALIGN_SCORE_THRESHOLD = os.environ.get("ALIGN_SCORE_THRESHOLD", 0.7)


# Backend paths
BACKEND_ROOT_PATH = os.environ.get("BACKEND_ROOT_PATH", "")

# Speech API
CUSTOM_SPEECH_ENDPOINT = os.environ.get("CUSTOM_SPEECH_ENDPOINT", None)
# Logging
LANGFUSE = os.environ.get("LANGFUSE", "False")

# Database
DB_POOL_SIZE = os.environ.get("DB_POOL_SIZE", 20)  # Number of connections in the pool

# Redis
REDIS_HOST = os.environ.get("REDIS_HOST", "redis://localhost:6379")

# Google Cloud storage
GCS_SPEECH_BUCKET = os.environ.get("GCS_SPEECH_BUCKET", "aaq-speech-test")
