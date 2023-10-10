import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

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
