"""All environment-driven settings for `core_backend`, including the ones that
used to live in per-feature `config.py` files (grouped at the bottom).
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
LITELLM_MODEL_CHAT = os.environ.get("LITELLM_MODEL_CHAT", "openai/chat")
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

LITELLM_MODEL_DOCMUNCHER_TITLE = os.environ.get(
    "LITELLM_MODEL_DOCMUNCHER", "openai/docmuncher-title"
)
LITELLM_MODEL_DOCMUNCHER_PARAPHRASE_TABLE = os.environ.get(
    "LITELLM_MODEL_DOCMUNCHER", "openai/docmuncher-paraphrase-table"
)
LITELLM_MODEL_DOCMUNCHER_SINGLE_LINE = os.environ.get(
    "LITELLM_MODEL_DOCMUNCHER", "openai/docmuncher-single-line"
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
PAGES_TO_CARDS_CONVERSION = int(os.environ.get("PAGES_TO_CARDS_CONVERSION", 2))

# Alignment Score variables
ALIGN_SCORE_THRESHOLD = os.environ.get("ALIGN_SCORE_THRESHOLD", 0.7)


# Backend paths
BACKEND_ROOT_PATH = os.environ.get("BACKEND_ROOT_PATH", "")

# Speech API
CUSTOM_STT_ENDPOINT = os.environ.get("CUSTOM_STT_ENDPOINT", None)
CUSTOM_TTS_ENDPOINT = os.environ.get("CUSTOM_TTS_ENDPOINT", None)

# Logging
LANGFUSE = os.environ.get("LANGFUSE", "False")

# Database
DB_POOL_SIZE = os.environ.get("DB_POOL_SIZE", 20)  # Number of connections in the pool

# Redis
REDIS_HOST = os.environ.get("REDIS_HOST", "redis://localhost:6379")
REDIS_CHAT_CACHE_EXPIRY_TIME = 3600
REDIS_DOC_INGEST_EXPIRY_TIME = 3600 * 24

# Google Cloud storage
GCS_SPEECH_BUCKET = os.environ.get("GCS_SPEECH_BUCKET", "aaq-speech-test")

# Sentry config
SENTRY_DSN = os.environ.get("SENTRY_DSN", None)
SENTRY_TRACES_SAMPLE_RATE = os.environ.get(
    "SENTRY_TRACES_SAMPLE_RATE", 1.0
)  # 1.0 means 100% of traces are sent to Sentry

# Language
DEFAULT_DOC_LANGUAGE = os.environ.get("DEFAULT_DOC_LANGUAGE", "ENGLISH")

# HTTPX
HTTPX_TIMEOUT: float = 10.0

# Turn.io
TURNIO_API_BASE: str = os.environ.get("TURNIO_API_BASE", "https://whatsapp.turn.io/v1/")

# ---- auth settings (moved from app/auth/config.py)
ACCESS_TOKEN_EXPIRE_MINUTES = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-secret")
NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID = os.environ.get(
    "NEXT_PUBLIC_GOOGLE_LOGIN_CLIENT_ID",
    "update-me",
)
REDIS_KEY_EXPIRED = -2

# ---- dashboard settings (moved from app/dashboard/config.py)
DISABLE_DASHBOARD_LLM = (
    os.environ.get("DISABLE_DASHBOARD_LLM", "false").lower() == "true"
)
MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY = os.environ.get(
    "MAX_FEEDBACK_RECORDS_FOR_AI_SUMMARY", 100
)
MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT = os.environ.get(
    "MAX_FEEDBACK_RECORDS_FOR_TOP_CONTENT", 7
)
TOPIC_MODELING_CONTEXT = os.environ.get("TOPIC_MODELING_CONTEXT", "maternal health")

# ---- question_answer settings (moved from app/question_answer/config.py)
# Functionality variables.
N_TOP_CONTENT_TO_CROSSENCODER = os.environ.get("N_TOP_CONTENT_TO_CROSSENCODER", "10")
N_TOP_CONTENT = os.environ.get("N_TOP_CONTENT", "4")

# ---- urgency_detection settings (moved from app/urgency_detection/config.py)
# cosine_distance_classifier, llm_entailment_classifier
URGENCY_CLASSIFIER = os.environ.get("URGENCY_CLASSIFIER", "cosine_distance_classifier")
URGENCY_DETECTION_MAX_DISTANCE = os.environ.get("URGENCY_DETECTION_MAX_DISTANCE", 0.5)
URGENCY_DETECTION_MIN_PROBABILITY = os.environ.get(
    "URGENCY_DETECTION_MIN_PROBABILITY", 0.5
)
