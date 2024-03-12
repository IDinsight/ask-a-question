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

# Secrets
QUESTION_ANSWER_SECRET = os.environ.get("QUESTION_ANSWER_SECRET", "update-me")
CONTENT_FULLACCESS_PASSWORD = os.environ.get(
    "CONTENT_FULLACCESS_PASSWORD", "fullaccess"
)
CONTENT_READONLY_PASSWORD = os.environ.get("CONTENT_READONLY_PASSWORD", "readonly")
ACCESS_TOKEN_EXPIRE_MINUTES = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-secret")

# PGVector variables
PGVECTOR_VECTOR_SIZE = os.environ.get("PGVECTOR_VECTOR_SIZE", "1536")
PGVECTOR_M = os.environ.get("PGVECTOR_M", "16")
PGVECTOR_EF_CONSTRUCTION = os.environ.get("PGVECTOR_EF_CONSTRUCTION", "64")
PGVECTOR_DISTANCE = os.environ.get("PGVECTOR_DISTANCE", "vector_cosine_ops")

# Functionality variables
N_TOP_SIMILAR = os.environ.get("N_TOP_SIMILAR", "4")
STANDARD_FAILURE_MESSAGE = os.environ.get(
    "STANDARD_FAILURE_MESSAGE",
    "Sorry, I am unable to find an answer to your question in the knowledge base.",
)

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

# WhatsApp variables
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "no-token-set")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "no-token-set")
