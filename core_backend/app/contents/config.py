import os

# PGVector variables
PGVECTOR_VECTOR_SIZE = os.environ.get("PGVECTOR_VECTOR_SIZE", "1024")
PGVECTOR_M = os.environ.get("PGVECTOR_M", "16")
PGVECTOR_EF_CONSTRUCTION = os.environ.get("PGVECTOR_EF_CONSTRUCTION", "64")
PGVECTOR_DISTANCE = os.environ.get("PGVECTOR_DISTANCE", "vector_cosine_ops")
