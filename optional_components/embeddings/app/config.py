import os

HUGGINGFACE_MODEL = os.environ.get("HUGGINGFACE_MODEL", "thenlper/gte-large")
STATIC_TOKEN = os.environ.get("EMBEDDINGS_API_KEY", "add-token")
