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


# LLM variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # Will be none if not set
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-ada-002")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4-1106-preview")
LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", None)
# LLM, AlignScore, or None
ALIGN_SCORE_METHOD = os.environ.get("ALIGN_SCORE_METHOD", "LLM")
ALIGN_SCORE_API = os.environ.get("ALIGN_SCORE_API")
ALIGN_SCORE_THRESHOLD = os.environ.get("ALIGN_SCORE_THRESHOLD", 0.7)

# Backend paths
BACKEND_ROOT_PATH = os.environ.get("BACKEND_ROOT_PATH", "")
