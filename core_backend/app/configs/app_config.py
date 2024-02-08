import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

DOMAIN = os.environ.get("DOMAIN", "localhost")

POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")

QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")  # Will be none if not set
QDRANT_URL = os.environ.get("QDRANT_URL")  # Will be none if not set
QDRANT_PORT = os.environ.get("QDRANT_PORT", "6333")
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")

QDRANT_COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "default_collection")
QDRANT_VECTOR_SIZE = os.environ.get("QDRANT_VECTOR_SIZE", "1536")
QDRANT_N_TOP_SIMILAR = os.environ.get("QDRANT_N_TOP_SIMILAR", "4")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # Will be none if not set
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-ada-002")

LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4-1106-preview")
LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", None)

QUESTION_ANSWER_SECRET = os.environ.get("QUESTION_ANSWER_SECRET", "update-me")

CONTENT_FULLACCESS_PASSWORD = os.environ.get(
    "CONTENT_FULLACCESS_PASSWORD", "fullaccess"
)
CONTENT_READONLY_PASSWORD = os.environ.get("CONTENT_READONLY_PASSWORD", "readonly")
ACCESS_TOKEN_EXPIRE_MINUTES = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.environ.get("JWT_SECRET", "update-me-for-production")

BACKEND_ROOT_PATH = os.environ.get("BACKEND_ROOT_PATH", "")

WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "no-token-set")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "no-token-set")

# Set below to `None" if not checking for LLM response alignment with content
ALIGN_SCORE_METHOD = os.environ.get(
    "ALIGN_SCORE_METHOD", "LLM"
)  # LLM or AlignScore or None
ALIGN_SCORE_THRESHOLD = os.environ.get("ALIGN_SCORE_THRESHOLD", 0.7)
ALIGN_SCORE_API = os.environ.get(
    "ALIGN_SCORE_API", "http://localhost:5001/alignscore_base"
)

STANDARD_FAILURE_MESSAGE = os.environ.get(
    "STANDARD_FAILURE_MESSAGE",
    "Sorry, I am unable to find an answer to your question in the knowledge base. ",
)
